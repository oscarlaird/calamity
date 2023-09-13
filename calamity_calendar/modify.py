# This is a sample Python script.
import time
import os

import questionary
import datetime

from calamity_calendar import colors
from calamity_calendar.database import Session, Event
from calamity_calendar.validators import DateValidator, CodeValidator, TimeValidator, RepetitionValidator
from calamity_calendar.getch import getch


def random_group_id():
    # return a random 4 byte integer
    return int.from_bytes(os.urandom(4), byteorder='big')


def has_repetition(event, session):
    return event.recurrence_parent is not None and (
        session.query(Event).filter(Event.recurrence_parent == event.recurrence_parent).filter(
            Event.id != event.id).first()) is not None


def kill_event(event, session, param=None, group=False):
    if group:
        session.query(Event).filter_by(recurrence_parent=event.recurrence_parent).delete()
    else:
        session.delete(event)

def kill_future_events(event, session, param=None, group=False):
    session.query(Event).filter_by(recurrence_parent=event.recurrence_parent).filter(Event.date >= event.date).delete()


def postpone(event, session, group=False, delta=1):
    if group and event.recurrence_parent is not None:
        # shift siblings
        session.query(Event).filter_by(recurrence_parent=event.recurrence_parent).update(
            {Event.date: Event.date + delta})
    else:
        event.date += delta



def edit_field(event, session, param=None, group=False, field=None):
    # TODO: make this work for start and end time
    validator = CodeValidator if field == 'code' else DateValidator if field == 'date' else None
    default = event.code if field == 'code' else datetime.date.fromordinal(event.date).strftime("%Y-%m-%d") if field == 'date' else event.description if field == 'description' else ''
    message = field.capitalize() + ':'
    input = questionary.text(message=message, validate=validator, default=default).ask()
    if field == 'date':
        input = datetime.datetime.strptime(input, "%Y-%m-%d").toordinal()
    setattr(event, field, input)
    # make siblings have same field
    if group and event.recurrence_parent is not None:
        session.query(Event).filter_by(recurrence_parent=event.recurrence_parent).update({field: getattr(event, field)})


def cycle_color(event, session, group=False, backwards=False):
    event.color = colors.CYCLE_DICT[event.color] if not backwards else colors.CYCLE_DICT_BACKWORDS[event.color]
    if group and event.recurrence_parent is not None:
        session.query(Event).filter_by(recurrence_parent=event.recurrence_parent).update({Event.color: event.color})



def repeat_event(event, session, param=None, group=False):
    event.recurrence_parent = event.recurrence_parent or random_group_id()  # if no group id, make one
    period, n = param if param is not None else questionary.text("How many times (period+repetitions)?",
                                                                 validate=RepetitionValidator,
                                                                 default="7+1").ask().split('+')
    siblings = [event] if not group else session.query(Event).filter_by(recurrence_parent=event.recurrence_parent).all()
    # for each sibling in the recurrence group, create n new events with period days in between
    for sib in siblings:
        for i in range(1, int(n) + 1):
            new_event = sib.copy()
            new_event.date += i * int(period)
            session.add(new_event)
    session.flush()  # get the id and default values back from the database
    return (period, n)


def detach_event(event, session, param=None, group=None):
    event.recurrence_parent = random_group_id()


def edit_time(event, session, param=None):
    if event.type != "appointment":
        return
    # get start time
    if param is None:
        old_start_time = '' if event.start_time is None else f'{event.start_time // 60:0>2}{event.start_time % 60:0>2}'
        start_time = questionary.text("Start time (HHMM):", validate=TimeValidator, default=old_start_time).ask()
        event.start_time = datetime.datetime.strptime(start_time, "%H%M").hour * 60 + datetime.datetime.strptime(
            start_time, "%H%M").minute
        # get end time
        old_end_time = '' if event.end_time is None else f'{event.end_time // 60:0>2}{event.end_time % 60:0>2}'
        end_time = questionary.text("End time (HHMM):", validate=TimeValidator, default=old_end_time).ask()
        event.end_time = datetime.datetime.strptime(end_time, "%H%M").hour * 60 + datetime.datetime.strptime(
            end_time, "%H%M").minute
    else:
        event.start_time, event.end_time = param
    # make siblings have same time
    if event.recurrence_parent is not None:
        session.query(Event).filter_by(recurrence_parent=event.recurrence_parent).update(
            {Event.start_time: event.start_time, Event.end_time: event.end_time})
    return (event.start_time, event.end_time)


def add_event(event, session, date=None, description=None, color=None, recurrence_parent=None, type=None, start_time=None, end_time=None, code=None):
    new_event = Event(date=date, description=description, color=color, recurrence_parent=recurrence_parent, type=type, start_time=start_time, end_time=end_time, code=code)
    session.add(new_event)
    session.flush()  # get the id of the new event
    if event.type == "task" and code is None:
        edit_field(event, session, field='code')
    elif event.type == "appointment" and (start_time is None or end_time is None):
        edit_time(event, session)
    return {'date': new_event.date, 'description': new_event.description, 'color': new_event.color, 'recurrence_parent': new_event.recurrence_parent, 'type': new_event.type, 'start_time': new_event.start_time, 'end_time': new_event.end_time, 'code': new_event.code}
