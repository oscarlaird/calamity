import math
import datetime
# to get the width of the terminal, use shutil.get_terminal_size().columns
import shutil
import signal

from calamity_calendar import colors, database

TIMETABLE_START = 7 * 4  # start at 7am
TIMETABLE_END = 19 * 4  # end at 7pm
TIMETABLE_WIDTH = TIMETABLE_END - TIMETABLE_START
NUM_DAYS = 30
TABLE_WIDTH = 8 + 48 + 8 + 10 * 3 + 2

TERM_WIDTH = shutil.get_terminal_size().columns
MARGIN = ' ' * ((TERM_WIDTH - TABLE_WIDTH) // 2)


def refresh_term_size():
    global TERM_WIDTH, MARGIN
    TERM_WIDTH = shutil.get_terminal_size().columns
    MARGIN = ' ' * ((TERM_WIDTH - TABLE_WIDTH) // 2)


# Set up signal handler for SIGWINCH
signal.signal(signal.SIGWINCH, lambda signum, frame: refresh_term_size())

def welcome():
    print('\n' * 100)  # clear the screen
    print(colors.ANSI_BOLD +
          "CAL-AMITY: Make friends with your timetable and avoid disaster.".center(TERM_WIDTH) + '\n' +
          'A-Z) Select day    1-9) Select event    a-z) Commands   ?) Help'.center(
              TERM_WIDTH) + '\n' + colors.ANSI_RESET)


def task_code(event, day_idx=0, show_day_idx=False, selected=False):
    assert event.type == "task"
    assert event.code is not None
    if selected and show_day_idx:
        symbol = '**'
    elif show_day_idx:
        symbol = chr(ord('1') + day_idx) + ' '
    else:
        symbol = ''
    return (colors.ANSI_REVERSE +
            colors.ANSI_COLOR_DICT.get(event.color, '') +
            colors.BOLD_ON * selected * show_day_idx +
            (symbol + event.code).ljust(10)[:10] +  # pad to 10 characters
            colors.BOLD_OFF * selected * show_day_idx +
            colors.RESET_COLOR +
            colors.REVERSE_OFF)

def timetable(appointments, row_selected=False, chosen_event_idx=None):
    base_blocks = '▏   ' * (TIMETABLE_WIDTH // 4)
    blocks = list(base_blocks)
    for day_idx, appointment in enumerate(appointments):
        assert appointment.type == "appointment"
        start_quarter_hours = max(math.floor(appointment.start_time / 15) - TIMETABLE_START, 0)
        end_quarter_hours = min(math.ceil(appointment.end_time / 15) - TIMETABLE_START, TIMETABLE_WIDTH)
        bold = False
        for i in range(start_quarter_hours, end_quarter_hours):
            symbol = base_blocks[i]
            if row_selected:
                if day_idx == chosen_event_idx:
                    bold = True
                    symbol = '*'
                if start_quarter_hours == i:
                    symbol = chr(ord('1') + day_idx)
            blocks[i] = (colors.ANSI_REVERSE + colors.ANSI_COLOR_DICT.get(appointment.color, '') + colors.BACKGROUND_COLOR_DICT['white']*(symbol=='▏') +
                         colors.BOLD_ON * bold + symbol + colors.ANSI_RESET)
    return ''.join(blocks)


def chore_str(chore, day_idx=0, show_day_idx=False, selected=False):
    symbol = '⚫'
    return (colors.ANSI_COLOR_DICT.get(chore.color, '') + colors.ANSI_REVERSE * selected * show_day_idx + symbol + colors.REVERSE_OFF * selected * show_day_idx + colors.RESET_COLOR)


def day_row(julian_date, hotkey, selected=False, chosen_event_idx=None, session=None):
    # fetch events (tasks/appts) from database
    tasks, appointments, chores = database.fetch_days_events(julian_date, session=session)
    n_appointments, n_tasks, n_chores = len(appointments), len(tasks), len(chores)
    # pretty print
    appointments = timetable(appointments, row_selected=selected, chosen_event_idx=chosen_event_idx)
    tasks = ' '.join(task_code(task, day_idx=i, show_day_idx=selected, selected=(i == chosen_event_idx)) for i, task in
                     enumerate(tasks, start=n_appointments))
    chores = [chore_str(chore, day_idx=i, show_day_idx=selected, selected=(i == chosen_event_idx)) for i, chore in
              enumerate(chores, start=n_appointments + n_tasks)]
    chores = ''.join(['  '] * (4 - len(chores)) + chores[:4])
    # get date from julian date
    day_of_month = datetime.date.fromordinal(julian_date).day
    # completely reverse the order of the fstring
    return f"{chores}{appointments}▏ {day_of_month:>2}│{'*' + colors.ANSI_REVERSE if selected else ' '}{hotkey}{colors.REVERSE_OFF * selected} │{tasks}{colors.RESET}"


timetable_header = '        7   8   9  10  11  12   1   2   3   4   5   6   '

def display_calendar(from_date, chosen_date=None, chosen_event_idx=None, session=None):
    print(colors.WRAP_OFF + colors.CURSOR_OFF, end='') # reassert wrap off
    for i in range(NUM_DAYS):
        date_num = from_date + i
        date = datetime.date.fromordinal(date_num)
        if date.day == 1 or i == 0:
            print(MARGIN + timetable_header + colors.ANSI_BOLD + date.strftime("%B").center(9) + colors.ANSI_RESET)
        hotkey = chr(ord('A') + i)
        selected = chosen_date == date_num
        print(MARGIN + day_row(date_num, hotkey, selected=selected, chosen_event_idx=chosen_event_idx, session=session))
    print('\n' * 3)
    print(colors.UP_LINE * 3, end='')
