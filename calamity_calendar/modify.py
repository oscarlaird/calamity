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


def edit_date(event, session, param=None, group=False):
    if group:
        raise NotImplementedError
    if param is None:
        old_date = datetime.date.fromordinal(event.date).strftime("%Y-%m-%d")
        date = questionary.text(message="Date (YYYY-MM-DD):", default=old_date, validate=DateValidator).ask()
        event.date = datetime.datetime.strptime(date, "%Y-%m-%d").toordinal()
    else:
        event.date = param
    return event.date


def postpone(event, session, param=1, group=False):
    if group and event.recurrence_parent is not None:
        # shift siblings
        session.query(Event).filter_by(recurrence_parent=event.recurrence_parent).update(
            {Event.date: Event.date + param})
    else:
        event.date += param
    return param


postpone_day = lambda event, session, param=None, group=False: postpone(event, session, param=1, group=group)
prepone_day = lambda event, session, param=None, group=False: postpone(event, session, param=-1, group=group)


def edit_description(event, session, param=None, group=False):
    old_description = event.description
    event.description = param if param is not None else questionary.text("Description:",
                                                                         default=event.description).ask()
    # make siblings have same description
    if event.recurrence_parent is not None:
        session.query(Event).filter_by(recurrence_parent=event.recurrence_parent).update(
            {Event.description: event.description})
    return event.description


def cycle_color(event, session, param=None, group=False, backwards=False):
    event.color = colors.CYCLE_DICT[event.color] if not backwards else colors.CYCLE_DICT_BACKWORDS[event.color]
    if group and event.recurrence_parent is not None:
        session.query(Event).filter_by(recurrence_parent=event.recurrence_parent).update({Event.color: event.color})


cycle_color_forwards = lambda event, session, param=None, group=False: cycle_color(event, session, param=param,
                                                                                   group=group, backwards=False)
cycle_color_backwards = lambda event, session, param=None, group=False: cycle_color(event, session, param=param,
                                                                                    group=group, backwards=True)


def edit_code(event, session, param=None):
    if not event.type == "task":
        return
    event.code = param if param is not None else questionary.text("Code:", validate=CodeValidator,
                                                                  default=event.code).ask()
    # make siblings have same code
    if event.recurrence_parent is not None:
        session.query(Event).filter_by(recurrence_parent=event.recurrence_parent).update({Event.code: event.code})
    return event.code


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


def add_event(event, session, param=None):
    if param is None:
        param = {}
    for key, value in param.items():
        if key != 'id':
            setattr(event, key, value)
    if event.type == "task":
        edit_code(event, session, param=param.get('code'))
    elif event.type == "appointment":
        interval = (param.get('start_time'), param.get('end_time'))
        interval = None if (interval[0] is None or interval[1] is None) else interval  # if either is None, set to None
        edit_time(event, session, param=interval)
    edit_description(event, session, param=param.get('description'))
    return event.to_dict()


def list_codes(session):
    # get all unique codes not null
    all_codes = session.query(Event.code).filter(Event.code != None).distinct().all()
    all_codes = [code[0] for code in all_codes]
    return all_codes
