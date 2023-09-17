"""
Get a single character from stdin, without waiting for a newline.
If the terminal is resized, getch() will return None.
"""
import sys
import tty
import termios
import os


import signal
import select

read_fd, write_fd = os.pipe()

def handle_winch(signum, frame):
    os.write(write_fd, b'x')

signal.signal(signal.SIGWINCH, handle_winch)

def getch():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        r, _, _ = select.select([sys.stdin, read_fd], [], [])
        if sys.stdin in r:
            ch = sys.stdin.read(1)
        elif read_fd in r:
            os.read(read_fd, 1)
            ch = 'RESIZE'
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch
