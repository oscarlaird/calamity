import math
import datetime
# to get the width of the terminal, use shutil.get_terminal_size().columns
import shutil
# import signal
import wcwidth

from calamity_calendar import colors, database

import sys
from io import StringIO


class Buffer(StringIO):
    def flush(self):
        print(self.getvalue(), end='', file=sys.stdout, flush=True)
        self.truncate(0)  # Clear the current buffer
        self.seek(0)  # Reset the position


buffer = Buffer()

N_HOURS = 12
TIMETABLE_WIDTH = N_HOURS * 4
TABLE_WIDTH = 8 + TIMETABLE_WIDTH + 8 + 10 * 3 + 2


def get_num_days():
    # terminal height minus 15
    num_days = shutil.get_terminal_size().lines - 17
    # show at least a week and at most 30 days
    return min(max(num_days, 7), 30)


def get_timetable_start():
    return database.config['start_hour'] * 4


def get_timetable_end():
    return (database.config['start_hour'] + N_HOURS) * 4


def get_term_width():
    return shutil.get_terminal_size().columns


def get_margin():
    return ' ' * ((get_term_width() - TABLE_WIDTH) // 2)


def get_timetable_header():
    fill = '0' if database.config['military_time'] else ' '
    nums = range(database.config['start_hour'], database.config['start_hour'] + N_HOURS)
    if not database.config['military_time']:
        nums = [(n - 1) % 12 + 1 for n in nums]
    return ' ' * 7 + '  '.join(str(n).rjust(2, fill) for n in nums) + ' ' * 3


def welcome():
    print('\n' * 100, file=buffer)  # clear the screen
    print(colors.ANSI_BOLD +
          "CAL-AMITY: Make friends with your timetable and avoid disaster.".center(get_term_width()) + '\n\n' +
          'Press ? for HELP.'.center(get_term_width()) + '\n' +
          colors.ANSI_RESET,
          file=buffer)


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
    code = conditional_rot13(task.code)
    return prefix + (symbol + code).ljust(10)[:10] + suffix  # pad to 10 characters


def tasks_row(date, cal):
    return ' '.join(task_code(task, cal) for task in database.fetch_tasks(date, cal.session))


def timetable_row(date, cal):
    appointments = database.fetch_appointments(date, cal.session)
    row_selected = date == cal.chosen_date
    base_blocks = '▏   ' * (TIMETABLE_WIDTH // 4)
    blocks = [block for block in base_blocks]
    for idx, appointment in enumerate(appointments):
        assert appointment.type == "appointment"
        start_quarter_hours = max(math.floor(appointment.start_time / 15) - get_timetable_start(), 0)
        end_quarter_hours = min(math.ceil(appointment.end_time / 15) - get_timetable_start(), TIMETABLE_WIDTH)
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
        prefix = colors.ANSI_REVERSE + colors.ANSI_COLOR_DICT.get(appointment.color, '') + colors.BACKGROUND_COLOR_DICT[
            'white']
        if selected:
            prefix += colors.BOLD_ON + colors.BACKGROUND_COLOR_DICT['black']
        blocks[start_quarter_hours] = prefix + blocks[start_quarter_hours]
        blocks[end_quarter_hours - 1] += colors.ANSI_RESET
    return ''.join(blocks)


def chore_str(chore, cal):
    symbol = '●'
    if wcwidth.wcwidth(symbol) == 1:
        symbol += ' '
    selected = chore is cal.chosen_event
    return (colors.ANSI_COLOR_DICT.get(chore.color, '') +
            colors.ANSI_REVERSE * selected + symbol + colors.REVERSE_OFF * selected + colors.RESET_COLOR)


def chores_row(date, cal):
    chores = database.fetch_chores(date, cal.session)
    chores = [chore_str(chore, cal) for chore in chores]
    chores = ''.join(['  '] * (4 - len(chores)) + chores[3::-1])  # pad to 4 chores
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
    hotkey = str(colors.ANSI_REVERSE) * selected + hotkey + str(colors.REVERSE_OFF) * selected
    return f"{chores}{appointments}▏ {day_of_month:>2}│{'*' if selected else ' '}{hotkey} │{tasks}{colors.RESET}"


def display_calendar(cal):
    for i in range(get_num_days()):
        date_num = cal.from_date + i
        date = datetime.date.fromordinal(date_num)
        if date.day == 1 or i == 0:
            print(get_margin() + get_timetable_header() + colors.ANSI_BOLD + date.strftime("%B").center(
                9) + colors.ANSI_RESET,
                  file=buffer)
        print(get_margin() + day_row(date_num, cal), file=buffer)


def show_days_events(cal):
    prev_type = None
    for i, event in enumerate(cal.events):
        if event.type != prev_type:
            print(get_margin() + f"          {event.type.capitalize()}s:", file=buffer)
            prev_type = event.type
        text = conditional_rot13(event.description or event.code)
        print(get_margin() + f"            {chr(ord('1') + i)}) "
                             f"{colors.ANSI_COLOR_DICT[event.color]}{colors.ANSI_REVERSE * (event is cal.chosen_event)}"
                             f"{text}"
                             f"{colors.ANSI_RESET}",
              file=buffer)
    print(file=buffer)


welcomed = False


def show_all(cal):
    print(colors.CLEAR_SCREEN + colors.CURSOR_OFF + colors.WRAP_OFF, end='', file=buffer)
    global welcomed
    if welcomed:
        show_days_events(cal)
    elif not welcomed:
        welcome()
        welcomed = True
    display_calendar(cal)
    print(file=buffer)
    for line in (lines := cal.message.splitlines()[:3]):
        print(line.center(get_term_width()), file=buffer)
    print('\n' * (3 - len(lines)), end='', file=buffer)
    buffer.flush()  # print the buffer
    print(colors.UP_LINE * 3 + colors.CLEAR_TO_END, end='')  # clear the last line when we next print


rot13_trans = str.maketrans(
    'ABCDEFGHIJKLMabcdefghijklmNOPQRSTUVWXYZnopqrstuvwxyz',
    'NOPQRSTUVWXYZnopqrstuvwxyzABCDEFGHIJKLMabcdefghijklm'
)


def rot13(text):
    # Define the ROT13 translation table
    return text.translate(rot13_trans)


def conditional_rot13(text):
    # Do ROT13 if the config says so
    return rot13(text) if database.config['ROT13'] else text
