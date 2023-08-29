import math
import datetime
# to get the width of the terminal, use shutil.get_terminal_size().columns
import shutil
import signal
import wcwidth

from calamity_calendar import colors, database

NUM_DAYS = 30
MILITARY = False
TIMETABLE_START_HOUR = 7
TIMETABLE_START = 7 * 4  # start at 7am
TIMETABLE_END = 19 * 4  # end at 7pm
TIMETABLE_WIDTH = 48
TABLE_WIDTH = 8 + 48 + 8 + 10 * 3 + 2

TERM_WIDTH = shutil.get_terminal_size().columns
MARGIN = ' ' * ((TERM_WIDTH - TABLE_WIDTH) // 2)

timetable_header = '        7   8   9  10  11  12   1   2   3   4   5   6   '

def refresh_term_size():
    global TERM_WIDTH, MARGIN
    TERM_WIDTH = shutil.get_terminal_size().columns
    MARGIN = ' ' * ((TERM_WIDTH - TABLE_WIDTH) // 2)

def toggle_military():
    global MILITARY
    MILITARY = not MILITARY
    change_start_time(TIMETABLE_START_HOUR)

def change_start_time(hour):
    global TIMETABLE_START, TIMETABLE_START_HOUR, TIMETABLE_END, timetable_header
    TIMETABLE_START_HOUR = hour
    TIMETABLE_START = hour * 4
    TIMETABLE_END = (hour + 12) * 4
    fill = '0' if MILITARY else ' '
    nums = range(hour, hour + 12)
    if not MILITARY:
        nums = [(n - 1) % 12 + 1 for n in nums]
    timetable_header = ' '*7 + '  '.join(str(n).rjust(2, fill) for n in nums) + ' '*3


# Set up signal handler for SIGWINCH
signal.signal(signal.SIGWINCH, lambda signum, frame: refresh_term_size())

def welcome():
    print('\n' * 100)  # clear the screen
    print(colors.ANSI_BOLD +
          "CAL-AMITY: Make friends with your timetable and avoid disaster.".center(TERM_WIDTH) + '\n' +
          'A-Z) Select day    1-9) Select event    a-z) Commands   ?) Help'.center(
              TERM_WIDTH) + '\n' + colors.ANSI_RESET)


def task_code(task, cal):
    assert task.type == "task"
    assert task.code is not None
    symbol = ''
    prefix, suffix = colors.ANSI_REVERSE + colors.ANSI_COLOR_DICT.get(task.color, ''), colors.ANSI_RESET
    if task.date == cal.chosen_date:
        symbol = chr(ord('1') + cal.idx_of(task)) + ' '
    if task is cal.chosen_event:
        symbol = '**'
        prefix += colors.BOLD_ON
    return prefix + (symbol + task.code).ljust(10)[:10] + suffix  # pad to 10 characters

def tasks_row(date, cal):
    return ' '.join(task_code(task, cal) for task in database.fetch_tasks(date, cal.session))

def timetable_row(date, cal):
    appointments = database.fetch_appointments(date, cal.session)
    row_selected = date == cal.chosen_date
    base_blocks = '▏   ' * (TIMETABLE_WIDTH // 4)
    blocks = list(base_blocks)
    for idx, appointment in enumerate(appointments):
        assert appointment.type == "appointment"
        start_quarter_hours = max(math.floor(appointment.start_time / 15) - TIMETABLE_START, 0)
        end_quarter_hours = min(math.ceil(appointment.end_time / 15) - TIMETABLE_START, TIMETABLE_WIDTH)
        if start_quarter_hours >= TIMETABLE_WIDTH or end_quarter_hours <= 0:
            continue
        selected = appointment is cal.chosen_event
        for i in range(start_quarter_hours, end_quarter_hours):
            symbol = base_blocks[i]
            if selected:
                symbol = '*'
            if row_selected and start_quarter_hours == i:
                symbol = chr(ord('1') + idx)
            blocks[i] = symbol
        prefix = colors.ANSI_REVERSE + colors.ANSI_COLOR_DICT.get(appointment.color, '') + colors.BACKGROUND_COLOR_DICT['white'] + colors.BOLD_ON * selected
        blocks[start_quarter_hours] = prefix + blocks[start_quarter_hours]
        blocks[end_quarter_hours - 1] += colors.ANSI_RESET
    return ''.join(blocks)


def chore_str(chore, cal):
    symbol = '●'
    if wcwidth.wcwidth(symbol) == 1:
        symbol += ' '
    selected = chore is cal.chosen_event
    return colors.ANSI_COLOR_DICT.get(chore.color, '') + colors.ANSI_REVERSE * selected + symbol + colors.REVERSE_OFF * selected + colors.RESET_COLOR

def chores_row(date, cal):
    chores = database.fetch_chores(date, cal.session)
    chores = [chore_str(chore, cal) for chore in chores]
    chores = ''.join(['  '] * (4 - len(chores)) + chores[:4])  # pad to 4 chores
    return chores


def day_row(date, cal):
    # pretty print
    appointments = timetable_row(date, cal)
    tasks = tasks_row(date, cal)
    chores = chores_row(date, cal)
    # get day of month from julian date
    day_of_month = datetime.date.fromordinal(date).day
    selected = date == cal.chosen_date
    hotkey = chr(ord('A') + date - cal.from_date)
    hotkey = colors.ANSI_REVERSE * selected + hotkey + colors.REVERSE_OFF * selected
    return f"{chores}{appointments}▏ {day_of_month:>2}│{'*' if selected else ' '}{hotkey} │{tasks}{colors.RESET}"



def display_calendar(cal):
    for i in range(NUM_DAYS):
        date_num = cal.from_date + i
        date = datetime.date.fromordinal(date_num)
        if date.day == 1 or i == 0:
            print(MARGIN + timetable_header + colors.ANSI_BOLD + date.strftime("%B").center(9) + colors.ANSI_RESET)
        print(MARGIN + day_row(date_num, cal))
    print('\n' * 3)
    print(colors.UP_LINE * 3, end='')

def show_days_events(cal):
    prev_type = None
    for i, event in enumerate(cal.events):
        if event.type != prev_type:
            print(MARGIN + f"          {event.type.capitalize()}s:")
            prev_type = event.type
        print(MARGIN + f"            {chr(ord('1') + i)}) "
                       f"{colors.ANSI_COLOR_DICT[event.color]}{colors.ANSI_REVERSE * (event is cal.chosen_event)}"
                       f"{event.description or event.code}"
                       f"{colors.ANSI_RESET}")
    print()
