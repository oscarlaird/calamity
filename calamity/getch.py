""""
Get a single character from stdin, without waiting for a newline.
If the terminal is resized, getch() will return None.
"""


import sys
import tty
import termios
import signal
import select

# Global flag to determine if terminal was resized
terminal_resized = False

def handle_resize(signum, frame):
    global terminal_resized
    terminal_resized = True

# Set up signal handler for SIGWINCH
signal.signal(signal.SIGWINCH, handle_resize)

def getch(watch_resize=False):
    global terminal_resized
    terminal_resized = False

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)

        while True:
            # Wait for input or check every 0.1 seconds
            rlist, _, _ = select.select([fd], [], [], 0.020)

            if rlist:  # If input is available, read it
                ch = sys.stdin.read(1)
                if ch == '\x1b':
                    ch += sys.stdin.read(1)
                    if ch[-1] == '[':  # arrow keys
                        ch += sys.stdin.read(1)
                return ch

            # Check the terminal resize flag
            if watch_resize and terminal_resized:
                return None

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

if __name__ == '__main__':  # test getch
    while True:
        c = getch()
        # check ctrl-c
        if c == '\x03':
            break
        print(repr(c))