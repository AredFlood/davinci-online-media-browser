from __future__ import annotations

from ..models import Asset, AssetKind
from ..utils.http import request_bytes
from .qt_compat import (
    QLabel,
    QAudioOutput,
    QFrame,
    QHBoxLayout,
    QMediaPlayer,
    QPixmap,
    QProgressBar,
    QPushButton,
    QSlider,
    QThread,
    Qt,
    QUrl,
    QVBoxLayout,
    QVideoWidget,
    QWidget,
    Signal,
)


class ImageLoader(QThread):
    # The generation token lets the panel ignore results from a load that has
    # since been superseded by a newer selection.
    loaded = Signal(int, bytes)
    failed = Signal(int, str)

    def __init__(self, generation: int, url: str):
        super().__init__()
        self.generation = generation
        self.url = url

    def run(self) -> None:
        try:
            self.loaded.emit(self.generation, request_bytes(self.url, timeout=15.0).body)
        except Exception as exc:
            self.failed.emit(self.generation, str(exc))


class PreviewPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.current_asset: Asset | None = None
        # Keep references to in-flight loaders so a still-running QThread is never
        # garbage-collected mid-download (that aborts the whole app).
        self._image_loaders: list[ImageLoader] = []
        self._image_generation = 0
        self._seeking = False
        self._has_multimedia = bool(QMediaPlayer and QVideoWidget)

        self.player = QMediaPlayer() if QMediaPlayer else None
        self.audio_output = QAudioOutput() if QAudioOutput else None
        if self.player and self.audio_output and hasattr(self.player, "setAudioOutput"):
            self.player.setAudioOutput(self.audio_output)

        self._build_ui()
        self._connect_player()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        self.preview_frame = QFrame()
        self.preview_frame.setObjectName("PreviewFrame")
        preview_layout = QVBoxLayout(self.preview_frame)
        preview_layout.setContentsMargins(0, 0, 0, 0)

        self.video_widget = QVideoWidget() if QVideoWidget else None
        self.image_label = QLabel("Select an asset to preview")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setWordWrap(True)
        self.image_label.setMinimumHeight(230)
        if self.video_widget:
            self.video_widget.setMinimumHeight(230)
            preview_layout.addWidget(self.video_widget)
            self.video_widget.hide()
            if self.player:
                self.player.setVideoOutput(self.video_widget)
        preview_layout.addWidget(self.image_label)
        root.addWidget(self.preview_frame)

        self.loading_bar = QProgressBar()
        self.loading_bar.setObjectName("LoadingBar")
        self.loading_bar.setRange(0, 0)  # indeterminate "busy" animation
        self.loading_bar.setTextVisible(False)
        self.loading_bar.setMaximumHeight(4)
        self.loading_bar.hide()
        root.addWidget(self.loading_bar)

        controls = QHBoxLayout()
        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.toggle_playback)
        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setRange(0, 0)
        self.position_slider.sliderPressed.connect(self._begin_seek)
        self.position_slider.sliderReleased.connect(self._finish_seek)
        self.position_slider.sliderMoved.connect(self._preview_seek)
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setMinimumWidth(96)
        controls.addWidget(self.play_button)
        controls.addWidget(self.position_slider, 1)
        controls.addWidget(self.time_label)
        root.addLayout(controls)
        self._set_controls_enabled(False)

    def _connect_player(self) -> None:
        if not self.player:
            return
        self.player.positionChanged.connect(self._position_changed)
        self.player.durationChanged.connect(self._duration_changed)
        self.player.playbackStateChanged.connect(self._state_changed)
        if hasattr(self.player, "errorOccurred"):
            self.player.errorOccurred.connect(self._player_error)

    def load_asset(self, asset: Asset | None) -> None:
        self.stop()
        # Invalidate any image load still in flight from a previous selection.
        self._image_generation += 1
        self.current_asset = asset
        self.position_slider.setValue(0)
        self.position_slider.setRange(0, 0)
        self.time_label.setText("00:00 / 00:00")
        self._set_loading(False)
        if not asset:
            self._show_message("Select an asset to preview")
            self._set_controls_enabled(False)
            return

        preview_url = asset.preview_url or asset.thumbnail_url or asset.source_url
        if not preview_url:
            self._show_message("No preview available")
            self._set_controls_enabled(False)
            return

        if asset.kind == AssetKind.IMAGE:
            self._load_image(preview_url)
            return

        if not self._has_multimedia or not self.player:
            self._show_message("Qt multimedia is not available in this Python environment")
            self._set_controls_enabled(False)
            return

        self._show_video_surface(asset.kind == AssetKind.VIDEO)
        if hasattr(self.player, "setSource"):
            self.player.setSource(QUrl(preview_url))
        else:
            self.player.setMedia(QUrl(preview_url))
        self._set_controls_enabled(True)
        if asset.kind in {AssetKind.MUSIC, AssetKind.SFX}:
            self._show_message(f"♪  {asset.display_title}")
        # Single-click auto-plays the clip; the busy bar covers buffering.
        self._set_loading(True)
        self.play_button.setText("Pause")
        self.player.play()

    def toggle_playback(self) -> None:
        if not self.player:
            return
        if self._is_playing():
            self.player.pause()
        else:
            self.player.play()

    def stop(self) -> None:
        if self.player:
            self.player.stop()

    def _load_image(self, url: str) -> None:
        self._set_controls_enabled(False)
        self._show_message("Loading image preview...")
        self._set_loading(True)
        loader = ImageLoader(self._image_generation, url)
        loader.loaded.connect(self._image_loaded)
        loader.failed.connect(self._image_failed)
        loader.finished.connect(lambda: self._retire_loader(loader))
        self._image_loaders.append(loader)
        loader.start()

    def _retire_loader(self, loader: ImageLoader) -> None:
        if loader in self._image_loaders:
            self._image_loaders.remove(loader)
        loader.deleteLater()

    def _image_loaded(self, generation: int, data: bytes) -> None:
        if generation != self._image_generation:
            return
        self._set_loading(False)
        pixmap = QPixmap()
        pixmap.loadFromData(data)
        if pixmap.isNull():
            self._show_message("Image preview failed")
            return
        scaled = pixmap.scaled(
            self.image_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self._show_image()
        self.image_label.setPixmap(scaled)

    def _image_failed(self, generation: int, error: str) -> None:
        if generation != self._image_generation:
            return
        self._set_loading(False)
        self._show_message(f"Image preview failed\n{error}")

    def _set_loading(self, loading: bool) -> None:
        self.loading_bar.setVisible(loading)

    def shutdown(self) -> None:
        """Stop playback and wait for image loader threads before teardown."""
        self.stop()
        self._image_generation += 1
        for loader in list(self._image_loaders):
            loader.wait()

    def _show_video_surface(self, show_video: bool) -> None:
        if self.video_widget:
            self.video_widget.setVisible(show_video)
        self.image_label.setVisible(not show_video)
        if not show_video:
            self.image_label.setPixmap(QPixmap())

    def _show_image(self) -> None:
        if self.video_widget:
            self.video_widget.hide()
        self.image_label.show()

    def _show_message(self, text: str) -> None:
        self._show_image()
        self.image_label.setPixmap(QPixmap())
        self.image_label.setText(text)

    def _set_controls_enabled(self, enabled: bool) -> None:
        self.play_button.setEnabled(enabled)
        self.position_slider.setEnabled(enabled)

    def _begin_seek(self) -> None:
        self._seeking = True

    def _preview_seek(self, position: int) -> None:
        self._update_time_label(position, self.position_slider.maximum())

    def _finish_seek(self) -> None:
        if self.player:
            self.player.setPosition(self.position_slider.value())
        self._seeking = False

    def _position_changed(self, position: int) -> None:
        if position > 0:
            self._set_loading(False)
        if not self._seeking:
            self.position_slider.setValue(position)
        self._update_time_label(position, self.position_slider.maximum())

    def _duration_changed(self, duration: int) -> None:
        self.position_slider.setRange(0, max(0, duration))
        self._update_time_label(self.position_slider.value(), duration)

    def _state_changed(self, state: object) -> None:
        playing = self._is_playing(state)
        self.play_button.setText("Pause" if playing else "Play")
        if playing:
            self._set_loading(False)

    def _player_error(self, *_args: object) -> None:
        self._set_loading(False)
        if not self.player:
            return
        error_text = ""
        if hasattr(self.player, "errorString"):
            error_text = self.player.errorString()
        if error_text:
            self._show_message(f"Preview failed\n{error_text}")

    def _is_playing(self, state: object | None = None) -> bool:
        if not self.player:
            return False
        current_state = state if state is not None else self.player.playbackState()
        return current_state == QMediaPlayer.PlayingState

    def _update_time_label(self, position: int, duration: int) -> None:
        self.time_label.setText(f"{_format_ms(position)} / {_format_ms(duration)}")


def _format_ms(value: int) -> str:
    seconds = max(0, int(value / 1000))
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"
