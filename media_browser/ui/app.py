from __future__ import annotations

import sys
import traceback

from ..config import load_config
from ..models import Asset, AssetKind
from ..search import SearchRouter
from ..services.cache import CacheManager
from ..services.downloader import DownloadCancelled, DownloadError, Downloader
from ..services.licenses import LICENSE_FILTERS, LicenseService, filter_assets_by_license
from ..services.resolve_bridge import ResolveBridge, ResolveUnavailable
from ..services.settings import SettingsStore
from ..services.translate import translate_query_to_english
from ..utils.http import request_bytes
from .cards import make_card_pixmap, make_placeholder_pixmap
from .i18n import LANGUAGES, tr
from .preview import PreviewPanel
from .theme import SCIFI_STYLESHEET
from .qt_compat import (
    QApplication,
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QIcon,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSize,
    QSplitter,
    QStatusBar,
    QTextEdit,
    QThread,
    Qt,
    QVBoxLayout,
    QWidget,
    Signal,
)


THUMB_SIZE = QSize(180, 112)
THUMBNAIL_WORKERS = 4

# (value, i18n key) — labels are resolved per language at build/retranslate time.
CATEGORY_VALUES = ["all", "auto", "video", "image", "music", "sfx", "3d"]
LICENSE_VALUES = [value for value, _label in LICENSE_FILTERS]


class SearchWorker(QThread):
    # assets, errors, effective_query (post-translation)
    finished_ok = Signal(list, list, str)
    failed = Signal(str)

    def __init__(self, router: SearchRouter, query: str, category: str):
        super().__init__()
        self.router = router
        self.query = query
        self.category = category

    def run(self) -> None:
        try:
            effective = translate_query_to_english(self.query)
            result = self.router.search_with_errors(effective, category=self.category, per_page=20)
            self.finished_ok.emit(result.assets, result.errors, effective)
        except Exception:
            self.failed.emit(traceback.format_exc())


class ThumbnailWorker(QThread):
    """Fetches thumbnail bytes for a subset of result rows on a background thread.

    Emits ``ready(generation, row_index, data)``. The generation token lets the
    window ignore results from a superseded search/filter pass.
    """

    ready = Signal(int, int, bytes)

    def __init__(self, generation: int, jobs: list[tuple[int, str]]):
        super().__init__()
        self.generation = generation
        self.jobs = jobs
        self._stopped = False

    def stop(self) -> None:
        self._stopped = True

    def run(self) -> None:
        for row_index, url in self.jobs:
            if self._stopped:
                return
            try:
                # Bounded timeout so a hung fetch can't block window close for long.
                data = request_bytes(url, timeout=10.0).body
            except Exception:
                continue
            if self._stopped:
                return
            self.ready.emit(self.generation, row_index, data)


class ImportWorker(QThread):
    file_started = Signal(int, int, str)   # row index, total files, title
    file_progress = Signal(int, int)       # bytes done, bytes total (0 if unknown)
    finished_ok = Signal(int, list)
    failed = Signal(str)
    cancelled = Signal(list)               # paths downloaded before cancel

    def __init__(self, downloader: Downloader, assets: list[Asset]):
        super().__init__()
        self.downloader = downloader
        self.assets = assets
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def _is_cancelled(self) -> bool:
        return self._cancel

    def run(self) -> None:
        paths: list = []
        try:
            total = len(self.assets)
            for index, asset in enumerate(self.assets):
                if self._cancel:
                    self.cancelled.emit([str(path) for path in paths])
                    return
                self.file_started.emit(index, total, asset.display_title)
                path = self.downloader.download(
                    asset,
                    progress=self._emit_progress,
                    cancel=self._is_cancelled,
                )
                paths.append(path)
            if self._cancel:
                self.cancelled.emit([str(path) for path in paths])
                return
            try:
                imported = ResolveBridge().import_media(paths, self.assets)
                self.finished_ok.emit(len(imported), [str(path) for path in paths])
            except ResolveUnavailable:
                self.finished_ok.emit(0, [str(path) for path in paths])
        except DownloadCancelled:
            self.cancelled.emit([str(path) for path in paths])
        except (DownloadError, Exception) as exc:
            self.failed.emit(str(exc))

    def _emit_progress(self, done: int, total: int) -> None:
        self.file_progress.emit(done, total)


class MainWindow(QMainWindow):
    def __init__(self, config_path: str | None = None):
        super().__init__()
        self.config = load_config(config_path)
        self.router = SearchRouter.from_config(self.config)
        self.cache = CacheManager(self.config.cache_dir)
        self.downloader = Downloader(self.cache)
        self.license_service = LicenseService(self.config.license_policy)
        self.settings = SettingsStore.default()
        self.all_assets: list[Asset] = []
        self.assets: list[Asset] = []
        self.search_worker: SearchWorker | None = None
        self.import_worker: ImportWorker | None = None
        self.thumb_workers: list[ThumbnailWorker] = []
        self.thumb_cache: dict[tuple[str, str], bytes] = {}
        # All QThreads are tracked here until they emit finished, so a running
        # thread's Python wrapper is never garbage-collected (that aborts the app).
        self._live_threads: list[QThread] = []
        self._result_generation = 0
        self._import_index = 0
        self._import_total = 0
        self._search_errors: list[object] = []
        self._last_query_pair: tuple[str, str] = ("", "")
        lang = str(self.settings.read().get("language", "zh"))
        self._lang = lang if lang in {code for code, _ in LANGUAGES} else "zh"

        self.setWindowTitle("✦ DaVinci 在线素材浏览器  ·  Online Media Browser")
        self.resize(1180, 760)
        self._build_ui()
        self._apply_styles()
        self._retranslate()

    def tr_text(self, key: str, **kwargs) -> str:
        return tr(self._lang, key, **kwargs)

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("Root")
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        top_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.returnPressed.connect(self.search)
        self.category_combo = QComboBox()
        for value in CATEGORY_VALUES:
            self.category_combo.addItem(value, value)
        self.license_combo = QComboBox()
        for value in LICENSE_VALUES:
            self.license_combo.addItem(value, value)
        self.license_combo.currentIndexChanged.connect(self._apply_license_filter)
        self.language_combo = QComboBox()
        for code, label in LANGUAGES:
            self.language_combo.addItem(label, code)
        self.language_combo.setCurrentIndex(
            max(0, [code for code, _ in LANGUAGES].index(self._lang))
        )
        self.language_combo.currentIndexChanged.connect(self._change_language)
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search)

        self.type_label = QLabel()
        self.license_label = QLabel()
        self.language_label = QLabel()
        top_row.addWidget(self.search_input, 1)
        top_row.addWidget(self.type_label)
        top_row.addWidget(self.category_combo)
        top_row.addWidget(self.license_label)
        top_row.addWidget(self.license_combo)
        top_row.addWidget(self.language_label)
        top_row.addWidget(self.language_combo)
        top_row.addWidget(self.search_button)
        root.addLayout(top_row)

        self.busy_bar = QProgressBar()
        self.busy_bar.setObjectName("BusyBar")
        self.busy_bar.setRange(0, 0)  # indeterminate
        self.busy_bar.setTextVisible(False)
        self.busy_bar.setMaximumHeight(3)
        self.busy_bar.hide()
        root.addWidget(self.busy_bar)

        splitter = QSplitter(Qt.Horizontal)
        self.results_list = QListWidget()
        self.results_list.setViewMode(QListWidget.IconMode)
        self.results_list.setIconSize(QSize(180, 112))
        self.results_list.setGridSize(QSize(210, 176))
        self.results_list.setResizeMode(QListWidget.Adjust)
        self.results_list.setMovement(QListWidget.Static)
        self.results_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.results_list.itemSelectionChanged.connect(self._update_details)
        splitter.addWidget(self.results_list)

        details_panel = QWidget()
        details_layout = QVBoxLayout(details_panel)
        self.details_title = QLabel("No asset selected")
        self.details_title.setWordWrap(True)
        self.preview_panel = PreviewPanel()
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.import_button = QPushButton("Import to Media Pool")
        self.import_button.clicked.connect(self.import_selected)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.hide()
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self._cancel_import)
        self.cancel_button.hide()
        progress_row = QHBoxLayout()
        progress_row.addWidget(self.progress_bar, 1)
        progress_row.addWidget(self.cancel_button)

        details_layout.addWidget(self.details_title)
        details_layout.addWidget(self.preview_panel)
        details_layout.addWidget(self.details_text, 1)
        details_layout.addLayout(progress_row)
        details_layout.addWidget(self.import_button)
        splitter.addWidget(details_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, 1)

        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage(f"Config: {self.config.config_path}")

    def _apply_styles(self) -> None:
        self.setStyleSheet(SCIFI_STYLESHEET)

    def search(self) -> None:
        query = self.search_input.text().strip()
        if not query:
            QMessageBox.information(self, self.tr_text("search"), self.tr_text("enter_term"))
            return
        if self.search_worker is not None and self.search_worker.isRunning():
            return
        category = self.category_combo.currentData()
        self.search_button.setEnabled(False)
        self.results_list.clear()
        self.preview_panel.load_asset(None)
        self.details_title.setText(self.tr_text("searching"))
        self.details_text.clear()
        self.statusBar().showMessage(self.tr_text("searching_sources"))
        self._set_busy(True)
        self.search_worker = SearchWorker(self.router, query, category)
        self.search_worker.finished_ok.connect(self._search_finished)
        self.search_worker.failed.connect(self._search_failed)
        self._keep_alive(self.search_worker)
        self.search_worker.start()

    def _search_finished(self, assets: list[Asset], errors: list[object], effective_query: str) -> None:
        self.search_button.setEnabled(True)
        self._set_busy(False)
        self.all_assets = assets
        self._search_errors = errors
        self._last_query_pair = (self.search_input.text().strip(), effective_query)
        self._populate_results()

    def _apply_license_filter(self) -> None:
        if self.all_assets:
            self._populate_results()

    def _populate_results(self) -> None:
        mode = self.license_combo.currentData()
        self.assets = filter_assets_by_license(self.all_assets, mode)
        self._stop_thumbnail_workers()
        self._result_generation += 1
        self.results_list.clear()
        for index, asset in enumerate(self.assets):
            item = QListWidgetItem()
            item.setText(self._item_text(asset))
            item.setData(Qt.UserRole, index)
            item.setToolTip(self._details_text(asset))
            item.setIcon(self._card_icon(asset))
            self.results_list.addItem(item)
        self._start_thumbnail_loading()
        self._update_result_status()

    def _update_result_status(self) -> None:
        errors = self._search_errors
        total = len(self.all_assets)
        shown = len(self.assets)
        if shown != total:
            status = self.tr_text("results_filtered", shown=shown, total=total)
        else:
            status = self.tr_text("results", shown=shown)
        src, dst = self._last_query_pair
        if dst and src and dst.lower() != src.lower():
            status += self.tr_text("translated", src=src, dst=dst)
        if errors:
            status += f"  ·  {len(errors)} warnings"
        self.statusBar().showMessage(status)
        if errors and not shown:
            self.details_title.setText(self.tr_text("source_warnings"))
            self.details_text.setText(
                "\n".join(f"{error.source}: {error.message}" for error in errors)
            )
        elif shown:
            self.details_title.setText(self.tr_text("select_asset"))
            self.details_text.clear()
        elif total:
            self.details_title.setText(self.tr_text("no_filter_match"))
            self.details_text.setText(self.tr_text("no_filter_match_hint"))
        else:
            self.details_title.setText(self.tr_text("no_results"))
            self.details_text.setText(self.tr_text("no_results_hint"))

    def _card_icon(self, asset: Asset) -> QIcon:
        data = self.thumb_cache.get((asset.source, asset.id))
        if data:
            return QIcon(make_card_pixmap(data, asset, THUMB_SIZE))
        return QIcon(make_placeholder_pixmap(asset, THUMB_SIZE))

    def _start_thumbnail_loading(self) -> None:
        # Drop references to finished workers; keep running ones alive so a
        # still-running QThread is never garbage-collected mid-flight.
        self.thumb_workers = [worker for worker in self.thumb_workers if worker.isRunning()]
        jobs: list[tuple[int, str]] = []
        for index, asset in enumerate(self.assets):
            if (asset.source, asset.id) in self.thumb_cache:
                continue
            url = asset.thumbnail_url
            if not url and asset.kind == AssetKind.IMAGE:
                url = asset.preview_url
            if url:
                jobs.append((index, url))
        if not jobs:
            return
        bucket_count = min(THUMBNAIL_WORKERS, len(jobs))
        buckets: list[list[tuple[int, str]]] = [[] for _ in range(bucket_count)]
        for offset, job in enumerate(jobs):
            buckets[offset % bucket_count].append(job)
        for bucket in buckets:
            worker = ThumbnailWorker(self._result_generation, bucket)
            worker.ready.connect(self._on_thumbnail_ready)
            self.thumb_workers.append(worker)
            self._keep_alive(worker)
            worker.start()

    def _stop_thumbnail_workers(self) -> None:
        for worker in self.thumb_workers:
            worker.stop()

    def _on_thumbnail_ready(self, generation: int, row_index: int, data: bytes) -> None:
        if generation != self._result_generation:
            return
        if not (0 <= row_index < len(self.assets)):
            return
        asset = self.assets[row_index]
        self.thumb_cache[(asset.source, asset.id)] = data
        item = self.results_list.item(row_index)
        if item is None:
            return
        item.setIcon(QIcon(make_card_pixmap(data, asset, THUMB_SIZE)))

    def _search_failed(self, error: str) -> None:
        self.search_button.setEnabled(True)
        self._set_busy(False)
        self.statusBar().showMessage("Search failed")
        QMessageBox.critical(self, "Search failed", error)

    def _selected_assets(self) -> list[Asset]:
        selected: list[Asset] = []
        for item in self.results_list.selectedItems():
            index = item.data(Qt.UserRole)
            if isinstance(index, int) and 0 <= index < len(self.assets):
                selected.append(self.assets[index])
        return selected

    def _update_details(self) -> None:
        selected = self._selected_assets()
        if not selected:
            self.details_title.setText(self.tr_text("no_asset"))
            self.details_text.clear()
            self.preview_panel.load_asset(None)
            return
        if len(selected) > 1:
            self.details_title.setText(f"{len(selected)} assets selected")
            self.details_text.setText("\n\n".join(self._details_text(asset) for asset in selected))
            self.preview_panel.load_asset(None)
            return
        asset = selected[0]
        self.details_title.setText(asset.display_title)
        self.details_text.setText(self._details_text(asset))
        self.preview_panel.load_asset(asset)

    def import_selected(self) -> None:
        selected = self._selected_assets()
        decision = self.license_service.evaluate(selected)
        if not decision.allowed:
            QMessageBox.warning(self, decision.title, decision.message)
            return
        if decision.requires_confirmation and self.settings.should_show_license_notice():
            dialog = LicenseConfirmationDialog(decision.title, decision.message, self)
            if dialog.exec() != QDialog.Accepted:
                return
            if dialog.suppress_for_month:
                self.settings.suppress_license_notice_for_days(30)
        self.preview_panel.stop()
        self.import_button.setEnabled(False)
        self._import_index = 0
        self._import_total = len(selected)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(self.tr_text("preparing"))
        self.progress_bar.show()
        self.cancel_button.setEnabled(True)
        self.cancel_button.setText(self.tr_text("cancel"))
        self.cancel_button.show()
        self.statusBar().showMessage("Downloading and importing...")
        self.import_worker = ImportWorker(self.downloader, selected)
        self.import_worker.file_started.connect(self._on_file_started)
        self.import_worker.file_progress.connect(self._on_file_progress)
        self.import_worker.finished_ok.connect(self._import_finished)
        self.import_worker.failed.connect(self._import_failed)
        self.import_worker.cancelled.connect(self._on_import_cancelled)
        self._keep_alive(self.import_worker)
        self.import_worker.start()

    def _on_file_started(self, index: int, total: int, title: str) -> None:
        self._import_index = index
        self._import_total = total
        self.progress_bar.setFormat(f"{index + 1}/{total}  {title[:28]}  %p%")
        self.statusBar().showMessage(f"Downloading {index + 1}/{total}: {title}")

    def _on_file_progress(self, done: int, total_bytes: int) -> None:
        frac = (done / total_bytes) if total_bytes > 0 else 0.0
        files = max(1, self._import_total)
        overall = (self._import_index + frac) / files
        self.progress_bar.setValue(int(overall * 100))

    def _cancel_import(self) -> None:
        if self.import_worker:
            self.import_worker.cancel()
            self.cancel_button.setEnabled(False)
            self.cancel_button.setText(self.tr_text("cancelling"))
            self.statusBar().showMessage("Cancelling download...")

    def _reset_progress_ui(self) -> None:
        self.progress_bar.hide()
        self.progress_bar.reset()
        self.progress_bar.setFormat("%p%")
        self.cancel_button.hide()
        self.import_button.setEnabled(True)

    def _import_finished(self, imported_count: int, paths: list[str]) -> None:
        self._reset_progress_ui()
        if imported_count:
            message = f"Imported {imported_count} item(s) into the current Resolve Media Pool."
        else:
            message = "Downloaded files, but Resolve is not available from this process. Run inside Resolve to import."
        self.statusBar().showMessage(message)
        QMessageBox.information(self, "Import complete", f"{message}\n\n" + "\n".join(paths[:10]))

    def _import_failed(self, error: str) -> None:
        self._reset_progress_ui()
        self.statusBar().showMessage("Import failed")
        QMessageBox.critical(self, "Import failed", error)

    def _on_import_cancelled(self, paths: list[str]) -> None:
        self._reset_progress_ui()
        self.statusBar().showMessage("Import cancelled")
        if paths:
            QMessageBox.information(
                self, "已取消", "已取消下载。已完成的缓存文件：\n" + "\n".join(paths[:10])
            )
        else:
            QMessageBox.information(self, "已取消", "已取消下载，未保留任何文件。")

    def _item_text(self, asset: Asset) -> str:
        title = asset.display_title
        return title if len(title) <= 48 else title[:47] + "…"

    def _set_busy(self, busy: bool) -> None:
        self.busy_bar.setVisible(busy)

    # --- QThread lifetime management -------------------------------------
    def _keep_alive(self, thread: QThread) -> None:
        self._live_threads.append(thread)
        thread.finished.connect(lambda: self._discard_thread(thread))

    def _discard_thread(self, thread: QThread) -> None:
        if thread in self._live_threads:
            self._live_threads.remove(thread)
        thread.deleteLater()

    # --- language / i18n --------------------------------------------------
    def _change_language(self) -> None:
        code = self.language_combo.currentData()
        if not code or code == self._lang:
            return
        self._lang = code
        data = self.settings.read()
        data["language"] = code
        self.settings.write(data)
        self._retranslate()

    def _retranslate(self) -> None:
        self.search_input.setPlaceholderText(self.tr_text("search_placeholder"))
        self.search_button.setText(self.tr_text("search"))
        self.type_label.setText(self.tr_text("type"))
        self.license_label.setText(self.tr_text("license"))
        self.language_label.setText(self.tr_text("language"))
        self.import_button.setText(self.tr_text("import"))
        self._retranslate_combo(self.category_combo, "cat_")
        self._retranslate_combo(self.license_combo, "lic_")
        # Refresh dynamic panes that carry translatable text.
        if self.all_assets or self._search_errors:
            self._update_result_status()
        elif not self._selected_assets():
            self.details_title.setText(self.tr_text("no_asset"))

    def _retranslate_combo(self, combo: QComboBox, prefix: str) -> None:
        for i in range(combo.count()):
            value = combo.itemData(i)
            combo.setItemText(i, self.tr_text(f"{prefix}{value}"))

    def closeEvent(self, event: object) -> None:
        for worker in self.thumb_workers:
            worker.stop()
        if self.import_worker and self.import_worker.isRunning():
            self.import_worker.cancel()
        self.preview_panel.shutdown()
        # Wait fully: a finished thread returns instantly, an in-flight fetch
        # returns within its bounded timeout. This prevents "QThread destroyed
        # while still running" aborts during teardown.
        for thread in list(self._live_threads):
            thread.wait()
        super().closeEvent(event)

    def _details_text(self, asset: Asset) -> str:
        parts = [
            f"Source: {asset.source}",
            f"Type: {asset.kind.value}",
            f"Author: {asset.author or 'Unknown'}",
            f"License: {asset.license_name or 'Unknown'}",
            f"License URL: {asset.license_url}",
            f"Original URL: {asset.source_url}",
        ]
        if asset.duration is not None:
            parts.append(f"Duration: {asset.duration:.1f}s")
        if asset.width and asset.height:
            parts.append(f"Size: {asset.width} x {asset.height}")
        if asset.tags:
            parts.append(f"Tags: {', '.join(asset.tags[:12])}")
        if asset.metadata.get("download_note"):
            parts.append(str(asset.metadata["download_note"]))
        return "\n".join(parts)


class LicenseConfirmationDialog(QDialog):
    def __init__(self, title: str, message: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.suppress_for_month = False
        self.resize(560, 420)

        layout = QVBoxLayout(self)
        label = QLabel(title)
        label.setWordWrap(True)
        body = QTextEdit()
        body.setReadOnly(True)
        body.setText(message)
        self.checkbox = QCheckBox("一个月内不再提示授权确认")
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(label)
        layout.addWidget(body, 1)
        layout.addWidget(self.checkbox)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        self.suppress_for_month = self.checkbox.isChecked()
        self.accept()


def run_app(config_path: str | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow(config_path=config_path)
    window.show()
    return app.exec()
