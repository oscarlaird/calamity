import datetime
import shutil
import os
import time

from sqlalchemy import text, sql
import questionary

from calamity_calendar import display, database, modify, colors, help, dateutils
from calamity_calendar.getch import getch

from string import ascii_uppercase, ascii_lowercase, digits

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

    # represent the commands using a trie
    # parent nodes.
    R = ROOT = TrieNode('')
    R['e'] = TrieNode(message='e) edit')
    R['z'] = TrieNode(message='z) center, zt) top, zb) bottom, zz) center, zh) left, zl) right, zj) down, zk) up')
    R['g'] = TrieNode(message='gg) jump to today, gy) group yank')
    R['g']['e'] = TrieNode(message='ge) group edit')
    R['\x1b'] = TrieNode(message='ESC ESC) quit, ESC) cancel')
    R['\x1b']['['] = TrieNode(message='ESC [) quit, ESC) cancel')
    # difficulty of migration: letters/numbers, motions, misc_commands, new_types, commands, group commands
    # CAPITAL LETTERS
    for c in ascii_uppercase:
        R[c] = lambda self, c=c: setattr(self, 'chosen_date', self.from_date + ord(c) - ord('A'))
    # NUMBERS
    for c in digits[1:]:
        R[c] = lambda self, c=c: setattr(self, 'chosen_event_idx', int(c) - 1)
    # MOTIONS
    R['j'] = lambda self: setattr(self, 'chosen_event_idx', self.chosen_event_idx + 1)
    R['k'] = lambda self: setattr(self, 'chosen_event_idx', self.chosen_event_idx - 1)
    R['h'] = lambda self: self.move_horizontal()
    R['l'] = lambda self: self.move_horizontal(back=True)
    R['w'] = lambda self: setattr(self, 'chosen_date', self.chosen_date + 7)
    R['b'] = lambda self: setattr(self, 'chosen_date', self.chosen_date - 7)
    R['<'] = lambda self: self.move_month(back=True)
    R['>'] = lambda self: self.move_month()
    R['\t'] = lambda self: self.cycle_event_by_type('chore')
    R[' '] = lambda self: self.cycle_event_by_type('appointment')
    R['\n'] = lambda self: self.cycle_event_by_type('task')  # TODO check if getch works properly
    R['\r'] = lambda self: self.cycle_event_by_type('task')
    R['/'] = lambda self: self.get_search_term()
    R['n'] = lambda self: self.search_motion()
    R['N'] = lambda self: self.search_motion(back=True)
    R['*'] = lambda self: self.get_search_group()
    R['#'] = lambda self: self.get_search_group(back=True)
    R['0'] = lambda self: setattr(self, 'chosen_event_idx', len(self.appointments) + len(self.tasks))
    R['$'] = lambda self: setattr(self, 'chosen_event_idx', len(self.appointments) + len(self.tasks) - 1)
    R['y'] = lambda self: (setattr(self, 'yank', self.chosen_event), setattr(self, 'group_yank', False))
    R['g']['g'] = lambda self: setattr(self, 'chosen_date', self.today)
    R['g']['y'] = lambda self: (setattr(self, 'yank', self.chosen_event), setattr(self, 'group_yank', True))
    R['z']['t'] = lambda self: setattr(self, 'from_date', self.chosen_date)
    R['z']['b'] = lambda self: setattr(self, 'from_date', self.chosen_date - display.NUM_DAYS + 1)
    R['z']['z'] = lambda self: setattr(self, 'from_date', self.chosen_date - display.NUM_DAYS // 2)
    R['z']['k'] = lambda self: setattr(self, 'from_date', self.from_date - 1)
    R['z']['j'] = lambda self: setattr(self, 'from_date', self.from_date + 1)
    R['z']['h'] = lambda self: setattr(self.config, 'start_hour', self.config['start_hour'] - 1)
    R['z']['l'] = lambda self: setattr(self.config, 'start_hour', self.config['start_hour'] + 1)  # TODO display needs to use the config, not its own global vars; TODO check start_hour < 12
    R['\x1b']['[']['A'] = R['z']['k']
    R['\x1b']['[']['B'] = R['z']['j']
    R['\x1b']['[']['D'] = R['z']['h']
    R['\x1b']['[']['C'] = R['z']['l']
    # MISC_COMMANDS (INTRANSITIVE)
    R[None] = lambda self: display.refresh_term_size()
    R['u'] = lambda self: self.undo()  # TODO do I really need a lambda here?
    R['\x12'] = lambda self: self.redo()
    R['?'] = lambda self: self.show_help()
    R['q'] = lambda self: self.quit()
    R['\x1b']['\x1b'] = R['q']
    R['\x03'] = lambda self: self.quit(save=False)
    R['~'] = lambda self: setattr(self.config, 'military_time', not self.config['military_time'])  # TODO display doesn't use config
    R['v'] = lambda self: self.make_backup()
    R['p'] = lambda self: self.paste()  # TODO paste relies on setting the chosen_action which is deprecated
    R['g']['p'] = lambda self: self.paste(group=True)
    R['g']['?'] = lambda self: self.rot13()
    # NEW_TYPES
    for key, event_type in zip('atc', ('appointment', 'task', 'chore')):
        # TODO this doesn't automatically choose the new event
        R[key] = lambda self, event_type=event_type: self.checkpoint_wrapper(modify.add_event, self.chosen_event, self.session, date=self.chosen_date, type=event_type, group=True)
    # MODIFY
    # color cycle
    R[';'] = lambda self: self.checkpoint_wrapper(modify.cycle_color, self.chosen_event, self.session, group=False, backwards=False)
    R[','] = lambda self: self.checkpoint_wrapper(modify.cycle_color, self.chosen_event, self.session, group=False, backwards=True)
    R['g'][';'] = lambda self: self.checkpoint_wrapper(modify.cycle_color, self.chosen_event, self.session, group=True, backwards=False)
    R['g'][','] = lambda self: self.checkpoint_wrapper(modify.cycle_color, self.chosen_event, self.session, group=True, backwards=True)
    # postpone / prepone
    R['-'] = lambda self: self.checkpoint_wrapper(modify.postpone, self.chosen_event, self.session, group=False, delta=-1)  # TODO chosen_date might not keep up with the chosen_event
    R['+'] = lambda self: self.checkpoint_wrapper(modify.postpone, self.chosen_event, self.session, group=False, delta=1)
    R['='] = R['+']
    R['g']['-'] = lambda self: self.checkpoint_wrapper(modify.postpone, self.chosen_event, self.session, group=True, delta=-1)
    R['g']['+'] = lambda self: self.checkpoint_wrapper(modify.postpone, self.chosen_event, self.session, group=True, delta=1)
    R['g']['='] = R['g']['+']
    # EDIT
    for key, field in zip('Ddct', ('date', 'description', 'code', 'time')):
        R['e'][key] = lambda self, field=field: self.checkpoint_wrapper(modify.edit_field, self.chosen_event, self.session, field=field)
        R['g'][key] = lambda self, field=field: self.checkpoint_wrapper(modify.edit_field, self.chosen_event, self.session, field=field, group=True)
        R['g']['e'][key] = R['g'][key]
    # COMMANDS (TRANSITIVE)
    for key, func in zip('xrs', (modify.kill_event, modify.repeat_event, modify.detach_event)):
        R[key] = lambda self, func=func: self.checkpoint_wrapper(func, self.chosen_event, self.session, group=False)
        R['g'][key] = lambda self, func=func: self.checkpoint_wrapper(func, self.chosen_event, self.session, group=True)
    R['g']['X'] = lambda self: self.checkpoint_wrapper(modify.kill_future_events, self.chosen_event, self.session, group=True)


    COMMANDS = {
        'm': (modify.edit_date, "Move (set date)"),
    }


    def main_loop(self):
        self.session = database.Session()
        self.config = database.ConfigDict(self.session)
        self.session.execute(text(f'SAVEPOINT SP_0'))
        with self.session:
            display.set_military(self.config['military_time'])
            display.change_start_time(self.config['start_hour'])
            node = self.ROOT
            while True:
                self.display()
                c = getch(watch_resize=True)
                if c in node:
                    node = node[c]
                    if isinstance(node, TrieNode):
                        self.message = node.message
                    else:  # the "node" is actually the function to execute
                        node(self)
                        node = self.ROOT
                else:
                    node = self.ROOT

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

    # MISCELLANEOUS COMMANDS
    def undo(self):
        if self.undo_stack:
            self.session.execute(text(f'ROLLBACK TO SP_{len(self.undo_stack) - 1}'))  # rollback to the savepoint
            self.session.expire_all()  # invalidates all cached objects, must reload them from the database
            self.chosen_event = None  # the chosen event may have been deleted, so we need to reset it to avoid errors
            self.chosen_date, idx, _, _, _ = self.undo_stack[-1]  # copy coordinates from undo stack
            self.chosen_event_idx = idx  # make sure we have the correct date before setting chosen_event_idx
            self.redo_stack.append(self.undo_stack.pop())
    def redo(self):
        if self.redo_stack:
            _, _, func, args, kwargs = self.redo_stack.pop()
            func(*args, **kwargs)  # replay
    def show_help(self):
        print(colors.ALT_SCREEN + help.help); getch(); print(colors.MAIN_SCREEN)
    def quit(self, save=True):
        if not save and questionary.confirm("Quit without saving (undo all changes)?", default=False).ask():
            self.session.rollback()
            raise KeyboardInterrupt
        self.session.commit()
        exit()
    def make_backup(self):
        # make a backup of the database
        self.session.commit()
        self.config['backup_location'] = questionary.path(message="Backup database location: ", only_directories=True,
                                                          default=self.config['backup_location']).ask()
        shutil.copy(database.DB_PATH, os.path.expanduser(self.config['backup_location']))
    def paste(self, group=False):
        if self.yank:
            self.chosen_action = 'gr' if (group or self.group_yank) else 'r'
            difference = self.chosen_date - self.yank.date
            self.param = (difference, 1)
            self.chosen_event = self.yank
    def rot13(self):
        # ROT13 encrypt the entire database (description and code)
        start_time = time.time()
        for event in self.session.query(database.Event).all():
            event.description = display.rot13(event.description or '')
            event.code = display.rot13(event.code or '')
        end_time = time.time()
        self.message = f"ROT13 took {int((end_time - start_time)*1000)}ms"

    def checkpoint_wrapper(self, func, *args, **kwargs):
        # undo record: chosen_date, chosen_event_idx, chosen_function, param (we want to know where we were before we did the action)
        undo_record = [self.chosen_date, self.chosen_event_idx, func, args, kwargs]  # TODO refactor triple
        new_kwargs = func(*args, **kwargs)
        undo_record[-1].update(new_kwargs)  # update kwargs with whatever we get back to make it run more smoothly next time.
        self.make_savepoint(undo_record)
        # we need to be able to re-run func. This requires saving the arguments to func. We also want to update kwargs with whatever we get back to make it run more smoothly next time.


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


    # MOTION METHODS
    def move_horizontal(self, back=False):
        if not self.events:
            return
        if self.chosen_event_idx:
            self.chosen_event_idx = (self.chosen_event_idx - 1) % len(self.events)
            return
        if not back:  # move right
            if self.tasks:
                self.task_idx = 0
        elif back:  # move left
            if self.appointments:
                self.appointment_idx = len(self.appointments) - 1
            elif self.chores:
                self.chore_idx = len(self.chores) - 1
    def move_month(self, back=False):
        old_date = self.chosen_date
        self.chosen_date = dateutils.add_month(self.chosen_date, back=back)
        self.from_date += (self.chosen_date - old_date)
    def cycle_event_by_type(self, event_type):
        event_list = getattr(self, event_type + 's')
        if old_idx := getattr(self, event_type + '_idx') is not None:
            setattr(self, event_type + '_idx', (old_idx + 1) % len(event_list))
        elif event_list:
            setattr(self, event_type + '_idx', 0)
    def get_search_term(self):
        self.search = questionary.text("Search: ", default=self.search).ask()
        self.matching = (database.Event.description.like(f'%{self.search}%') |
                            database.Event.code.like(f'%{self.search}%')) if self.search else None
        self.search_motion(back=False)
        self.MOTIONS.add('N')  # add N to the list of motions
    def get_search_group(self, back=False):
        if self.chosen_event and self.chosen_event.recurrence_parent:
            self.matching = (database.Event.recurrence_parent == self.chosen_event.recurrence_parent)
            self.search_motion(back=back)
            self.MOTIONS.add('N')  # add N to the list of motions

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
