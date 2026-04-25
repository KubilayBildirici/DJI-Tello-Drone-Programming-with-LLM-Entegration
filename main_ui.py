"""
Drone Control System — Ana UI
DJI Tello + OpenAI GPT-4o-mini ile hedef tespit sistemi.
"""

from __future__ import annotations

import sys
import cv2
import time
from datetime import datetime
from collections import deque
from pathlib import Path

from PySide6.QtCore import QTimer, QObject, QThread, Signal, Qt, QSize
from PySide6.QtGui import QImage, QPixmap, QMovie
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QFrame, QVBoxLayout, QHBoxLayout, QFileDialog,
    QProgressBar, QSlider, QTextEdit, QSizePolicy,
)

from drone_control_system import DroneControlSystem
from Gamepad_Control_System import GamepadController
from llm import analyze_frame, encode_frame
from loggingSystem import Logger
from config import Config

_BASE_DIR = Path(__file__).parent

# ── STYLE SHEET ───────────────────────────────────────────────────────────────
STYLESHEET = """
QWidget {
    background-color: #0a0a0f;
    color: #d0d0e0;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
}
QFrame#panel {
    background-color: #12121c;
    border-radius: 12px;
    border: 1px solid #2a2a3a;
}
QFrame#header_bar {
    background-color: #0d0d18;
    border-radius: 0px;
    border-bottom: 1px solid #1e1e30;
}
QFrame#video_frame {
    background-color: #000000;
    border-radius: 12px;
    border: 2px solid #1e1e30;
}
QLabel {
    background-color: transparent;
    border: none;
}
QLabel#section_title {
    color: #00e5aa;
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 1.5px;
    background-color: transparent;
    border: none;
}
QLabel#stat_label {
    background-color: #1a1a2a;
    border: 1px solid #2a2a3a;
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 12px;
}
QLabel#status_badge_ok {
    background-color: #0f2e1f;
    color: #00e57a;
    border: 1px solid #00e57a;
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: bold;
}
QLabel#status_badge_warn {
    background-color: #2e1f0f;
    color: #ffaa00;
    border: 1px solid #ffaa00;
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: bold;
}
QLabel#status_badge_err {
    background-color: #2e0f0f;
    color: #ff4444;
    border: 1px solid #ff4444;
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: bold;
}
QLabel#target_result_found {
    background-color: #0a2e1a;
    color: #00e57a;
    border: 1px solid #00e57a;
    border-radius: 8px;
    padding: 8px;
    font-weight: bold;
    font-size: 13px;
}
QLabel#target_result_notfound {
    background-color: #2e0a0a;
    color: #ff4444;
    border: 1px solid #ff4444;
    border-radius: 8px;
    padding: 8px;
    font-weight: bold;
    font-size: 13px;
}
QLabel#target_result_idle {
    background-color: #1a1a2a;
    color: #606080;
    border: 1px solid #2a2a3a;
    border-radius: 8px;
    padding: 8px;
    font-size: 13px;
}
QPushButton {
    background-color: #1a1a2a;
    border-radius: 8px;
    padding: 9px 14px;
    font-weight: bold;
    font-size: 12px;
    border: 1px solid #2a2a3a;
    color: #d0d0e0;
}
QPushButton:hover {
    background-color: #22223a;
    border: 1px solid #00e5aa;
    color: #00e5aa;
}
QPushButton:pressed { background-color: #0d0d18; }
QPushButton:disabled {
    background-color: #111118;
    color: #444458;
    border: 1px solid #1a1a2a;
}
QPushButton#btn_danger { border-color: #ff4444; color: #ff4444; }
QPushButton#btn_danger:hover { background-color: #2e0a0a; border-color: #ff6666; color: #ff6666; }
QPushButton#btn_success { border-color: #00e57a; color: #00e57a; }
QPushButton#btn_success:hover { background-color: #0a2e1a; border-color: #00ff99; color: #00ff99; }
QPushButton#btn_record_active { border-color: #ff4444; color: #ff4444; background-color: #2e0a0a; }
QPushButton#btn_ai_on  { border-color: #00e5aa; color: #00e5aa; }
QPushButton#btn_ai_off { border-color: #555570; color: #555570; }
QProgressBar {
    background-color: #1a1a2a;
    border: 1px solid #2a2a3a;
    border-radius: 6px;
    height: 10px;
    text-align: center;
    font-size: 10px;
}
QSlider::groove:horizontal {
    border: 1px solid #2a2a3a;
    height: 6px;
    background: #1a1a2a;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #00e5aa;
    border: 1px solid #00e5aa;
    width: 14px;
    height: 14px;
    border-radius: 7px;
    margin: -4px 0;
}
QSlider::sub-page:horizontal { background: #00c896; border-radius: 3px; }
QTextEdit#log_panel {
    background-color: #0a0a14;
    border: 1px solid #1e1e30;
    border-radius: 8px;
    color: #8888aa;
    font-family: 'Consolas', monospace;
    font-size: 11px;
    padding: 4px;
}
"""


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _section(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setObjectName("section_title")
    return lbl

def _stat_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("stat_label")
    return lbl

def _divider() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet(
        "border: none; border-top: 1px solid #1e1e30; background: transparent;"
    )
    return line


# ─────────────────────────────────────────────────────────────────────────────
# Worker Threads
# ─────────────────────────────────────────────────────────────────────────────

class ConnectWorker(QObject):
    finished = Signal(object, object)  # drone, gamepad
    error = Signal(str)

    def run(self) -> None:
        try:
            drone   = DroneControlSystem()
            gamepad = GamepadController(drone)
            self.finished.emit(drone, gamepad)
        except Exception as e:
            self.error.emit(str(e))


class LLMWorker(QObject):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, target_b64: str, frame_b64: str) -> None:
        super().__init__()
        self.target_b64 = target_b64
        self.frame_b64 = frame_b64

    def run(self) -> None:
        try:
            result = analyze_frame(self.target_b64, self.frame_b64)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class DroneUI(QWidget):

    def __init__(self) -> None:
        super().__init__()
        self.logger = Logger("UI", Logger.GREEN)

        # ── State ────────────────────────────────────────────────────────────
        self.drone: DroneControlSystem | None = None
        self.gamepad: GamepadController | None = None

        self.target_b64: str | None = None
        self.target_image = None

        self.last_gamepad_update: float = 0.0
        self.last_capture: float = 0.0
        self.last_result: str = ""

        self.connect_busy: bool = False
        self.llm_enabled: bool = True

        self.connect_thread: QThread | None = None
        self.connect_worker: ConnectWorker | None = None
        self.llm_thread: QThread | None = None
        self.llm_worker: LLMWorker | None = None

        self.detection_found: int = 0
        self.detection_total: int = 0

        self._frame_times: deque = deque(maxlen=Config.FPS_SAMPLE_SIZE)

        self._video_writer: cv2.VideoWriter | None = None
        self._recording: bool = False
        self._record_start: float = 0.0

        Path(Config.RECORDINGS_DIR).mkdir(exist_ok=True)
        Path(Config.SCREENSHOTS_DIR).mkdir(exist_ok=True)

        self.setStyleSheet(STYLESHEET)
        self.setWindowTitle(Config.WINDOW_TITLE)
        self.setMinimumSize(Config.WINDOW_W, Config.WINDOW_H)

        self._build_ui()

        self.timer = QTimer()
        self.timer.timeout.connect(self._update_all)
        self.timer.start(Config.TIMER_MS)

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self._build_header())

        body = QHBoxLayout()
        body.setSpacing(10)
        body.setContentsMargins(12, 10, 12, 10)
        body.addWidget(self._build_left_panel(), 0)
        body.addWidget(self._build_center_panel(), 1)
        body.addWidget(self._build_right_panel(), 0)
        root.addLayout(body)

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("header_bar")
        frame.setFixedHeight(52)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(18, 0, 18, 0)

        icon_lbl = QLabel("🚁")
        icon_lbl.setStyleSheet("font-size: 22px; background: transparent; border: none;")

        title_lbl = QLabel("Drone Control System")
        title_lbl.setStyleSheet(
            "font-size: 17px; font-weight: bold; color: #00e5aa;"
            "background: transparent; border: none;"
        )

        sub_lbl = QLabel("DJI Tello  ·  GPT-4o-mini")
        sub_lbl.setStyleSheet(
            "font-size: 11px; color: #555570; background: transparent; border: none;"
        )

        layout.addWidget(icon_lbl)
        layout.addSpacing(8)
        layout.addWidget(title_lbl)
        layout.addSpacing(10)
        layout.addWidget(sub_lbl)
        layout.addStretch()

        self.conn_badge = QLabel("○  Disconnected")
        self.conn_badge.setObjectName("status_badge_err")

        self.fps_label = QLabel("FPS: —")
        self.fps_label.setStyleSheet(
            "font-size: 11px; color: #555570; background: transparent; border: none;"
        )

        layout.addWidget(self.fps_label)
        layout.addSpacing(12)
        layout.addWidget(self.conn_badge)
        return frame

    # ── Left panel ────────────────────────────────────────────────────────────

    def _build_left_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("panel")
        frame.setFixedWidth(220)
        layout = QVBoxLayout(frame)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        layout.addWidget(_section("Telemetry"))

        self.battery_lbl = QLabel("🔋  —")
        self.battery_lbl.setObjectName("stat_label")
        layout.addWidget(self.battery_lbl)

        self.battery_bar = QProgressBar()
        self.battery_bar.setRange(0, 100)
        self.battery_bar.setValue(0)
        self.battery_bar.setTextVisible(False)
        self.battery_bar.setFixedHeight(8)
        layout.addWidget(self.battery_bar)

        self.height_lbl = _stat_label("📏  Height: —")
        self.speed_lbl  = _stat_label("🚀  Speed: —")
        self.temp_lbl   = _stat_label("🌡  Temp: —")
        for w in (self.height_lbl, self.speed_lbl, self.temp_lbl):
            layout.addWidget(w)

        layout.addWidget(_divider())

        self.warning_lbl = QLabel("○  Not Connected")
        self.warning_lbl.setObjectName("status_badge_err")
        self.warning_lbl.setWordWrap(True)
        layout.addWidget(self.warning_lbl)

        layout.addWidget(_divider())
        layout.addWidget(_section("Controls"))

        self.btn_connect = QPushButton("⚡  Connect")
        self.btn_takeoff = QPushButton("🚀  Takeoff")
        self.btn_land    = QPushButton("🛬  Land")
        self.btn_takeoff.setObjectName("btn_success")
        self.btn_land.setObjectName("btn_danger")
        self.btn_takeoff.setEnabled(False)
        self.btn_land.setEnabled(False)

        for btn in (self.btn_connect, self.btn_takeoff, self.btn_land):
            btn.setFixedHeight(36)
            layout.addWidget(btn)

        layout.addWidget(_divider())
        layout.addWidget(_section("Capture"))

        self.btn_screenshot = QPushButton("📸  Screenshot")
        self.btn_record     = QPushButton("⏺  Record")
        self.btn_screenshot.setFixedHeight(36)
        self.btn_record.setFixedHeight(36)
        layout.addWidget(self.btn_screenshot)
        layout.addWidget(self.btn_record)
        layout.addStretch()

        self.btn_connect.clicked.connect(self._connect_drone)
        self.btn_takeoff.clicked.connect(self._takeoff)
        self.btn_land.clicked.connect(self._land)
        self.btn_screenshot.clicked.connect(self._take_screenshot)
        self.btn_record.clicked.connect(self._toggle_recording)
        return frame

    # ── Center panel ──────────────────────────────────────────────────────────

    def _build_center_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("video_frame")
        layout = QVBoxLayout(frame)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(Config.VIDEO_WIDTH, Config.VIDEO_HEIGHT)
        self.video_label.setScaledContents(True)
        self.video_label.setStyleSheet("background-color: black; border: none;")

        gif_path = str(_BASE_DIR / "assets" / "2.gif")
        if Path(gif_path).exists():
            self._movie = QMovie(gif_path)
            self._movie.setScaledSize(QSize(Config.VIDEO_WIDTH, Config.VIDEO_HEIGHT))
            self.video_label.setMovie(self._movie)
            self._movie.start()
        else:
            self.video_label.setText("No video signal")
            self.video_label.setStyleSheet(
                "background-color: #0a0a14; color: #444; font-size: 18px;"
            )

        layout.addWidget(self.video_label)
        return frame

    # ── Right panel ───────────────────────────────────────────────────────────

    def _build_right_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("panel")
        frame.setFixedWidth(240)
        layout = QVBoxLayout(frame)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        layout.addWidget(_section("Target Object"))

        self.image_label = QLabel("No target selected")
        self.image_label.setFixedSize(Config.TARGET_IMG_W, Config.TARGET_IMG_H)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet(
            "border: 2px dashed #2a2a3a; border-radius: 8px;"
            "color: #555570; font-size: 12px; background: #0d0d18;"
        )
        layout.addWidget(self.image_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.btn_select_target = QPushButton("🎯  Select Target")
        self.btn_select_target.setFixedHeight(34)
        layout.addWidget(self.btn_select_target)

        layout.addWidget(_divider())
        layout.addWidget(_section("AI Analysis"))

        self.target_result_lbl = QLabel("—  Waiting for target")
        self.target_result_lbl.setObjectName("target_result_idle")
        self.target_result_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.target_result_lbl.setWordWrap(True)
        layout.addWidget(self.target_result_lbl)

        self.detection_lbl = QLabel("Detections: 0 / 0")
        self.detection_lbl.setObjectName("stat_label")
        self.detection_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.detection_lbl)

        self.btn_ai_toggle = QPushButton("🔍  AI: ON")
        self.btn_ai_toggle.setObjectName("btn_ai_on")
        self.btn_ai_toggle.setFixedHeight(34)
        layout.addWidget(self.btn_ai_toggle)

        interval_row = QHBoxLayout()
        interval_row.addWidget(
            QLabel("Interval:")
        )
        interval_row.itemAt(0).widget().setStyleSheet(
            "color: #888; font-size: 11px; background: transparent; border: none;"
        )
        interval_row.addStretch()
        self.interval_val_lbl = QLabel(f"{Config.LLM_INTERVAL}s")
        self.interval_val_lbl.setStyleSheet(
            "color: #00e5aa; font-size: 11px; background: transparent; border: none;"
        )
        interval_row.addWidget(self.interval_val_lbl)
        layout.addLayout(interval_row)

        self.interval_slider = QSlider(Qt.Orientation.Horizontal)
        self.interval_slider.setRange(1, 30)
        self.interval_slider.setValue(Config.LLM_INTERVAL)
        layout.addWidget(self.interval_slider)

        layout.addWidget(_divider())
        layout.addWidget(_section("Event Log"))

        self.log_panel = QTextEdit()
        self.log_panel.setObjectName("log_panel")
        self.log_panel.setReadOnly(True)
        self.log_panel.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self.log_panel)

        self.btn_clear_log = QPushButton("Clear Log")
        self.btn_clear_log.setFixedHeight(28)
        self.btn_clear_log.setStyleSheet("font-size: 11px;")
        layout.addWidget(self.btn_clear_log)

        self.btn_select_target.clicked.connect(self._load_target)
        self.btn_ai_toggle.clicked.connect(self._toggle_ai)
        self.interval_slider.valueChanged.connect(self._on_interval_changed)
        self.btn_clear_log.clicked.connect(self.log_panel.clear)
        return frame

    # ── Logging ───────────────────────────────────────────────────────────────

    def _log(self, message: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_panel.append(
            f"<span style='color:#445566'>[{ts}]</span> {message}"
        )
        self.log_panel.verticalScrollBar().setValue(
            self.log_panel.verticalScrollBar().maximum()
        )
        self.logger.log(message)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _load_target(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Target Image", "",
            "Images (*.jpg *.jpeg *.png *.bmp)"
        )
        if not file_path:
            return

        pixmap = QPixmap(file_path)
        if pixmap.isNull():
            self._log("❌ Image could not be loaded.")
            return

        scaled = pixmap.scaled(
            Config.TARGET_IMG_W, Config.TARGET_IMG_H,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled)
        self.image_label.setStyleSheet(
            "border: 2px solid #00e5aa; border-radius: 8px;"
        )
        self.target_image = cv2.imread(file_path)
        self.target_b64   = encode_frame(self.target_image)
        self._log(f"🎯 Target set: {Path(file_path).name}")

    def _takeoff(self) -> None:
        if self.drone is None:
            return
        self.drone.takeoff()
        self._log("🚀 Takeoff command sent.")

    def _land(self) -> None:
        if self.drone is None:
            return
        self.drone.land()
        self._log("🛬 Land command sent.")

    def _toggle_ai(self) -> None:
        self.llm_enabled = not self.llm_enabled
        if self.llm_enabled:
            self.btn_ai_toggle.setText("🔍  AI: ON")
            self.btn_ai_toggle.setObjectName("btn_ai_on")
            self._log("🔍 AI analysis enabled.")
        else:
            self.btn_ai_toggle.setText("🔍  AI: OFF")
            self.btn_ai_toggle.setObjectName("btn_ai_off")
            self._log("⏸ AI analysis disabled.")
        self.btn_ai_toggle.setStyleSheet("")

    def _on_interval_changed(self, value: int) -> None:
        self.interval_val_lbl.setText(f"{value}s")

    def _take_screenshot(self) -> None:
        pixmap = self.video_label.pixmap()
        if pixmap is None or pixmap.isNull():
            self._log("❌ No frame available for screenshot.")
            return
        ts   = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        path = str(Path(Config.SCREENSHOTS_DIR) / f"{ts}.jpg")
        pixmap.save(path, "JPEG", 95)
        self._log(f"📸 Screenshot saved: {path}")

    def _toggle_recording(self) -> None:
        if not self._recording:
            self._start_recording()
        else:
            self._stop_recording()

    def _start_recording(self) -> None:
        ts     = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        path   = str(Path(Config.RECORDINGS_DIR) / f"{ts}.avi")
        fourcc = cv2.VideoWriter.fourcc(*"XVID")
        self._video_writer = cv2.VideoWriter(
            path, fourcc, 30,
            (Config.VIDEO_WIDTH, Config.VIDEO_HEIGHT)
        )
        self._recording    = True
        self._record_start = time.time()
        self.btn_record.setText("⏹  Stop Rec")
        self.btn_record.setObjectName("btn_record_active")
        self.btn_record.setStyleSheet("")
        self._log(f"⏺ Recording started: {path}")

    def _stop_recording(self) -> None:
        if self._video_writer:
            self._video_writer.release()
            self._video_writer = None
        self._recording = False
        self.btn_record.setText("⏺  Record")
        self.btn_record.setObjectName("")
        self.btn_record.setStyleSheet("")
        self._log("⏹ Recording stopped.")

    # ── Connection ────────────────────────────────────────────────────────────

    def _connect_drone(self) -> None:
        if self.connect_busy:
            return
        self.connect_busy = True
        self.warning_lbl.setText("⏳  Connecting…")
        self.warning_lbl.setObjectName("status_badge_warn")
        self.warning_lbl.setStyleSheet("")
        self.btn_connect.setEnabled(False)
        self._log("⚡ Connecting to drone…")

        self.connect_thread = QThread()
        self.connect_worker = ConnectWorker()
        self.connect_worker.moveToThread(self.connect_thread)

        self.connect_thread.started.connect(self.connect_worker.run)
        self.connect_worker.finished.connect(self._on_connect_success)
        self.connect_worker.error.connect(self._on_connect_error)
        self.connect_worker.finished.connect(self.connect_thread.quit)
        self.connect_worker.error.connect(self.connect_thread.quit)
        self.connect_thread.finished.connect(self._cleanup_connect_thread)
        self.connect_thread.finished.connect(self.connect_worker.deleteLater)
        self.connect_thread.finished.connect(self.connect_thread.deleteLater)

        self.connect_thread.start()

    def _on_connect_success(self, drone: DroneControlSystem, gamepad: GamepadController) -> None:
        self.drone   = drone
        self.gamepad = gamepad
        self.connect_busy = False

        self.warning_lbl.setText("✓  Connected")
        self.warning_lbl.setObjectName("status_badge_ok")
        self.warning_lbl.setStyleSheet("")

        self.conn_badge.setText("●  Connected")
        self.conn_badge.setObjectName("status_badge_ok")
        self.conn_badge.setStyleSheet("")

        self.btn_connect.setEnabled(True)
        self.btn_takeoff.setEnabled(True)
        self.btn_land.setEnabled(True)

        if hasattr(self, "_movie"):
            self._movie.stop()

        self._log("✅ Drone connected successfully.")

    def _on_connect_error(self, message: str) -> None:
        self.connect_busy = False
        self.warning_lbl.setText("✗  Connection Failed")
        self.warning_lbl.setObjectName("status_badge_err")
        self.warning_lbl.setStyleSheet("")
        self.btn_connect.setEnabled(True)
        self._log(f"❌ Connection error: {message}")

    def _cleanup_connect_thread(self) -> None:
        self.connect_thread = None
        self.connect_worker = None

    # ── LLM ──────────────────────────────────────────────────────────────────

    def _start_llm_worker(self, frame_b64: str) -> None:
        if self.target_b64 is None or not self.llm_enabled:
            return

        if self.llm_thread is not None:
            try:
                if self.llm_thread.isRunning():
                    return
            except RuntimeError:
                pass
            self.llm_thread = None
            self.llm_worker = None

        self.llm_thread = QThread()
        self.llm_worker = LLMWorker(self.target_b64, frame_b64)
        self.llm_worker.moveToThread(self.llm_thread)

        self.llm_thread.started.connect(self.llm_worker.run)
        self.llm_worker.finished.connect(self._on_llm_result)
        self.llm_worker.error.connect(self._on_llm_error)
        self.llm_worker.finished.connect(self.llm_thread.quit)
        self.llm_worker.error.connect(self.llm_thread.quit)
        self.llm_thread.finished.connect(self._cleanup_llm_thread)
        self.llm_thread.finished.connect(self.llm_worker.deleteLater)
        self.llm_thread.finished.connect(self.llm_thread.deleteLater)

        self.llm_thread.start()

    def _cleanup_llm_thread(self) -> None:
        self.llm_thread = None
        self.llm_worker = None

    def _on_llm_result(self, result: str) -> None:
        self.detection_total += 1
        if result == "HEDEF BULUNDU":
            self.detection_found += 1
            self.target_result_lbl.setText("✅  HEDEF BULUNDU")
            self.target_result_lbl.setObjectName("target_result_found")
        else:
            self.target_result_lbl.setText("❌  HEDEF BULUNAMADI")
            self.target_result_lbl.setObjectName("target_result_notfound")
        self.target_result_lbl.setStyleSheet("")

        self.detection_lbl.setText(
            f"Detections: {self.detection_found} / {self.detection_total}"
        )
        if result != self.last_result:
            self.last_result = result
            self._log(f"🔍 AI: {result}")

    def _on_llm_error(self, message: str) -> None:
        self._log(f"⚠️ AI error: {message}")

    # ── Main update loop ──────────────────────────────────────────────────────

    def _update_all(self) -> None:
        if self.drone is None:
            return

        now = time.time()

        # Gamepad
        if self.gamepad is not None and now - self.last_gamepad_update > Config.GAMEPAD_POLL_MS:
            try:
                self.gamepad.update()
                self.last_gamepad_update = now
            except Exception as e:
                self._log(f"⚠️ Gamepad error: {e}")

        # Video
        try:
            frame = self.drone.get_frame()
            if frame is not None:
                self._frame_times.append(now)
                if len(self._frame_times) >= 2:
                    elapsed = self._frame_times[-1] - self._frame_times[0]
                    fps = (len(self._frame_times) - 1) / elapsed if elapsed > 0 else 0
                    self.fps_label.setText(f"FPS: {fps:.0f}")

                display = frame.copy()

                if self._recording:
                    elapsed_rec = int(now - self._record_start)
                    mm, ss = divmod(elapsed_rec, 60)
                    cv2.circle(display, (18, 18), 7, (0, 0, 255), -1)
                    cv2.putText(
                        display, f"REC  {mm:02d}:{ss:02d}",
                        (32, 24), cv2.FONT_HERSHEY_SIMPLEX,
                        0.55, (255, 255, 255), 1, cv2.LINE_AA
                    )
                    if self._video_writer:
                        self._video_writer.write(
                            cv2.resize(frame, (Config.VIDEO_WIDTH, Config.VIDEO_HEIGHT))
                        )

                rgb = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb.shape
                qt_img = QImage(
                    rgb.data, w, h, ch * w, QImage.Format.Format_RGB888
                ).copy()
                self.video_label.setPixmap(QPixmap.fromImage(qt_img))

                interval = self.interval_slider.value()
                if now - self.last_capture > interval and self.llm_enabled:
                    small = cv2.resize(frame, (Config.LLM_RESIZE, Config.LLM_RESIZE))
                    self._start_llm_worker(encode_frame(small))
                    self.last_capture = now
        except Exception as e:
            self._log(f"⚠️ Video error: {e}")

        # Telemetry
        try:
            battery = self.drone.tello.get_battery()
            height  = self.drone.tello.get_height()
            speed   = self.drone.tello.get_speed_x()
            temp    = self.drone.tello.get_temperature()

            self.battery_lbl.setText(f"🔋  Battery: {battery}%")
            self.height_lbl.setText(f"📏  Height: {height} cm")
            self.speed_lbl.setText(f"🚀  Speed: {speed} cm/s")
            self.temp_lbl.setText(f"🌡  Temp: {temp}°C")

            self.battery_bar.setValue(battery)
            if battery <= Config.BATTERY_WARNING:
                self.battery_bar.setStyleSheet(
                    "QProgressBar::chunk { background-color: #ff4444; border-radius: 5px; }"
                )
            elif battery <= 50:
                self.battery_bar.setStyleSheet(
                    "QProgressBar::chunk { background-color: #ffaa00; border-radius: 5px; }"
                )
            else:
                self.battery_bar.setStyleSheet(
                    "QProgressBar::chunk { background-color: #00e57a; border-radius: 5px; }"
                )

            if battery <= Config.BATTERY_WARNING:
                self.warning_lbl.setText("⚠️  LOW BATTERY")
                self.warning_lbl.setObjectName("status_badge_err")
            elif temp >= Config.TEMP_WARNING:
                self.warning_lbl.setText("🔥  HIGH TEMP")
                self.warning_lbl.setObjectName("status_badge_warn")
            else:
                self.warning_lbl.setText("✓  Connected")
                self.warning_lbl.setObjectName("status_badge_ok")
            self.warning_lbl.setStyleSheet("")

        except Exception as e:
            self.warning_lbl.setText("⚠️  Telemetry error")
            self.warning_lbl.setObjectName("status_badge_warn")
            self.warning_lbl.setStyleSheet("")

    # ── Close event ───────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        self.timer.stop()

        if self._recording:
            self._stop_recording()

        if self.llm_thread is not None and self.llm_thread.isRunning():
            self.llm_thread.quit()
            self.llm_thread.wait(2000)

        if self.connect_thread is not None and self.connect_thread.isRunning():
            self.connect_thread.quit()
            self.connect_thread.wait(2000)

        if self.drone:
            try:
                self.drone.shutdown()
            except Exception as e:
                self.logger.error(f"Shutdown error: {e}")

        event.accept()


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = DroneUI()
    window.show()
    sys.exit(app.exec())
