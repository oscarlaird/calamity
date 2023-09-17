import curses

up_keys = [curses.KEY_UP, ord('k'), ord('-')]
down_keys = [curses.KEY_DOWN, ord('j'), ord('+')]
# next page, f, space
page_forward_keys = [curses.KEY_NPAGE, ord('f'), ord(' ')]
# previous page, b, backspace
page_backward_keys = [curses.KEY_PPAGE, ord('b'), curses.KEY_BACKSPACE]

def pager(text, center=False):
    # Initialize curses
    stdscr = curses.initscr()
    curses.noecho()  # Don't echo keypresses to stdout
    curses.cbreak()  # Don't require enter to be pressed; cbreak stands for "character break"
    stdscr.keypad(1)

    # Split the text into lines
    lines = text.split('\n')

    # Initial position
    pos = 0

    while True:
        # Clear screen
        stdscr.clear()

        # Calculate the range of lines to show
        height, width = stdscr.getmaxyx()
        height -= 1  # Leave room for the status bar
        end_pos = max(0, len(lines) - height)
        visible_lines = lines[pos:pos+height]

        # Print the visible lines
        for i, line in enumerate(visible_lines):
            # Ensure line doesn't exceed the width of the terminal
            truncated_line = line if len(line) <= width else (line[:width-1] + line[-1])
            truncated_line = truncated_line.center(width) if center else truncated_line
            stdscr.addstr(i, 0, truncated_line)

        # Print the status bar (In dim text (use an ansi code), "press q to quit")
        status_bar = "Press q to quit."
        stdscr.addstr(height, 0, status_bar, curses.A_DIM)



        # Refresh the screen
        stdscr.refresh()

        # Wait for user input
        key = stdscr.getch()

        # Define key behaviors
        if key in down_keys:
            if pos < len(lines) - height:
                pos += 1
        elif key in up_keys:
            if pos > 0:
                pos -= 1
        elif key in page_forward_keys:
            pos += height
            pos = min(pos, end_pos)
        elif key in page_backward_keys:
            pos -= height
            pos = max(pos, 0)
        elif key == ord('g'):
            pos = 0
        elif key == ord('G'):
            pos = end_pos
        elif key == 410:
            pass  # window resized
        else:  # exit
            break

    # Cleanup and close curses
    curses.nocbreak()
    stdscr.keypad(0)
    curses.echo()
    curses.endwin()
