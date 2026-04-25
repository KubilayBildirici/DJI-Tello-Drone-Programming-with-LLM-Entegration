"""
Central configuration for the Drone Control System.
All magic numbers and tunable constants live here.
"""


class Config:
    # ── Drone / RC ─────────────────────────────────────────────────────────────
    DRONE_SPEED: int = 70          # max RC speed sent to Tello (0-100)
    RC_LOOP_INTERVAL: float = 0.05 # seconds between RC packets (~20 Hz)
    DRONE_CONNECT_TIMEOUT: int = 10

    # ── Gamepad ─────────────────────────────────────────────────────────────────
    GAMEPAD_DEADZONE: float = 0.1
    GAMEPAD_TRIGGER_THRESHOLD: float = 0.3
    GAMEPAD_UD_MIN: int = 10       # ignore ud values below this

    # ── AI / LLM ────────────────────────────────────────────────────────────────
    LLM_INTERVAL: int = 5          # seconds between analysis calls
    LLM_RESIZE: int = 320          # resize frame to NxN before sending
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_MAX_TOKENS: int = 50
    OPENAI_TIMEOUT: float = 30.0   # seconds

    # ── Telemetry thresholds ────────────────────────────────────────────────────
    BATTERY_WARNING: int = 20      # %
    TEMP_WARNING: int = 80         # °C

    # ── Video ───────────────────────────────────────────────────────────────────
    VIDEO_WIDTH: int = 640
    VIDEO_HEIGHT: int = 480
    TARGET_IMG_W: int = 220
    TARGET_IMG_H: int = 165
    FPS_SAMPLE_SIZE: int = 30      # rolling average over N frames

    # ── Paths ───────────────────────────────────────────────────────────────────
    RECORDINGS_DIR: str = "recordings"
    SCREENSHOTS_DIR: str = "screenshots"
    LOG_FILE: str = "drone.log"

    # ── UI ──────────────────────────────────────────────────────────────────────
    WINDOW_TITLE: str = "Drone Control System — DJI Tello"
    WINDOW_W: int = 1280
    WINDOW_H: int = 760
    TIMER_MS: int = 30             # UI refresh interval (ms)
    GAMEPAD_POLL_MS: float = 0.1   # seconds between gamepad polls
