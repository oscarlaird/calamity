import datetime
import shutil

from sqlalchemy import text
import questionary

from calamity_calendar import display, database, modify, colors, help
from calamity_calendar.getch import getch


class Calamity:

    def __init__(self):
        self.session = None
        self.appointments = []
        self.tasks = []
        self.chores = []
        self.events = []
        self.today = datetime.date.today().toordinal()
        self._chosen_date = self.today
        self._chosen_event = None
        self.chosen_action = None
        self.param = None
        self.undo_stack = []
        self.redo_stack = []
        self.welcomed = False
        self.error = None
        self.from_date = self.today

    # define a setter for chosen_event (we defined the getter elsewhere)
    @property
    def chosen_event(self):
        return self._chosen_event

    @chosen_event.setter
    def chosen_event(self, event):
        self._chosen_event = event
        if event and event.date != self.chosen_date:
            self.chosen_date = event.date  # trigger date setter

    @property
    def chosen_date(self):
        return self._chosen_date

    @chosen_date.setter
    def chosen_date(self, date):
        if self.chosen_event and self.chosen_event.date != date:
            old_type = self.chosen_event.type
            old_chore_idx, old_task_idx = self.chore_idx, self.task_idx,
            old_appt_start, old_appt_end = self.chosen_event.start_time, self.chosen_event.end_time
        self._chosen_date = date
        self.appointments, self.tasks, self.chores = database.fetch_events(self.chosen_date, session=self.session)
        self.events = self.appointments + self.tasks + self.chores
        # fix the window
        if self.from_date + display.NUM_DAYS <= self.chosen_date:
            self.from_date = self.chosen_date - display.NUM_DAYS + 1
        elif self.chosen_date < self.from_date:
            self.from_date = self.chosen_date
        if self.chosen_event and self.chosen_event.date != date:
            if old_type == 'chore':
                self.chore_idx = old_chore_idx
            elif old_type == 'task':
                self.task_idx = old_task_idx
            elif old_type == 'appointment':
                self.chosen_event = None
                for event in self.appointments:
                    if (old_appt_start < event.end_time <= old_appt_end) or (
                            old_appt_start <= event.start_time < old_appt_end):
                        self.chosen_event = event
                        break
            else:
                self.chosen_event = None

    @property
    def chosen_event_idx(self):
        # get position of chosen event in events
        if self.chosen_event is None:
            return None
        for i, event in enumerate(self.events):
            if event.id == self.chosen_event.id:
                return i
        raise RuntimeError('Chosen event not in events')

    @chosen_event_idx.setter
    def chosen_event_idx(self, idx):
        self.chosen_event = self.events[idx] if (idx is not None and 0 <= idx < len(self.events)) else None

    @property
    def task_idx(self):
        if not self.chosen_event or self.chosen_event.type != 'task':
            return None
        return self.chosen_event_idx - len(self.appointments)

    @task_idx.setter
    def task_idx(self, idx):
        self.chosen_event_idx = len(self.appointments) + idx if idx < len(self.tasks) else None

    @property
    def appointment_idx(self):
        if not self.chosen_event or self.chosen_event.type != 'appointment':
            return None
        return self.chosen_event_idx

    @appointment_idx.setter
    def appointment_idx(self, idx):
        self.chosen_event_idx = idx if idx < len(self.appointments) else None

    @property
    def chore_idx(self):
        if not self.chosen_event or self.chosen_event.type != 'chore':
            return None
        return self.chosen_event_idx - len(self.appointments) - len(self.tasks)

    @chore_idx.setter
    def chore_idx(self, idx):
        self.chosen_event_idx = len(self.appointments) + len(self.tasks) + idx if idx < len(self.chores) else None

    def idx_of(self, event):
        for i, e in enumerate(self.events):
            if e.id == event.id:
                return i
        raise RuntimeError('Event not in events')

    COMMANDS = {
        'x': (modify.delete_event, "Delete"),
        'd': (modify.delete_event, "Delete"),
        'r': (modify.repeat_event, "Repeat"),
        'y': (modify.duplicate_event, "Duplicate"),
        's': (modify.detach_event, "Separate / Detach"),
        # Edit
        'ed': (modify.edit_date, "Move (edit date)"),
        'el': (modify.edit_description, "Edit Description"),
        'ec': (modify.edit_code, "Edit Code (task)"),
        'et': (modify.edit_time, "Edit Time (appt)"),
        'es': (modify.edit_start_time, "Edit Start (appt)"),
        'ee': (modify.edit_end_time, "Edit End (appt)"),
        ';': (modify.cycle_color, "Cycle Color"),
        ',': (modify.cycle_color_backwards, "Cycle Color Backwards"),
        '+d': (modify.postpone_day, "Postpone one day/week/month"),
        '+w': (modify.postpone_week, "Postpone one day/week/month"),
        '+m': (modify.postpone_month, "Postpone one day/week/month"),
        '=d': (modify.postpone_day, "Postpone one day/week/month"),
        '=w': (modify.postpone_week, "Postpone one day/week/month"),
        '=m': (modify.postpone_month, "Postpone one day/week/month"),
        '-d': (modify.prepone_day, "Prepone one day/week/month"),
        '-w': (modify.prepone_week, "Prepone one day/week/month"),
        '-m': (modify.prepone_month, "Prepone one day/week/month"),
        'm': (modify.edit_date, "Move (set date)"),
    }
    NEW_TYPES = ('a', 't', 'c')
    MOTIONS = (
        'j', 'k', 'h', 'l', 'w', 'b', '<', '>', '\t', ' ', '\n', '\r', 'n', 'p', '0', '$', 'gg', 'zz', 'zb', 'zt',
        '\x1b[A', '\x1b[B', '\x1b[C', '\x1b[D')
    MISC_COMMANDS = (
        '?', 'u', '\x12', '\x1b\x1b', 'q', '\x03', None, '~', 'v', 'o')  # help, undo, redo, quit, ctrl-c INTRANSITIVE

    def vim_getch(self):  # allow for g- z- etc. prefix commands
        c = getch(watch_resize=True)
        if c == 'g':
            c += getch()
            return c if c in ('gg',) else None
        elif c == 'z':
            print('t) top, b) bottom, z) center')
            c += getch()
            return c if c in ('zt', 'zb', 'zz') else None
        elif c == 'e':
            if not self.chosen_event:
                return None
            msg = 'Edit: d) date, l) label'
            if self.chosen_event.type == 'appointment':
                msg += ', t) time, s) start, e) end'
            elif self.chosen_event.type == 'task':
                msg += ', c) code'
            print(msg)
            c += getch()
            return c if c in ('ed', 'el', 'et', 'es', 'ee', 'ec') else None
        elif c in ('+', '=', '-'):
            if not self.chosen_event:
                return None
            print('Postpone: d) day, w) week, m) month')
            next_char = getch()
            return c + next_char if next_char in ('d', 'w', 'm') else None
        elif c == 'm':
            print('Move date: press a capital letter or two digits. E.g. mC, m09')
            new_date = None
            a = getch()
            if a.isdigit():
                b = getch()
                if b.isdigit():
                    new_day = 10 * int(a) + int(b)
                    for date in range(self.from_date, self.from_date + display.NUM_DAYS):
                        if datetime.date.fromordinal(date).day == new_day:
                            new_date = date
                            break
            elif 0 <= (day_num := ord(a.upper()) - ord('A')) < display.NUM_DAYS:
                new_date = self.from_date + day_num
            if new_date is not None:
                self.param = new_date
            return 'm'
        return c

    def main_loop(self):
        print('here')
        self.session = database.Session()
        self.session.execute(text(f'SAVEPOINT SP_0'))
        with self.session:
            while True:
                self.display()
                c = self.vim_getch()
                if c in self.MISC_COMMANDS:
                    self.do_misc_command(c)
                elif c in self.MOTIONS:
                    self.process_motion(c)
                elif len(c) == 1 and 0 <= (index := ord(c) - ord('A')) < display.NUM_DAYS:  # select date by letter
                    self.chosen_date = self.from_date + index
                elif len(c) == 1 and 0 <= (index := ord(c) - ord('1')) < len(self.events):  # select event by number
                    self.chosen_event_idx = index
                c = self.chosen_action or c  # allow ctrl-R to replay the last action
                if c in self.COMMANDS or c in self.NEW_TYPES:
                    self.do_command(c)
                else:
                    pass

    def display(self):
        # DISPLAY
        print(colors.CLEAR_SCREEN + colors.CURSOR_OFF + colors.WRAP_OFF, end='')
        self.chosen_date = self.chosen_date  # update events
        if self.welcomed:  # hide the events on the first screen
            display.show_days_events(self)
        elif not self.welcomed:
            display.welcome()
            self.welcomed = True

        display.display_calendar(self)
        # print(self.undo_stack, self.redo_stack)

    def do_misc_command(self, c):
        if c is None:  # terminal was resized
            display.refresh_term_size()
        elif c == 'u':
            if self.undo_stack:
                self.session.execute(text(f'ROLLBACK TO SP_{len(self.undo_stack) - 1}'))  # rollback to the savepoint
                self.session.expire_all()  # invalidates all cached objects, must reload them from the database
                self.chosen_date, idx, _, _ = self.undo_stack[-1]  # copy coordinates from undo stack
                self.chosen_event_idx = idx  # make sure we have the correct date before setting chosen_event_idx
                self.redo_stack.append(self.undo_stack.pop())
        elif c == '\x12':  # CTRL-R redo
            if self.redo_stack:
                self.chosen_date, chosen_event_idx, self.chosen_action, self.param = self.redo_stack[-1]  # replay
                self.chosen_event_idx = chosen_event_idx  # refresh chosen_date
        elif c == '?':
            # open help.txt
            print(colors.ALT_SCREEN + help.help)
            getch()
            print(colors.MAIN_SCREEN)
        elif c == '\x1b\x1b' or c == 'q' or c == '\x03':  # ESC ESC or q or ctrl-c
            if c == '\x03' and questionary.confirm("Quit without saving (undo all changes)?", default=False).ask():
                self.session.rollback()
                raise KeyboardInterrupt
            self.session.commit()
            exit()
        elif c == '~':
            display.toggle_military()
        elif c == 'v':
            # make a backup of the database
            target = questionary.path(message="Backup database location: ", only_directories=True).ask()
            shutil.copy(database.DB_PATH, target)
        elif c == 'o':
            # OPTIONS / config
            pass


    def do_command(self, c):
        self.chosen_action = c
        if not self.chosen_event and not (self.chosen_action in self.NEW_TYPES):
            return
        triple = [self.chosen_date, self.chosen_event_idx, self.chosen_action, None]
        if self.chosen_action in self.NEW_TYPES:
            assert self.chosen_date
            new_type = "appointment" if self.chosen_action == 'a' else "task" if self.chosen_action == 't' else "chore"
            new_event = database.Event(date=self.chosen_date, type=new_type)
            self.session.add(new_event)
            self.session.flush()  # get the id and default values back from the database
            self.param = modify.add_event(new_event, self.session, param=self.param)
            self.chosen_event = new_event
        elif self.chosen_action in self.COMMANDS and self.chosen_event:
            # save the parameters of the command in case we need to redo
            command = self.COMMANDS[self.chosen_action][0]
            self.param = command(self.chosen_event, session=self.session, param=self.param)
            self.chosen_event = self.chosen_event  # cause chosen_date to be updated
        else:
            raise ValueError(f"Unknown action {self.chosen_action}")
        triple[3] = self.param
        self.make_savepoint(triple)

    def make_savepoint(self, triple):
        # SAVEPOINT
        # create new savepoint
        if self.redo_stack and triple != self.redo_stack.pop():
            self.redo_stack = []
        self.undo_stack.append(triple)
        self.session.flush()  # synchronize the database with the session before saving
        self.session.execute(text(f'SAVEPOINT SP_{len(self.undo_stack)}'))
        self.chosen_action = None  # wait to get a new action
        self.param = None

    def process_motion(self, c):
        if c == 'j':
            self.chosen_date += 1
        elif c == 'k':
            self.chosen_date -= 1
        elif c == 'h':
            if not self.events:
                pass
            elif self.chosen_event_idx is None:
                if self.appointments:
                    self.appointment_idx = len(self.appointments) - 1
                elif self.chores:
                    self.chore_idx = len(self.chores) - 1
            else:
                self.chosen_event_idx = (self.chosen_event_idx - 1) % len(self.events)
        elif c == 'l':
            if not self.events:
                pass
            elif self.chosen_event_idx is None:
                if self.tasks:
                    self.task_idx = 0
            else:
                self.chosen_event_idx = (self.chosen_event_idx + 1) % len(self.events)
        elif c == 'w':
            self.chosen_date += 7
        elif c == 'b':
            self.chosen_date -= 7
        elif c == '<' or c == '>':
            old = datetime.date.fromordinal(self.chosen_date)  # set new_date to the previous month
            if c == '<':
                new_date = old.replace(year=old.year - (old.month == 1), month=(old.month - 2) % 12 + 1,
                                       day=1)  # get the number of days in this month n_days (e.g. 28 for Feb)
            elif c == '>':
                new_date = old.replace(year=old.year + (old.month == 12), month=old.month % 12 + 1, day=1)
            n_days = (new_date.replace(year=new_date.year + (new_date.month == 12),
                                       month=new_date.month % 12 + 1) - new_date).days
            new_date = new_date.replace(
                day=min(old.day, n_days))  # try to keep the same day of the month if possible
            difference = old.toordinal() - new_date.toordinal()
            self.chosen_date -= difference
            self.from_date -= difference
        elif c == '\t':  # cycle through chores
            if self.chore_idx is not None:
                self.chore_idx = (self.chore_idx + 1) % len(self.chores)
            elif self.chores:
                self.chore_idx = 0
        elif c == '\n' or c == '\r':  # cycle thru tasks
            if self.task_idx is not None:
                getch()
                self.task_idx = (self.task_idx + 1) % len(self.tasks)
            elif self.tasks:
                getch()
                self.task_idx = 0
        elif c == ' ':  # cycle thru appointments
            if self.appointment_idx is not None:
                self.appointment_idx = (self.appointment_idx + 1) % len(self.appointments)
            elif self.appointments:
                self.appointment_idx = 0
        elif c == 'n' or c == 'p':  # next occurrence of repeated event
            if not self.chosen_event or not self.chosen_event.recurrence_parent:
                pass
            else:
                # query the database for the next occurrence of the event (having a later date)
                filter_order = database.Event.date > self.chosen_event.date if c == 'n' else database.Event.date < self.chosen_event.date
                order_by = database.Event.date if c == 'n' else database.Event.date.desc()
                next_event = self.session.query(database.Event).filter_by(
                    recurrence_parent=self.chosen_event.recurrence_parent).filter(
                    filter_order).order_by(order_by).first()
                self.chosen_event = next_event or self.chosen_event
        elif c == 'gg':
            self.chosen_date = self.today
        elif c == 'zz':
            self.from_date = self.chosen_date - display.NUM_DAYS // 2
        elif c == 'zb':
            self.from_date = self.chosen_date - display.NUM_DAYS + 1
        elif c == 'zt':
            self.from_date = self.chosen_date
        elif c == '0':
            self.chosen_event_idx = len(self.appointments) + len(self.tasks)
        elif c == '$':
            self.chosen_event_idx = len(self.appointments) + len(self.tasks) - 1
        elif c == '\x1b[A':  # ctrl-up
            self.from_date -= 1
            if self.chosen_date - self.from_date >= display.NUM_DAYS:
                self.chosen_date -= 1
        elif c == '\x1b[B':  # ctrl-down
            self.from_date += 1
            if self.chosen_date < self.from_date:
                self.chosen_date += 1
        elif c == '\x1b[C':  # ctrl-right
            if display.TIMETABLE_START_HOUR < 12:
                display.change_start_time(display.TIMETABLE_START_HOUR + 1)
        elif c == '\x1b[D':
            if display.TIMETABLE_START_HOUR > 0:
                display.change_start_time(display.TIMETABLE_START_HOUR - 1)


def run():
    Calamity().main_loop()


if __name__ == '__main__':
    run()
