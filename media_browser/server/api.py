from __future__ import annotations

import json
import mimetypes
import queue
import secrets
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from ..adapters import FreesoundAdapter, PexelsAdapter, PixabayAdapter
from ..config import AppConfig, load_config, update_key_config
from ..models import Asset, AssetKind
from ..search import SearchRouter
from ..services.cache import CacheManager
from ..services.downloader import DownloadCancelled, Downloader
from ..services.licenses import LicenseService, filter_assets_by_license
from ..services.metadata import build_resolve_metadata
from ..services.resolve_bridge import ResolveBridge, ResolveUnavailable
from ..services.settings import SettingsStore
from ..services.translate import translate_query_to_english
from ..utils.http import request_bytes


TERMINAL_EVENTS = {"completed", "cancelled", "failed"}


@dataclass(slots=True)
class DownloadJob:
    id: str
    asset: Asset
    events: "queue.Queue[dict[str, Any]]" = field(default_factory=queue.Queue)
    cancel_event: threading.Event = field(default_factory=threading.Event)
    thread: threading.Thread | None = None
    state: str = "queued"
    local_path: str = ""
    error: str = ""

    def emit(self, event: dict[str, Any]) -> None:
        self.events.put({"job_id": self.id, **event})


class DownloadManager:
    def __init__(self, downloader: Downloader):
        self.downloader = downloader
        self._jobs: dict[str, DownloadJob] = {}
        self._lock = threading.Lock()

    def start(self, asset: Asset) -> DownloadJob:
        job = DownloadJob(id=secrets.token_urlsafe(12), asset=asset)
        with self._lock:
            self._jobs[job.id] = job
        job.emit({"type": "queued", "title": asset.display_title})
        thread = threading.Thread(target=self._run, args=(job,), daemon=True)
        job.thread = thread
        thread.start()
        return job

    def get(self, job_id: str) -> DownloadJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def cancel(self, job_id: str) -> bool:
        job = self.get(job_id)
        if not job:
            return False
        job.cancel_event.set()
        return True

    def _run(self, job: DownloadJob) -> None:
        try:
            job.state = "running"
            job.emit({"type": "started", "title": job.asset.display_title})

            def progress(done: int, total: int) -> None:
                job.emit({"type": "progress", "done": done, "total": total})

            path = self.downloader.download(
                job.asset,
                progress=progress,
                cancel=job.cancel_event.is_set,
            )
            job.state = "completed"
            job.local_path = str(path)
            job.emit({"type": "completed", "path": job.local_path})
        except DownloadCancelled:
            job.state = "cancelled"
            job.emit({"type": "cancelled"})
        except Exception as exc:
            job.state = "failed"
            job.error = str(exc)
            job.emit({"type": "failed", "message": job.error})


@dataclass(slots=True)
class ServerContext:
    config: AppConfig
    router: SearchRouter
    cache: CacheManager
    downloader: Downloader
    license_service: LicenseService
    settings: SettingsStore
    token: str = field(default_factory=lambda: secrets.token_urlsafe(24))
    downloads: DownloadManager | None = None

    @classmethod
    def from_config_path(cls, config_path: str | None = None, *, token: str | None = None) -> "ServerContext":
        config = load_config(config_path)
        cache = CacheManager(config.cache_dir)
        downloader = Downloader(cache)
        context = cls(
            config=config,
            router=SearchRouter.from_config(config),
            cache=cache,
            downloader=downloader,
            license_service=LicenseService(config.license_policy),
            settings=SettingsStore.default(),
            token=token or secrets.token_urlsafe(24),
        )
        context.downloads = DownloadManager(downloader)
        return context

    def ensure_downloads(self) -> DownloadManager:
        if self.downloads is None:
            self.downloads = DownloadManager(self.downloader)
        return self.downloads


class BrowserHttpServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], context: ServerContext):
        self.context = context
        super().__init__(server_address, _handler_for(context))

    @property
    def base_url(self) -> str:
        host, port = self.server_address[:2]
        return f"http://{host}:{port}"


def serve_in_thread(context: ServerContext, host: str = "127.0.0.1", port: int = 0) -> tuple[BrowserHttpServer, threading.Thread]:
    server = BrowserHttpServer((host, port), context)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _handler_for(context: ServerContext) -> type[BaseHTTPRequestHandler]:
    class BrowserRequestHandler(BaseHTTPRequestHandler):
        server_version = "DaVinciMediaBrowser/0.1"

        def do_OPTIONS(self) -> None:  # noqa: N802 - stdlib callback
            if not self._host_allowed():
                self._send_json(403, {"error": "forbidden_host"})
                return
            self.send_response(204)
            self._send_cors_headers()
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802 - stdlib callback
            if not self._host_allowed():
                self._send_json(403, {"error": "forbidden_host"})
                return
            parsed = urlparse(self.path)
            if parsed.path in {"/", "/index.html", "/app.js", "/styles.css", "/api-key-guide.html"}:
                self._handle_static(parsed.path)
                return
            if not self._authorized():
                self._send_json(401, {"error": "unauthorized"})
                return
            try:
                if parsed.path == "/health":
                    self._send_json(200, {"ok": True})
                elif parsed.path == "/search":
                    self._handle_search(parsed.query)
                elif parsed.path == "/thumbnail":
                    self._handle_thumbnail(parsed.query)
                elif parsed.path == "/settings":
                    self._handle_get_settings()
                elif parsed.path == "/api-keys":
                    self._handle_get_api_keys()
                elif parsed.path == "/tasks":
                    self._handle_get_tasks()
                elif parsed.path == "/download/events":
                    self._handle_download_events(parsed.query)
                else:
                    self._send_json(404, {"error": "not_found"})
            except Exception as exc:
                self._send_json(500, {"error": str(exc)})

        def _handle_static(self, path: str) -> None:
            static_root = Path(__file__).resolve().parents[1] / "web"
            filename = "index.html" if path in {"/", "/index.html"} else path.lstrip("/")
            file_path = static_root / filename
            if not file_path.exists() or not file_path.is_file():
                self._send_json(404, {"error": "not_found"})
                return
            body = file_path.read_bytes()
            content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:  # noqa: N802 - stdlib callback
            if not self._host_allowed():
                self._send_json(403, {"error": "forbidden_host"})
                return
            if not self._authorized():
                self._send_json(401, {"error": "unauthorized"})
                return
            parsed = urlparse(self.path)
            try:
                if parsed.path == "/settings":
                    self._handle_post_settings()
                elif parsed.path == "/api-keys":
                    self._handle_post_api_keys()
                elif parsed.path == "/validate-key":
                    self._handle_validate_key()
                elif parsed.path == "/tasks":
                    self._handle_post_tasks()
                elif parsed.path == "/license/evaluate":
                    self._handle_license_evaluate()
                elif parsed.path == "/download":
                    self._handle_download()
                elif parsed.path == "/cancel":
                    self._handle_cancel()
                elif parsed.path == "/import":
                    self._handle_import()
                else:
                    self._send_json(404, {"error": "not_found"})
            except Exception as exc:
                self._send_json(500, {"error": str(exc)})

        def _handle_search(self, query_string: str) -> None:
            params = parse_qs(query_string)
            query = _param(params, "query", "").strip()
            category = _param(params, "category", "all")
            page = _int_param(params, "page", 1)
            per_page = _int_param(params, "per_page", 20)
            license_filter = _param(params, "license_filter", "all")
            if not query:
                self._send_json(400, {"error": "query_required"})
                return

            effective_query = translate_query_to_english(query)
            result = context.router.search_with_errors(
                effective_query,
                category=category,
                page=page,
                per_page=per_page,
            )
            filtered = filter_assets_by_license(result.assets, license_filter)
            self._send_json(
                200,
                {
                    "query": query,
                    "effective_query": effective_query,
                    "translated": effective_query.lower() != query.lower(),
                    "category": category,
                    "license_filter": license_filter,
                    "total": len(result.assets),
                    "shown": len(filtered),
                    "assets": [_asset_payload(asset) for asset in filtered],
                    "warnings": [
                        {"source": error.source, "message": error.message}
                        for error in result.errors
                    ],
                },
            )

        def _handle_thumbnail(self, query_string: str) -> None:
            params = parse_qs(query_string)
            url = _param(params, "url", "")
            if not url:
                self._send_json(400, {"error": "url_required"})
                return
            response = request_bytes(url, timeout=20.0)
            content_type = response.headers.get("Content-Type", "application/octet-stream")
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(response.body)))
            self.end_headers()
            self.wfile.write(response.body)

        def _handle_get_settings(self) -> None:
            data = context.settings.read()
            self._send_json(
                200,
                {
                    "settings": data,
                    "show_license_notice": context.settings.should_show_license_notice(),
                },
            )

        def _handle_post_settings(self) -> None:
            payload = self._read_json()
            current = context.settings.read()
            update = payload.get("settings")
            if not isinstance(update, dict):
                update = {
                    key: value
                    for key, value in payload.items()
                    if key != "suppress_license_notice_days"
                }
            if isinstance(update, dict):
                current.update(update)
            days = payload.get("suppress_license_notice_days")
            if isinstance(days, int):
                context.settings.write(current)
                context.settings.suppress_license_notice_for_days(days)
                current = context.settings.read()
            else:
                context.settings.write(current)
            self._send_json(
                200,
                {
                    "settings": current,
                    "show_license_notice": context.settings.should_show_license_notice(),
                },
            )

        def _handle_get_api_keys(self) -> None:
            config = context.config
            any_configured = any(
                [
                    config.pexels_api_key,
                    config.pixabay_api_key,
                    config.freesound_client_id,
                    config.freesound_api_key,
                    config.freesound_oauth_access_token,
                ]
            )
            settings = context.settings.read()
            self._send_json(
                200,
                {
                    "configured": {
                        "pexels_api_key": bool(config.pexels_api_key),
                        "pixabay_api_key": bool(config.pixabay_api_key),
                        "freesound_client_id": bool(config.freesound_client_id),
                        "freesound_api_key": bool(config.freesound_api_key),
                        "freesound_oauth_access_token": bool(config.freesound_oauth_access_token),
                        "mixkit_enabled": bool(config.mixkit_enabled),
                    },
                    "masked": {
                        "pexels_api_key": _mask_secret(config.pexels_api_key),
                        "pixabay_api_key": _mask_secret(config.pixabay_api_key),
                        "freesound_client_id": _mask_secret(config.freesound_client_id),
                        "freesound_api_key": _mask_secret(config.freesound_api_key),
                        "freesound_oauth_access_token": _mask_secret(config.freesound_oauth_access_token),
                    },
                    "prompt_required": not any_configured and not bool(settings.get("api_keys_prompted")),
                    "config_path": str(config.config_path),
                },
            )

        def _handle_post_api_keys(self) -> None:
            payload = self._read_json()
            updates = payload.get("keys")
            deletes = payload.get("delete")
            if not isinstance(updates, dict):
                updates = {}
            if not isinstance(deletes, dict):
                deletes = {}

            errors = _validate_key_updates(updates, deletes)
            if errors:
                self._send_json(400, {"error": "api_key_validation_failed", "errors": errors})
                return

            new_config = update_key_config(str(context.config.config_path), updates, deletes)
            context.config = new_config
            context.router = SearchRouter.from_config(new_config)

            settings = context.settings.read()
            settings["api_keys_prompted"] = True
            context.settings.write(settings)

            self._send_json(
                200,
                {
                    "ok": True,
                    "message": "API keys saved.",
                    "configured": {
                        "pexels_api_key": bool(new_config.pexels_api_key),
                        "pixabay_api_key": bool(new_config.pixabay_api_key),
                        "freesound_client_id": bool(new_config.freesound_client_id),
                        "freesound_api_key": bool(new_config.freesound_api_key),
                        "freesound_oauth_access_token": bool(new_config.freesound_oauth_access_token),
                        "mixkit_enabled": bool(new_config.mixkit_enabled),
                    },
                },
            )

        def _handle_validate_key(self) -> None:
            payload = self._read_json()
            field = str(payload.get("field", ""))
            value = str(payload.get("value", "")).strip()
            if not value or value.startswith("••••") or value.startswith("****"):
                self._send_json(200, {"ok": False, "field": field, "error": "empty"})
                return
            error = ""
            try:
                if field == "pexels_api_key":
                    PexelsAdapter(value).search("test", AssetKind.IMAGE, per_page=1)
                elif field == "pixabay_api_key":
                    PixabayAdapter(value).search("test", AssetKind.IMAGE, per_page=3)
                elif field == "freesound_api_key":
                    FreesoundAdapter(value).search("whoosh", AssetKind.SFX, per_page=1)
                elif field == "freesound_oauth_access_token":
                    FreesoundAdapter("", oauth_access_token=value).search("whoosh", AssetKind.SFX, per_page=1)
                elif field == "freesound_client_id":
                    # Client ID alone is not callable; accept any non-empty value.
                    pass
                else:
                    self._send_json(400, {"ok": False, "field": field, "error": "unknown_field"})
                    return
            except Exception as exc:
                error = str(exc)
            self._send_json(200, {"ok": not error, "field": field, "error": error})

        def _handle_get_tasks(self) -> None:
            tasks = context.settings.read().get("download_tasks", [])
            if not isinstance(tasks, list):
                tasks = []
            self._send_json(200, {"tasks": tasks[:80]})

        def _handle_post_tasks(self) -> None:
            payload = self._read_json()
            tasks = payload.get("tasks")
            if not isinstance(tasks, list):
                self._send_json(400, {"error": "tasks_required"})
                return
            current = context.settings.read()
            current["download_tasks"] = tasks[:80]
            context.settings.write(current)
            self._send_json(200, {"tasks": current["download_tasks"]})

        def _handle_license_evaluate(self) -> None:
            payload = self._read_json()
            assets = [_asset_from_dict(item) for item in payload.get("assets", []) if isinstance(item, dict)]
            decision = context.license_service.evaluate(assets)
            self._send_json(
                200,
                {
                    "allowed": decision.allowed,
                    "requires_confirmation": decision.requires_confirmation,
                    "title": decision.title,
                    "message": decision.message,
                },
            )

        def _handle_download(self) -> None:
            payload = self._read_json()
            asset_data = payload.get("asset")
            if not isinstance(asset_data, dict):
                self._send_json(400, {"error": "asset_required"})
                return
            job = context.ensure_downloads().start(_asset_from_dict(asset_data))
            self._send_json(202, {"job_id": job.id, "state": job.state})

        def _handle_download_events(self, query_string: str) -> None:
            params = parse_qs(query_string)
            job_id = _param(params, "job_id", "")
            job = context.ensure_downloads().get(job_id)
            if not job:
                self._send_json(404, {"error": "job_not_found"})
                return
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            while True:
                try:
                    event = job.events.get(timeout=20.0)
                except queue.Empty:
                    event = {"job_id": job.id, "type": "heartbeat"}
                self._write_sse(event)
                if event.get("type") in TERMINAL_EVENTS:
                    self.close_connection = True
                    break

        def _handle_cancel(self) -> None:
            payload = self._read_json()
            job_id = str(payload.get("job_id", ""))
            cancelled = context.ensure_downloads().cancel(job_id)
            self._send_json(200, {"cancelled": cancelled})

        def _handle_import(self) -> None:
            payload = self._read_json()
            assets = [_asset_from_dict(item) for item in payload.get("assets", []) if isinstance(item, dict)]
            if not assets:
                self._send_json(400, {"error": "assets_required"})
                return
            decision = context.license_service.evaluate(assets)
            if not decision.allowed:
                self._send_json(
                    403,
                    {
                        "error": "license_blocked",
                        "title": decision.title,
                        "message": decision.message,
                    },
                )
                return
            raw_paths = payload.get("paths")
            if isinstance(raw_paths, list) and raw_paths:
                paths = [Path(str(path)) for path in raw_paths]
            else:
                paths = [context.downloader.download(asset) for asset in assets]
            try:
                imported = ResolveBridge().import_media(paths, assets)
                self._send_json(
                    200,
                    {
                        "imported_count": len(imported),
                        "paths": [str(path) for path in paths],
                        "resolve_available": True,
                    },
                )
            except ResolveUnavailable as exc:
                self._send_json(
                    200,
                    {
                        "imported_count": 0,
                        "paths": [str(path) for path in paths],
                        "resolve_available": False,
                        "warning": str(exc),
                    },
                )

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0") or 0)
            if length <= 0:
                return {}
            raw = self.rfile.read(length).decode("utf-8")
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}

        def _host_allowed(self) -> bool:
            # Reject non-loopback Host headers so a malicious website cannot use
            # DNS rebinding to reach this local-only service through the browser.
            host = self.headers.get("Host", "")
            hostname = host.rsplit(":", 1)[0].strip("[]").lower() if host else ""
            return hostname in {"", "127.0.0.1", "localhost", "::1"}

        def _authorized(self) -> bool:
            auth = self.headers.get("Authorization", "")
            if auth == f"Bearer {context.token}":
                return True
            params = parse_qs(urlparse(self.path).query)
            return _param(params, "token", "") == context.token

        def _send_json(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_cors_headers(self) -> None:
            # Intentionally no Access-Control-Allow-Origin: the page and the API
            # share the same loopback origin, so same-origin requests work without
            # CORS while cross-origin reads stay blocked by the browser.
            return

        def _write_sse(self, event: dict[str, Any]) -> None:
            kind = str(event.get("type", "message"))
            data = json.dumps(event, ensure_ascii=False)
            message = f"event: {kind}\ndata: {data}\n\n".encode("utf-8")
            try:
                self.wfile.write(message)
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                return

        def log_message(self, *_args: object) -> None:
            return

    return BrowserRequestHandler


def _asset_payload(asset: Asset) -> dict[str, Any]:
    data = asset.to_dict()
    data.update(
        {
            "requires_attribution": asset.requires_attribution,
            "is_non_commercial": asset.is_non_commercial,
            "is_attribution_free": asset.is_attribution_free,
            "license_badge": asset.license_badge,
            "resolve_metadata": build_resolve_metadata(asset),
        }
    )
    return data


def _asset_from_dict(data: dict[str, Any]) -> Asset:
    payload = dict(data)
    payload.pop("requires_attribution", None)
    payload.pop("is_non_commercial", None)
    payload.pop("is_attribution_free", None)
    payload.pop("license_badge", None)
    payload.pop("resolve_metadata", None)
    try:
        payload["kind"] = AssetKind(str(payload.get("kind", AssetKind.IMAGE.value)))
    except ValueError:
        payload["kind"] = AssetKind.IMAGE

    allowed = set(Asset.__dataclass_fields__.keys())
    clean = {key: value for key, value in payload.items() if key in allowed}
    clean.setdefault("id", "")
    clean.setdefault("source", "")
    clean.setdefault("title", "")
    return Asset(**clean)


def _validate_key_updates(updates: dict[str, Any], deletes: dict[str, bool]) -> dict[str, str]:
    errors: dict[str, str] = {}

    pexels_key = _posted_secret(updates, "pexels_api_key")
    pixabay_key = _posted_secret(updates, "pixabay_api_key")
    freesound_key = _posted_secret(updates, "freesound_api_key")
    freesound_oauth = _posted_secret(updates, "freesound_oauth_access_token")

    if pexels_key and not deletes.get("pexels_api_key"):
        try:
            PexelsAdapter(pexels_key).search("test", AssetKind.IMAGE, per_page=1)
        except Exception as exc:
            errors["pexels_api_key"] = str(exc)

    if pixabay_key and not deletes.get("pixabay_api_key"):
        try:
            PixabayAdapter(pixabay_key).search("test", AssetKind.IMAGE, per_page=3)
        except Exception as exc:
            errors["pixabay_api_key"] = str(exc)

    if (freesound_key and not deletes.get("freesound_api_key")) or (
        freesound_oauth and not deletes.get("freesound_oauth_access_token")
    ):
        try:
            FreesoundAdapter(
                "" if deletes.get("freesound_api_key") else freesound_key,
                oauth_access_token="" if deletes.get("freesound_oauth_access_token") else freesound_oauth,
            ).search("whoosh", AssetKind.SFX, per_page=1)
        except Exception as exc:
            errors["freesound"] = str(exc)

    return errors


def _posted_secret(updates: dict[str, Any], key: str) -> str:
    value = str(updates.get(key, "")).strip()
    if value.startswith("••••") or value.startswith("****"):
        return ""
    return value


def _mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "••••" + value[-2:]
    return value[:4] + "••••" + value[-4:]


def _param(params: dict[str, list[str]], key: str, default: str) -> str:
    values = params.get(key)
    if not values:
        return default
    return values[0]


def _int_param(params: dict[str, list[str]], key: str, default: int) -> int:
    try:
        return int(_param(params, key, str(default)))
    except ValueError:
        return default
