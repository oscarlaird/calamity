COLORS = ["red", "green", "yellow", "magenta", "cyan", "white"]
CYCLE_DICT = {color: COLORS[(i + 1) % len(COLORS)] for i, color in enumerate(COLORS)}
CYCLE_DICT_BACKWARDS = {color: COLORS[(i - 1) % len(COLORS)] for i, color in enumerate(COLORS)}

ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
ANSI_REVERSE = "\033[7m"
CURSOR_OFF = "\033[?25l"
CURSOR_ON = "\033[?25h"
CLEAR_LINE = "\033[K"
CLEAR_TO_END = "\033[0K"
ANSI_COLOR_DICT = {
    "red": "\033[91m",
    "green": "\033[32m",
    "blue": "\033[34m",
    "yellow": "\033[33m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    "black": "\033[30m",
}
BACKGROUND_COLOR_DICT = {
    "green": "\033[42m",
    "blue": "\033[44m",
    "yellow": "\033[43m",
    "magenta": "\033[45m",
    "cyan": "\033[46m",
    "white": "\033[47m",
    "red": "\033[101m",
    "black": "\033[40m",
}
WRAP_OFF = "\033[?7l"
WRAP_ON = "\033[?7h"

CLEAR_SCREEN = "\033[2J"

RESET = "\033[0m"
RESET_COLOR = "\033[39m"
RESET_BACKGROUND = "\033[49m"
RESET_STYLE = "\033[22m"
REVERSE_OFF = "\033[27m"
FLASH_OFF = "\033[25m"
FLASH_ON = "\033[5m"
BOLD_OFF = "\033[22m"
BOLD_ON = "\033[1m"
UP_LINE = "\033[F"
DOWN_LINE = "\033[E"
ALT_SCREEN = "\033[?1049h"
MAIN_SCREEN = "\033[?1049l"
