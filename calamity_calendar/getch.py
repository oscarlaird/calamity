"""
Get a single character from stdin, without waiting for a newline.
If the terminal is resized, getch() will return None.
"""
import sys
import tty
import termios


# import signal
# import select

def getch():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch
