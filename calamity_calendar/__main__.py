import shutil
import os
import types
import string
import datetime
import signal

import questionary
import sqlalchemy

from calamity_calendar import display, database, colors, help, dateutils, command_tree, pager
from calamity_calendar.validators import DateValidator, CodeValidator, TimeValidator, RepetitionValidator
from calamity_calendar.database import Event
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
        self.yank_list = []
        self.yank_date = self.today

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
        # fix the window
        if self.from_date + display.get_num_days() <= self.chosen_date:
            self.from_date = self.chosen_date - display.get_num_days() + 1
        elif self.chosen_date < self.from_date:
            self.from_date = self.chosen_date
        # set the chosen date and re-fetch the list of events
        self._chosen_date = date
        self.appointments, self.tasks, self.chores = database.fetch_events(self.chosen_date, session=self.session)
        self.events = self.appointments + self.tasks + self.chores
        # try to keep the same chore_idx/appt_idx/task_idx if possible
        if self.chosen_event and self.chosen_event.date != date:
            if old_type == 'chore':
                self.chore_idx = old_chore_idx
            elif old_type == 'task':
                self.task_idx = old_task_idx
            elif old_type == 'appointment':
                self.chosen_event = None
                for event in self.appointments:
                    # set if we start before or during the event (i.e. start <= end)
                    # if still None, set
                    if event.start_time < old_appt_end:
                        self.chosen_event = event
                    elif self.chosen_event is None:
                        self.chosen_event = event
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
        self.chosen_event_idx = len(self.appointments) + idx if idx < len(self.tasks) else (
                len(self.appointments) + len(self.tasks) - 1) if self.tasks else None

    @property
    def appointment_idx(self):
        if not self.chosen_event or self.chosen_event.type != 'appointment':
            return None
        return self.chosen_event_idx

    @appointment_idx.setter
    def appointment_idx(self, idx):
        self.chosen_event_idx = idx if idx < len(self.appointments) else len(
            self.appointments) - 1 if self.appointments else None

    @property
    def chore_idx(self):
        if not self.chosen_event or self.chosen_event.type != 'chore':
            return None
        return self.chosen_event_idx - len(self.appointments) - len(self.tasks)

    @chore_idx.setter
    def chore_idx(self, idx):
        zero = len(self.appointments) + len(self.tasks)
        self.chosen_event_idx = zero + idx if idx < len(self.chores) else (
                zero + len(self.chores) - 1) if self.chores else None

    def idx_of(self, event):
        # get the index of event in the list of events
        for i, e in enumerate(self.events):
            if e.id == event.id:
                return i
        raise RuntimeError('Event not in events')

    def choose_event(self, event):
        self.chosen_event = event

    def main_loop(self):
        self.session = database.Session()
        self.session.execute(sqlalchemy.text(f'SAVEPOINT SP_0'))
        node = command_tree.ROOT
        while True:
            # display
            if isinstance(node, command_tree.TrieNode) and database.config['show_help']:
                self.message = node.message
            self.display()
            # get the next character and move to the corresponding node
            # TODO terminal resized or refreshed from another instance of calamity
            c = getch()
            if c not in node:
                node = command_tree.ROOT
            if c in node:
                node = node[c]
                if isinstance(node, types.FunctionType):
                    node(self)
                    node = command_tree.ROOT

    def display(self):
        # refresh data
        self.chosen_event = self.chosen_event  # follow event to a new date
        self.chosen_date = self.chosen_date  # update list of events on that date
        # display
        display.show_all(self)
        self.message = ''

    def redraw(self, signum=None, frame=None):
        display.show_all(self)

    # MISCELLANEOUS COMMANDS
    def show_help(self):
        pager.pager(help.HELP_TEXT, center=True)

    def quit(self, save=True, ask=False):
        if not save or (ask and questionary.confirm("Quit without saving (undo all changes)?", default=False).ask()):
            self.session.rollback()
            database.config.session.rollback()
            print("Changes discarded.")
        self.session.commit()
        database.config.commit()
        print(colors.CLEAR_TO_END + colors.CURSOR_ON + colors.WRAP_ON + colors.RESET, end='', flush=True)
        exit()

    # quit on signal
    def sig_quit(self, signum, frame):
        self.quit()

    def sig_quit_without_saving(self, signum, frame):
        self.quit(save=False)

    def make_backup(self):
        # make a backup of the database
        self.session.commit()
        database.config['backup_location'] = questionary.path(message="Backup database location: ",
                                                              only_directories=True,
                                                              default=database.config['backup_location']).ask()
        shutil.copy(database.DB_PATH, os.path.expanduser(database.config['backup_location']))

    def yank(self, group=False):
        if not self.chosen_event:
            return
        self.yank_date = self.chosen_date
        yank_list = [self.chosen_event]
        if group:
            yank_list = self.session.query(database.Event).filter(
                database.Event.recurrence_parent == self.chosen_event.recurrence_parent)
        self.yank_list = [event.to_dict() for event in yank_list]

    def paste(self, group=None):
        # self.yank is a list of events serialized as dictionaries
        delta = self.chosen_date - self.yank_date
        for event_dict in self.yank_list:
            new_dict = event_dict.copy()
            del new_dict['id']  # don't want to copy the old event's id
            new_dict['date'] += delta
            new_event = database.Event(**new_dict)
            self.session.add(new_event)  # create the new event and add it to the session
            if new_event.date == self.chosen_date:
                self.chosen_event = new_event
        self.session.flush()  # get the ids of the new events back from the database

    def separate(self, group=None):
        if self.chosen_event is None:
            return
        self.chosen_event.recurrence_parent = database.Event.random_group_id()

    # UNDO/REDO HISTORY
    def undo(self):
        if self.undo_stack:
            self.session.execute(
                sqlalchemy.text(f'ROLLBACK TO SP_{len(self.undo_stack) - 1}'))  # rollback to the savepoint
            self.session.expire_all()  # invalidates all cached objects, must reload them from the database
            self.chosen_event = None  # the chosen event may have been deleted, so we need to reset it to avoid errors
            self.chosen_date, idx, _, _, _ = self.undo_stack[-1]  # copy coordinates from undo stack
            self.chosen_event_idx = idx  # make sure we have the correct date before setting chosen_event_idx
            self.redo_stack.append(self.undo_stack.pop())

    def redo(self):
        if self.redo_stack:
            _, _, func, args, kwargs = self.redo_stack.pop()
            func(*args, **kwargs)  # replay

    def repeat(self):
        last_action = self.redo_stack[0] if self.redo_stack else self.undo_stack[-1] if self.undo_stack else None
        if not last_action:
            return
        _, _, func, args, kwargs = last_action
        self.checkpoint_wrapper(func, *args, **kwargs)  # replay the last action (checkpointing)

    def checkpoint_wrapper(self, func, *args, **kwargs):
        # undo record: chosen_date, chosen_event_idx, chosen_function, param (we want to know where we were before we did the action)
        # undo record:
        # - chosen_date
        # - chosen_event_idx   Where were we before we did the action?
        # - func
        # - args
        # - kwargs             What did we do? With what arguments?
        # to repeat an action using (.) we need to use the new chosen_event/date. However, these can't be retrieved from args.
        undo_record = [self.chosen_date, self.chosen_event_idx, func, args, kwargs]
        new_kwargs = func(*args, **kwargs)
        if new_kwargs is not None:
            assert isinstance(new_kwargs,
                              dict), "checkpoint_wrapper must wrap a function which returns Union[None, dict]"
            undo_record[-1].update(
                new_kwargs)  # update kwargs with whatever we get back to make it run more smoothly next time.
        self.make_savepoint(undo_record)
        # we need to be able to re-run func. This requires saving the arguments to func. We also want to update kwargs with whatever we get back to make it run more smoothly next time.

    def make_savepoint(self, undo_record):
        # SAVEPOINT
        # create new savepoint
        if self.redo_stack and undo_record != self.redo_stack.pop():
            self.redo_stack = []
        self.undo_stack.append(undo_record)
        self.session.flush()  # send changes to the database before making the savepoint
        self.session.execute(sqlalchemy.text(f'SAVEPOINT SP_{len(self.undo_stack)}'))

    # MOTION METHODS
    def move_horizontal(self, back=False):
        if not self.events:
            return
        if self.chosen_event_idx is not None:
            self.chosen_event_idx = (self.chosen_event_idx + (-1 if back else 1)) % len(self.events)
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
        if (old_idx := getattr(self, event_type + '_idx')) is not None:
            setattr(self, event_type + '_idx', (old_idx + 1) % len(event_list))
        elif event_list:
            setattr(self, event_type + '_idx', 0)

    def get_search_term(self):
        search = questionary.text("Search: ").ask()
        self.matching = (database.Event.description.like(f'%{search}%') |
                         database.Event.code.like(f'%{search}%')) if search else None
        self.search_motion()

    def get_search_group(self, back=False):
        if self.chosen_event and self.chosen_event.recurrence_parent:
            self.matching = (database.Event.recurrence_parent == self.chosen_event.recurrence_parent)
            self.search_motion(back=back)

    def search_motion(self, back=False):
        # back is True if we are searching backwards
        # e.g. matching = database.Event.description.like(f'%{self.search}%')
        # e.g. matching = database.Event.recurrence_parent == self.chosen_event.recurrence_parent
        # check that there is a search to do
        if self.matching is None:
            return
        # sqlalchemy objects
        is_today = database.Event.date == self.chosen_date
        is_chosen = (database.Event.id == self.chosen_event.id) if self.chosen_event else sqlalchemy.sql.false()
        order_by = database.Event.date % self.chosen_date
        order_by = order_by.desc() if back else order_by
        # search for the next occurrence on the same day
        todays_matches = self.session.query(database.Event).filter(self.matching & is_today & ~is_chosen).all()
        for event in self.events[
                     self.chosen_event_idx::(-1 if back else 1)]:  # search backwards if we are going backwards
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

    # MODIFY
    def kill_event(self, group=False):
        old_type = self.chosen_event.type
        old_type_idx = getattr(self, old_type + '_idx')
        if self.chosen_event is None:
            return
        self.yank(group=group)
        if group:
            self.session.query(Event).filter_by(recurrence_parent=self.chosen_event.recurrence_parent).delete()
        else:
            self.session.delete(self.chosen_event)
        self.chosen_date = self.chosen_date  # update events
        setattr(self, old_type + '_idx', old_type_idx)

    def kill_future_events(self):
        if self.chosen_event is None:
            return
        self.session.query(Event).filter_by(recurrence_parent=self.chosen_event.recurrence_parent).filter(
            Event.date >= self.chosen_event.date).delete()

    def postpone(self, group=False, delta=1):
        if self.chosen_event is None:
            return
        if group and self.chosen_event.recurrence_parent is not None:
            # shift siblings
            self.session.query(Event).filter_by(recurrence_parent=self.chosen_event.recurrence_parent).update(
                {Event.date: Event.date + delta})
        else:
            self.chosen_event.date += delta

    def postpone_one(self, group=False):
        self.postpone(group=group, delta=1)

    def prepone_one(self, group=False):
        self.postpone(group=group, delta=-1)

    def edit_field(self, group=False, field=None, new_value=None):
        if self.chosen_event is None:
            return
        if new_value is None:
            # validator for field
            validators = {'code': CodeValidator, 'date': DateValidator,
                          'start_time': TimeValidator, 'end_time': TimeValidator}
            validator = validators.get(field, None)
            # default string for the field
            default = getattr(self.chosen_event, field)
            if field == 'date':
                default = datetime.date.fromordinal(default).strftime("%Y-%m-%d")
            if field in ('start_time', 'end_time'):
                default = '' if default is None else f'{default // 60:0>2}{default % 60:0>2}'
            # message for the field
            message = field.replace('_', ' ').title() + ': '
            new_value = questionary.text(message=message, validate=validator, default=default).ask()
            # casting
            if field == 'date':
                new_value = datetime.datetime.strptime(new_value, "%Y-%m-%d").toordinal()
            if field in ('start_time', 'end_time'):
                time = datetime.datetime.strptime(new_value, "%H%M")
                hour, minute = time.hour, time.minute
                new_value = hour * 60 + minute
        # set the field
        if group and self.chosen_event.recurrence_parent is not None:
            self.session.query(Event).filter_by(recurrence_parent=self.chosen_event.recurrence_parent).update(
                {field: new_value})
        else:
            setattr(self.chosen_event, field, new_value)
        # return the new value
        return {'new_value': new_value}

    def cycle_color(self, group=False, backwards=False):
        if self.chosen_event is None:
            return
        old_color = self.chosen_event.color
        new_color = colors.CYCLE_DICT[old_color] if not backwards else colors.CYCLE_DICT_BACKWARDS[old_color]
        self.chosen_event.color = new_color
        database.config['color'] = new_color
        if group and self.chosen_event.recurrence_parent is not None:
            self.session.query(Event).filter_by(recurrence_parent=self.chosen_event.recurrence_parent).update(
                {Event.color: new_color})

    def cycle_color_forward(self, group=False):
        self.cycle_color(group=group, backwards=False)

    def cycle_color_backward(self, group=False):
        self.cycle_color(group=group, backwards=True)

    def toggle_type(self, group=False):
        if self.chosen_event is None or self.chosen_event.type not in ('task', 'chore'):
            return
        self.chosen_event.type = 'chore' if self.chosen_event.type == 'task' else 'task'
        if group and self.chosen_event.recurrence_parent is not None:
            self.session.query(Event).filter_by(recurrence_parent=self.chosen_event.recurrence_parent).update(
                {Event.type: self.chosen_event.type})

    def repeat_event(self, period=None, n_repetitions=None, group=False):
        if self.chosen_event is None:
            return
        if period is None or n_repetitions is None:
            period, n_repetitions = questionary.text("How many times (period+repetitions)?",
                                                     validate=RepetitionValidator, default="7+1").ask().split('+')
            period, n_repetitions = int(period), int(n_repetitions)
        siblings = [self.chosen_event] if not group else self.session.query(Event).filter_by(
            recurrence_parent=self.chosen_event.recurrence_parent).all()
        # for each sibling in the recurrence group, create n new events with period days in between
        for sib in siblings:
            for i in range(1, n_repetitions + 1):
                new_event = sib.copy()
                new_event.date += i * period
                self.session.add(new_event)
        self.session.flush()  # get the id and default values back from the database
        return {'period': period, 'n_repetitions': n_repetitions}

    def edit_time(self, start_time=None, end_time=None, group=False):
        if self.chosen_event is None or self.chosen_event.type != 'appointment':
            return
        start_time = self.edit_field(field='start_time', new_value=start_time, group=group)['new_value']
        end_time = self.edit_field(field='end_time', new_value=end_time, group=group)['new_value']
        return {'start_time': start_time, 'end_time': end_time}

    def add_event(self, date=None, description=None, color=None, recurrence_parent=None, type=None, start_time=None,
                  end_time=None, code=None):
        # TODO use an event dict so you aren't writing out column names
        new_event = Event(date=(date or self.chosen_date), description=description, color=color,
                          recurrence_parent=recurrence_parent,
                          type=type, start_time=start_time, end_time=end_time, code=code)
        self.session.add(new_event)
        self.session.flush()  # get the id of the new event
        self.chosen_event = new_event
        if type == "task" and code is None:
            self.edit_field(field='code')
        elif type == "appointment" and (start_time is None or end_time is None):
            self.edit_time()
        if description is None:
            self.edit_field(field='description')
        return {'description': new_event.description, 'start_time': new_event.start_time,
                'end_time': new_event.end_time, 'code': new_event.code,
                'recurrence_parent': new_event.recurrence_parent, 'color': new_event.color}

    def get_move_date(self):
        help_text = ("[A-Z] move to a date by capital letter     A) move to the first date in view",
                     "[0-9] move to a two digit date            14) move to the 14th of the month ",
                     "+/-   move by day/week/month              2w) move forward two weeks        ",
                     "                                         -1m) move back one month           ")
        for line in help_text:
            print(line.center(display.get_term_width()), end='' if line == help_text[-1] else '\n', flush=True)
        c1 = getch()
        english_delta, direction, n = None, 1, 1
        # date by capital letter
        if c1 in string.ascii_uppercase + '[\\]^_':
            return self.from_date + ord(c1) - ord('A')
        # two digit date
        elif c1 in string.digits:
            c2 = getch()
            if c2.isdigit():
                new_day = int(c1 + c2)
                for date in range(self.from_date, self.from_date + display.get_num_days()):
                    if datetime.date.fromordinal(date).day == new_day:
                        return date
            elif c2 in 'dwm':
                n = int(c1)
                english_delta = c2
        # +/-
        elif c1 in '+-':
            direction = 1 if c1 == '+' else -1
            first_digit = True
            while True:
                c = getch()
                if c.isdigit():
                    if first_digit:
                        n = 0
                        first_digit = False
                    n = 10 * n + int(c)
                elif c in 'dwm':
                    english_delta = c
                    break
                else:
                    return None  # invalid input
        # d/w/m
        elif c1 in 'dwm':
            english_delta = c1
        # get the target
        if english_delta is not None:
            if english_delta == 'd':
                return self.chosen_date + n * direction
            elif english_delta == 'w':
                return self.chosen_date + 7 * n * direction
            elif english_delta == 'm':
                new_date = self.chosen_date
                for _ in range(n):
                    new_date = dateutils.add_month(new_date, back=(direction == -1))
                return new_date

    def move_event(self, target=None, fail=False, group=False):
        if self.chosen_event is None:
            return
        if fail:
            return
        # get the target
        if target is None:
            target = self.get_move_date()
            # did we get a target?
            if target is None:
                return {'fail': True}
        self.postpone(group=group, delta=target - self.chosen_event.date)
        return {'target': target}


def run():
    cal = Calamity()
    # polite quit request
    signal.signal(signal.SIGTERM, cal.sig_quit)
    # listen to interrupt from another instance
    signal.signal(signal.SIGUSR1, cal.sig_quit)
    signal.signal(signal.SIGUSR2, cal.sig_quit_without_saving)
    # listen to terminal resize
    # signal.signal(signal.SIGWINCH, cal.redraw)
    cal.main_loop()


if __name__ == '__main__':
    run()
