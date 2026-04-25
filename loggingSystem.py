import logging
import sys
from logging.handlers import RotatingFileHandler
from config import Config

try:
    import colorama
    colorama.init(autoreset=True)
    _COLORAMA_AVAILABLE = True
except ImportError:
    _COLORAMA_AVAILABLE = False

# ── Root logger shared by all Logger instances ──────────────────────────────
_root_logger = logging.getLogger("drone")
_root_logger.setLevel(logging.DEBUG)

if not _root_logger.handlers:
    # Console handler
    _console_handler = logging.StreamHandler(sys.stdout)
    _console_handler.setFormatter(logging.Formatter("%(message)s"))
    _root_logger.addHandler(_console_handler)

    # File handler (rotating, max 1 MB, keep 3 backups)
    try:
        _file_handler = RotatingFileHandler(
            Config.LOG_FILE,
            maxBytes=1_048_576,
            backupCount=3,
            encoding="utf-8",
        )
        _file_handler.setFormatter(
            logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        )
        _root_logger.addHandler(_file_handler)
    except OSError:
        pass  # Read-only filesystem — skip file logging


class Logger:
    RED = "\033[31m"
    GREEN = "\033[32m"
    BLUE = "\033[34m"
    YELLOW = "\033[33m"
    WHITE = "\033[37m"
    RESET = "\033[0m"

    def __init__(self, name: str = "SYSTEM", color: str = WHITE) -> None:
        self.name = name
        self.color = color if _COLORAMA_AVAILABLE else ""

    def log(self, message: str) -> None:
        reset = self.RESET if _COLORAMA_AVAILABLE else ""
        formatted = f"{self.color}[{self.name}] {message}{reset}"
        _root_logger.info(formatted)

    def error(self, message: str) -> None:
        reset = self.RESET if _COLORAMA_AVAILABLE else ""
        formatted = f"{Logger.RED}[{self.name}] ERROR: {message}{reset}"
        _root_logger.error(formatted)

    def warning(self, message: str) -> None:
        reset = self.RESET if _COLORAMA_AVAILABLE else ""
        formatted = f"{Logger.YELLOW}[{self.name}] WARNING: {message}{reset}"
        _root_logger.warning(formatted)