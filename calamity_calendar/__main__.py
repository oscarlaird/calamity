import datetime
import shutil
import os
import time

from sqlalchemy import text, sql
import questionary

from calamity_calendar import display, database, modify, colors, help, dateutils
from calamity_calendar.getch import getch

class TrieNode(dict):

    def __init__(self, message):
        super().__init__()
        self.message = message

class Calamity:

    def __init__(self):
        self.session = None
        self.config = None
        self.appointments = []
        self.tasks = []
        self.chores = []
        self.events = []
        self.today = datetime.date.today().toordinal()
        self._chosen_date = self.today
        self._chosen_event = None
        self.chosen_action = None
        self.param = None
        # undo/redo
        self.undo_stack = []
        self.redo_stack = []
        # search
        self.search = ''
        self.matching = None
        # message
        self.welcomed = False
        self.error = None
        self.message = ''
        # window
        self.from_date = self.today
        # yank/paste
        self.yank = None
        self.group_yank = False

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
        # save the idx of the old event
        if self.chosen_event and self.chosen_event.date != date:
            old_type = self.chosen_event.type
            old_chore_idx, old_task_idx = self.chore_idx, self.task_idx,
            old_appt_start, old_appt_end = self.chosen_event.start_time, self.chosen_event.end_time
        # set the chosen date and re-fetch the list of events
        self._chosen_date = date
        self.appointments, self.tasks, self.chores = database.fetch_events(self.chosen_date, session=self.session)
        self.events = self.appointments + self.tasks + self.chores
        # fix the window
        if self.from_date + display.NUM_DAYS <= self.chosen_date:
            self.from_date = self.chosen_date - display.NUM_DAYS + 1
        elif self.chosen_date < self.from_date:
            self.from_date = self.chosen_date
        # try to keep the same chore_idx/appt_idx/task_idx if possible
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
        'x': (modify.kill_event, "Delete"),
        'X': (modify.kill_future_events, "Delete Future Events"),
        'r': (modify.repeat_event, "Repeat"),
        's': (modify.detach_event, "Separate / Detach"),
        # Edit
        'eD': (modify.edit_date, "Move (edit date)"),
        'ed': (modify.edit_description, "Edit Description"),
        'ec': (modify.edit_code, "Edit Code (task)"),
        'et': (modify.edit_time, "Edit Time (appt)"),
        ';': (modify.cycle_color_forwards, "Cycle Color"),
        ',': (modify.cycle_color_backwards, "Cycle Color Backwards"),
        '+': (modify.postpone_day, "Postpone one day/week/month"),
        '=': (modify.postpone_day, "Postpone one day/week/month"),
        '-': (modify.prepone_day, "Prepone one day/week/month"),
        'm': (modify.edit_date, "Move (set date)"),
    }
    COMMANDS.update({'g'+key: value for key, value in COMMANDS.items()})  # group commands
    del COMMANDS['X']
    NEW_TYPES = ('a', 't', 'c')
    MOTIONS = {  # motions take precedence over capital letters
        'j', 'k', 'h', 'l', 'w', 'b', '<', '>', '\t', ' ', '\n', '\r', 'n', '*', '#', '/', '0', '$', 'gg', 'zz', 'zb', 'zt', 'y','gy',
        '\x1b[A', '\x1b[B', '\x1b[C', '\x1b[D', 'zl', 'zh', 'zj', 'zk'
    }
    MISC_COMMANDS = (
        '?', 'g?', 'u', '\x12', '\x1b\x1b', 'q', '\x03', None, '~', 'v', 'o', 'p','gp')  # help, undo, redo, quit, ctrl-c INTRANSITIVE

    def vim_getch(self):  # allow for g- z- etc. prefix commands
        c = getch(watch_resize=True)
        if c == 'g':
            print('GROUP EDIT: D) date, d) description, t) time, s) start, f) finish, c) code\n'
                  'GROUP CMD:  x) delete, r) repeat, s) separate, ;) cycle color, ,) cycle color backwards\n'
                  '            +) postpone, =) postpone, -) prepone, m) move, y) yank, p) paste\n'
                  'MISC:       g?) rot13 encrypt, gg) jump to today')
            next_char = getch()
            if next_char == 'e':
                next_char = getch()
            if next_char in ('g','?','y','p'):
                return c + next_char
            elif next_char in self.COMMANDS:
                return c + next_char  # TODO get -> e && gt -> t (both are wrong)
        elif c == 'z':
            print('Move view:\t t) top, b) bottom, z) center\t h) left, l) right, j) down, k) up')
            next_char = getch()
            return c + next_char if next_char in ('t', 'b', 'z', 'h', 'l', 'j', 'k') else None
        elif c == 'e':
            if not self.chosen_event:
                return None
            msg = 'Edit: D) date, d) description'
            if self.chosen_event.type == 'appointment':
                msg += ', t) time, s) start, f) finish'
            elif self.chosen_event.type == 'task':
                msg += ', c) code'
            print(msg)
            c += getch()
            return c if c in ('eD', 'ed', 'et', 'es', 'ef', 'ec') else None
        elif c == 'm':
            # TODO make it possible to do m2j, m1w, etc. (even m9h). Lots to think of here.
            print('+w) plus one week\t\t -m) minus one month')
            print('09) ninth of the month L) move to date L')
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
            elif a in ('+','-'):
                direction = 1 if a == '+' else -1
                b = getch()
                # cast chosen_date to datetime.date
                if b == 'd':
                    new_date = self.chosen_date + 1 * direction
                elif b == 'w':
                    new_date = self.chosen_date + 7 * direction
                elif b == 'm':
                    new_date = dateutils.add_month(self.chosen_date, back=(direction == -1))
                else:
                    pass
            if new_date is not None:
                self.param = new_date
            return 'm'
        return c

    def main_loop(self):
        self.session = database.Session()
        self.config = database.ConfigDict(self.session)
        self.session.execute(text(f'SAVEPOINT SP_0'))
        with self.session:
            display.set_military(self.config['military_time'])
            display.change_start_time(self.config['start_hour'])
            while True:
                self.display()
                c = self.vim_getch()
                if c in self.MISC_COMMANDS:
                    self.do_misc_command(c)
                elif c in self.MOTIONS:  # motions take precedence over capital letters
                    self.process_motion(c)
                elif len(c) == 1 and 0 <= (index := ord(c) - ord('A')) < display.NUM_DAYS:  # select date by letter
                    self.chosen_date = self.from_date + index
                elif len(c) == 1 and 0 <= (index := ord(c) - ord('1')) < len(self.events):  # select event by number
                    self.chosen_event_idx = index
                c = self.chosen_action or c  # allow ctrl-R to replay the last action (also paste uses this)
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
        if self.message:
            print(self.message)
            self.message = ''
        # print(self.undo_stack, self.redo_stack)
        # print(repr(self.config))

    def do_misc_command(self, c):
        if c is None:  # terminal was resized
            display.refresh_term_size()
        elif c == 'u':
            if self.undo_stack:
                self.session.execute(text(f'ROLLBACK TO SP_{len(self.undo_stack) - 1}'))  # rollback to the savepoint
                self.session.expire_all()  # invalidates all cached objects, must reload them from the database
                self.chosen_event = None  # the chosen event may have been deleted, so we need to reset it to avoid errors
                self.chosen_date, idx, _, _, _ = self.undo_stack[-1]  # copy coordinates from undo stack
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
            self.config['military_time'] = not self.config['military_time']
            display.set_military(self.config['military_time'])
        elif c == 'v':
            # make a backup of the database
            self.session.commit()
            self.config['backup_location'] = questionary.path(message="Backup database location: ", only_directories=True,
                                                              default=self.config['backup_location']).ask()
            shutil.copy(database.DB_PATH, os.path.expanduser(self.config['backup_location']))
        elif c == 'o':
            # OPTIONS / config
            # military_time, timezone, save_location, autosave,
            pass
        elif c == 'p' or c == 'gp':
            # Instead of treating this as add_event we could treat it as a repeat with n=1
            if self.yank:
                self.chosen_action = 'gr' if (self.group_yank or c == 'gp') else 'r'
                difference = self.chosen_date - self.yank.date
                self.param = (difference, 1)
                self.chosen_event = self.yank
        elif c == 'g?':
            # ROT13 encrypt the entire database (description and code)
            start_time = time.time()
            for event in self.session.query(database.Event).all():
                event.description = display.rot13(event.description or '')
                event.code = display.rot13(event.code or '')
            end_time = time.time()
            self.message = f"ROT13 took {int((end_time - start_time)*1000)}ms"



    def do_command(self, c):
        self.chosen_action = c
        if not self.chosen_event and not (self.chosen_action in self.NEW_TYPES):
            return
        # chosen_date, chosen_event_idx, chosen_action (command), param, group
        triple = [self.chosen_date, self.chosen_event_idx, self.chosen_action, None, False]
        if self.chosen_action in self.NEW_TYPES:
            assert self.chosen_date
            new_type = "appointment" if self.chosen_action == 'a' else "task" if self.chosen_action == 't' else "chore"
            new_event = database.Event(date=self.chosen_date, type=new_type)
            self.session.add(new_event)
            self.session.flush()  # get the id and default values back from the database
            self.param = modify.add_event(new_event, self.session, param=self.param)
            self.chosen_event = new_event
        elif self.chosen_action in self.COMMANDS and self.chosen_event:
            # TODO x/gx/gX should yank the event/group
            # TODO this requires that yank isn't an event (which could be deleted)
            if self.chosen_action.startswith('g'):
                triple[4] = True
                self.chosen_action = self.chosen_action[1:]
            # save the parameters of the command in case we need to redo
            command = self.COMMANDS[self.chosen_action][0]
            self.param = command(self.chosen_event, session=self.session, param=self.param, group=triple[4])
            if self.chosen_action in ('x','d'):
                self.chosen_event_idx = None
                self.chosen_date = self.chosen_date  # refresh events list
                self.chosen_event_idx = triple[1]
            else:
                self.chosen_event = self.chosen_event  # cause chosen_date to be updated and also lists of events
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
            old_date = self.chosen_date
            self.chosen_date = dateutils.add_month(self.chosen_date, back=(c == '<'))
            self.from_date += (self.chosen_date - old_date)
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
        elif c == '/':  # search
            self.search = questionary.text("Search: ", default=self.search).ask()
            self.matching = (database.Event.description.like(f'%{self.search}%') |
                                database.Event.code.like(f'%{self.search}%')) if self.search else None
            self.search_motion(back=False)
            self.MOTIONS.add('N')  # add N to the list of motions
        elif c == 'n' or c == 'N':  # next or previous search result
            self.search_motion(back=(c == 'N'))
        elif c == '*' or c == '#':  # next occurrence of repeated event
            if self.chosen_event and self.chosen_event.recurrence_parent:
                self.matching = (database.Event.recurrence_parent == self.chosen_event.recurrence_parent)
                self.search_motion(back=(c == '#'))
                self.MOTIONS.add('N')  # add N to the list of motions
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
        elif c == '\x1b[A' or c == 'zk':  # up
            self.from_date -= 1
            if self.chosen_date - self.from_date >= display.NUM_DAYS:
                self.chosen_date -= 1
        elif c == '\x1b[B' or c == 'zj':  # down
            self.from_date += 1
            if self.chosen_date < self.from_date:
                self.chosen_date += 1
        elif c == '\x1b[C' or c == 'zl':  # right
            if self.config['start_hour'] < 12:
                self.config['start_hour'] += 1
                display.change_start_time(self.config['start_hour'])
        elif c == '\x1b[D' or c == 'zh':  # left
            if self.config['start_hour'] > 0:
                self.config['start_hour'] -= 1
                display.change_start_time(self.config['start_hour'])
        elif c == 'y':
            self.yank = self.chosen_event
            self.group_yank = False
        elif c == 'gy':
            self.yank = self.chosen_event
            self.group_yank = True

    def search_motion(self, back=False):
        # back is True if we are searching backwards
        # e.g. matching = database.Event.description.like(f'%{self.search}%')
        # e.g. matching = database.Event.recurrence_parent == self.chosen_event.recurrence_parent
        # check that there is a search to do
        if self.matching is None:
            return
        # sqlalchemy objects
        is_today = database.Event.date == self.chosen_date
        is_chosen = (database.Event.id == self.chosen_event.id) if self.chosen_event else sql.false()
        order_by = database.Event.date % self.chosen_date
        order_by = order_by.desc() if back else order_by
        # search for the next occurrence on the same day
        todays_matches = self.session.query(database.Event).filter(self.matching & is_today & ~is_chosen).all()
        for event in self.events[self.chosen_event_idx::(-1 if back else 1)]:  # search backwards if we are going backwards
            if event in todays_matches:
                self.chosen_event = event
                return
        # if we didn't find anything, search for the next day with an occurrence
        next_date = self.session.query(database.Event.date).filter(self.matching & ~is_today).order_by(order_by).first()
        # if we found a date, go to it
        if next_date:
            self.chosen_event = None
            self.chosen_date = next_date[0]
            is_today = database.Event.date == self.chosen_date
            todays_matches = self.session.query(database.Event).filter(self.matching & is_today).all()
        # find the first event on that date
        for event in self.events[::(-1 if back else 1)]:  # search backwards if we are going backwards
            if event in todays_matches:
                self.chosen_event = event
                return


def run():
    Calamity().main_loop()


if __name__ == '__main__':
    run()
