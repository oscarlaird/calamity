# This is a sample Python script.
import time

import questionary
import datetime

from calamity_calendar import colors
from calamity_calendar.database import Session, Event
from calamity_calendar.validators import DateValidator, CodeValidator, TimeValidator, RepetitionValidator


def delete_event(event, session, param=None):
    # delete event
    if event.recurrence_parent is not None:
        if param if param is not None else questionary.confirm("Delete all repetitions?", default=False).ask():
            # delete all recurrence children
            session.query(Event).filter_by(recurrence_parent=event.recurrence_parent).delete()
            return True
        session.delete(event)
        return False
    else:
        session.delete(event)
        return None


def move_event(event, session, param=None):
    if param is None:
        old_date = datetime.date.fromordinal(event.date).strftime("%Y-%m-%d")
        date = questionary.text(message="Date (YYYY-MM-DD):", default=old_date, validate=DateValidator).ask()
        event.date = datetime.datetime.strptime(date, "%Y-%m-%d").toordinal()
    else:
        event.date = param
    return event.date


def edit_description(event, session, param=None):
    event.description = param if param is not None else questionary.text("Description:",
                                                                         default=event.description).ask()
    # make siblings have same description
    if event.recurrence_parent is not None:
        session.query(Event).filter_by(recurrence_parent=event.recurrence_parent).update(
            {Event.description: event.description})
    return event.description


def cycle_color(event, session, param=None):
    event.color = colors.CYCLE_DICT[event.color]
    # make siblings have same color
    if event.recurrence_parent is not None:
        session.query(Event).filter_by(recurrence_parent=event.recurrence_parent).update({Event.color: event.color})


def cycle_color_backwards(event, session, param=None):
    event.color = colors.CYCLE_DICT_BACKWORDS[event.color]
    # make siblings have same color
    if event.recurrence_parent is not None:
        session.query(Event).filter_by(recurrence_parent=event.recurrence_parent).update({Event.color: event.color})


def edit_code(event, session, param=None):
    if not event.type == "task":
        return
    event.code = param if param is not None else questionary.autocomplete("Code:", validate=CodeValidator,
                                          choices=list_codes(session), default=event.code).ask()
    # make siblings have same code
    if event.recurrence_parent is not None:
        session.query(Event).filter_by(recurrence_parent=event.recurrence_parent).update({Event.code: event.code})
    return event.code


def repeat_event(event, session, param=None):
    event.recurrence_parent = event.recurrence_parent or event.id  # if this is the first time, set the parent to self
    period, n = param if param is not None else questionary.text("How many times (period+repetitions)?",
                                 validate=RepetitionValidator,
                                 default="7+1").ask().split('+')
    for i in range(1, int(n) + 1):
        new_event = event.copy()
        new_event.date += i * int(period)
        session.add(new_event)
    session.flush()  # get the id and default values back from the database
    return (period, n)



def duplicate_event(event, session, param=None):
    repeat_event(event, session, param=(0, 1))
    # new_event = event.copy()  # will even include recurrence parent, but could be none
    # session.add(new_event)  # add to database to get id
    return None

def detach_event(event, session, param=None):
    event.recurrence_parent = None


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
