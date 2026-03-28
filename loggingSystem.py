import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)

class Logger:
    RED = '\033[31m'
    GREEN = '\033[32m'
    BLUE = '\033[34m'
    WHITE = '\033[37m'

    BG_BLACK = '\033[40m'
    RESET = '\033[0m'

    def __init__(self, name="SYSTEM", color=WHITE):
        self.name = name
        self.color = color

    def log(self, message):
        color_code = self.BG_BLACK + self.color
        msg = f"[{self.name}] {message}"
        print(color_code + msg + self.RESET)