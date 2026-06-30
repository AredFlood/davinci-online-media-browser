from __future__ import annotations

import ipaddress
import json
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping


DEFAULT_USER_AGENT = "DaVinciOnlineMediaBrowser/0.1 (+local Resolve workflow plugin)"
STRICT_SSL_ENV = "DAVINCI_ONLINE_BROWSER_STRICT_SSL"
_ALLOWED_SCHEMES = {"http", "https"}


class UnsafeURLError(RuntimeError):
    """Raised when a URL is blocked by the SSRF / local-file guard."""


def _is_blocked_host(host: str) -> bool:
    host = host.strip().strip("[]").rstrip(".").lower()
    if not host or host == "localhost" or host.endswith(".local") or host.endswith(".internal"):
        return True
    # Block literal internal/loopback/link-local IPs (covers file-less SSRF like
    # http://127.0.0.1, http://10.x, http://169.254.169.254 metadata, etc.).
    # A hostname that *resolves* to an internal address (DNS-rebinding style SSRF)
    # is a documented residual risk; see SECURITY.md.
    try:
        ip = ipaddress.ip_address(host.split("%")[0])
    except ValueError:
        return False
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def assert_fetchable(url: str) -> None:
    """Block non-http(s) schemes (file:, ftp:, data:) and internal/loopback hosts.

    Outbound fetches are driven by client-supplied URLs (thumbnails, asset
    download links), so this prevents the local service from being abused as an
    SSRF proxy or to read local files.
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        raise UnsafeURLError(f"Blocked URL scheme: {parsed.scheme or '(none)'}")
    if not parsed.hostname:
        raise UnsafeURLError("Blocked URL with no host")
    if _is_blocked_host(parsed.hostname):
        raise UnsafeURLError(f"Blocked internal/loopback host: {parsed.hostname}")


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Re-validate every redirect hop so a public URL can't be bounced to
    file:// or an internal host (urllib already blocks redirects to file://,
    this also blocks redirects to internal IPs)."""

    def __init__(self, allow_internal: bool = False):
        super().__init__()
        self._allow_internal = allow_internal

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401 - stdlib signature
        if not self._allow_internal:
            assert_fetchable(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)

# Signature for streaming progress callbacks: (bytes_done, total_bytes_or_zero).
ProgressCallback = Callable[[int, int], None]
# Returns True to abort an in-flight download.
CancelCheck = Callable[[], bool]


class DownloadCancelled(RuntimeError):
    """Raised by download_to_file when the cancel check requests an abort."""


@dataclass(slots=True)
class HttpResponse:
    url: str
    status: int
    headers: Mapping[str, str]
    body: bytes

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")

    def json(self) -> object:
        return json.loads(self.text)


def build_url(base_url: str, params: Mapping[str, object | None]) -> str:
    filtered = {key: value for key, value in params.items() if value not in (None, "")}
    query = urllib.parse.urlencode(filtered)
    if not query:
        return base_url
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{query}"


def request_bytes(
    url: str,
    *,
    headers: Mapping[str, str] | None = None,
    timeout: float = 20.0,
    attempts: int = 3,
    allow_internal_hosts: bool = False,
) -> HttpResponse:
    merged_headers = {"User-Agent": DEFAULT_USER_AGENT}
    if headers:
        merged_headers.update(headers)
    request = urllib.request.Request(url, headers=merged_headers)
    last_error: Exception | None = None
    for attempt in range(1, max(1, attempts) + 1):
        try:
            with _urlopen(request, timeout=timeout, allow_internal=allow_internal_hosts) as response:
                body = response.read()
                return HttpResponse(
                    url=response.geturl(),
                    status=response.status,
                    headers=dict(response.headers.items()),
                    body=body,
                )
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if exc.code < 500:
                raise RuntimeError(f"HTTP {exc.code} for {url}: {detail[:500]}") from exc
            last_error = RuntimeError(f"HTTP {exc.code} for {url}: {detail[:500]}")
        except urllib.error.URLError as exc:
            last_error = RuntimeError(f"Network error for {url}: {exc.reason}")
        if attempt < attempts:
            time.sleep(0.35 * attempt)
    if last_error:
        raise last_error
    raise RuntimeError(f"Network request failed for {url}")


def request_json(
    url: str,
    *,
    headers: Mapping[str, str] | None = None,
    timeout: float = 20.0,
) -> object:
    return request_bytes(url, headers=headers, timeout=timeout).json()


def download_to_file(
    url: str,
    dest: Path,
    *,
    headers: Mapping[str, str] | None = None,
    timeout: float = 120.0,
    attempts: int = 3,
    chunk_size: int = 65536,
    progress: ProgressCallback | None = None,
    cancel: CancelCheck | None = None,
    allow_internal_hosts: bool = False,
) -> int:
    """Stream ``url`` to ``dest`` in chunks, reporting progress and honouring cancel.

    Writes to a ``.part`` sidecar first and atomically renames on success so a
    cancelled or failed download never leaves a truncated file at ``dest``.
    Returns the number of bytes written. Raises :class:`DownloadCancelled` if the
    cancel check returns True before the transfer completes.
    """
    merged_headers = {"User-Agent": DEFAULT_USER_AGENT}
    if headers:
        merged_headers.update(headers)
    part_path = dest.with_name(dest.name + ".part")
    last_error: Exception | None = None

    for attempt in range(1, max(1, attempts) + 1):
        if cancel and cancel():
            raise DownloadCancelled(f"Download cancelled before start: {url}")
        request = urllib.request.Request(url, headers=merged_headers)
        try:
            with _urlopen(request, timeout=timeout, allow_internal=allow_internal_hosts) as response:
                total = _content_length(response)
                written = 0
                if progress:
                    progress(0, total)
                with part_path.open("wb") as handle:
                    while True:
                        if cancel and cancel():
                            handle.close()
                            part_path.unlink(missing_ok=True)
                            raise DownloadCancelled(f"Download cancelled: {url}")
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        handle.write(chunk)
                        written += len(chunk)
                        if progress:
                            progress(written, total)
                part_path.replace(dest)
                return written
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            part_path.unlink(missing_ok=True)
            if exc.code < 500:
                raise RuntimeError(f"HTTP {exc.code} for {url}: {detail[:500]}") from exc
            last_error = RuntimeError(f"HTTP {exc.code} for {url}: {detail[:500]}")
        except urllib.error.URLError as exc:
            part_path.unlink(missing_ok=True)
            last_error = RuntimeError(f"Network error for {url}: {exc.reason}")
        if attempt < attempts:
            time.sleep(0.35 * attempt)
    if last_error:
        raise last_error
    raise RuntimeError(f"Network request failed for {url}")


def _urlopen(request: urllib.request.Request, *, timeout: float, allow_internal: bool = False):
    """Open a URL with verified TLS, with a Resolve/macOS CA fallback.

    Blocks non-http(s) schemes and internal/loopback hosts (SSRF / local-file
    guard) unless ``allow_internal`` is set. Some Resolve-launched Python runtimes
    on macOS cannot find a CA bundle even though the same URLs work in browsers,
    so strict verification is tried first and only certificate-chain failures fall
    back to an unverified context (disable with
    ``DAVINCI_ONLINE_BROWSER_STRICT_SSL=1``).
    """
    if not allow_internal:
        assert_fetchable(request.full_url)
    try:
        return _open(request, timeout=timeout, context=_verified_ssl_context(), allow_internal=allow_internal)
    except urllib.error.URLError as exc:
        if _allow_insecure_ssl_fallback() and _is_certificate_verify_error(exc):
            _warn_insecure_tls(request.full_url)
            return _open(request, timeout=timeout, context=_unverified_ssl_context(), allow_internal=allow_internal)
        raise


def _open(request: urllib.request.Request, *, timeout: float, context: ssl.SSLContext, allow_internal: bool = False):
    # A per-call opener whose redirect handler re-validates each hop.
    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=context),
        _SafeRedirectHandler(allow_internal=allow_internal),
    )
    return opener.open(request, timeout=timeout)


_warned_insecure_hosts: set[str] = set()


def _warn_insecure_tls(url: str) -> None:
    import sys

    host = urllib.parse.urlparse(url).hostname or url
    if host in _warned_insecure_hosts:
        return
    _warned_insecure_hosts.add(host)
    print(
        f"[security] TLS certificate verification failed for {host}; retrying without "
        f"verification. Install 'certifi' (pip install certifi) or set {STRICT_SSL_ENV}=1 "
        f"to require strict TLS.",
        file=sys.stderr,
    )


def _verified_ssl_context() -> ssl.SSLContext:
    try:
        import certifi  # type: ignore[import-not-found]

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _unverified_ssl_context() -> ssl.SSLContext:
    context = ssl._create_unverified_context()  # noqa: SLF001 - intentional TLS fallback
    context.check_hostname = False
    return context


def _allow_insecure_ssl_fallback() -> bool:
    return os.environ.get(STRICT_SSL_ENV, "").strip().lower() not in {"1", "true", "yes", "on"}


def _is_certificate_verify_error(error: urllib.error.URLError) -> bool:
    reason = getattr(error, "reason", error)
    if isinstance(reason, ssl.SSLCertVerificationError):
        return True
    message = str(reason).lower()
    return "certificate_verify_failed" in message or "certificate verify failed" in message


def _content_length(response: object) -> int:
    try:
        value = response.headers.get("Content-Length")  # type: ignore[attr-defined]
        return int(value) if value else 0
    except (TypeError, ValueError, AttributeError):
        return 0
