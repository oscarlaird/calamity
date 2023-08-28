import datetime
import time

from sqlalchemy import text

from calamity_calendar import display, database, modify, colors, help
from calamity_calendar.getch import getch

BACKSPACE = '\x7f'
DELETE = '\x1b[3~'
UP = '\x1b[A'
DOWN = '\x1b[B'
RIGHT = '\x1b[C'
LEFT = '\x1b[D'
CTRL_R = '\x12'

COMMANDS = {
    'x': (modify.delete_event, "Delete"),
    DELETE: (modify.delete_event, "Delete"),
    'r': (modify.repeat_event, "Repeat"),
    'y': (modify.duplicate_event, "Duplicate"),
    's': (modify.detach_event, "Separate / Detach"),
    # Edit
    'm': (modify.move_event, "Move (edit date)"),
    'd': (modify.edit_description, "Edit Description"),
    'i': (modify.edit_time, "Edit Time (appt)"),
    'o': (modify.edit_code, "Edit Code (task)"),
    ';': (modify.cycle_color, "Cycle Color"),
    ',': (modify.cycle_color_backwards, "Cycle Color Backwords"),
}
NEW_TYPES = {'a': ('appointment', "New Appointment"),
             't': ('task', "New Task"),
             'c': ('chore', "New Chore")}
MOTIONS = ('j', DOWN, 'k', UP, 'h', LEFT, 'l', RIGHT, 'w', 'b', '<', '>', '\t', ' ', '\n', '\r', 'g', 'z')

TODAY = datetime.date.today().toordinal()
from_date = TODAY

def get_index_of_event_from_id(event_id, session):
    tasks, appointments, chores = database.fetch_days_events(chosen_date, session=session)
    events = appointments + tasks + chores
    for i, event in enumerate(events):
        if event.id == event_id:
            return i

error = None
try:
    welcomed = False
    chosen_date = TODAY
    chosen_event_idx = None
    chosen_action = None
    param = None
    with database.Session() as session:
        session.execute(text(f'SAVEPOINT SP_0'))
        undo_stack = []
        redo_stack = []


        print(colors.CURSOR_OFF + colors.WRAP_OFF, colors.ALT_SCREEN, end='')  # turn off cursor and wrap, switch to alt screen

        while True:
            # DISPLAY
            print(colors.CLEAR_SCREEN)
            tasks, appointments, chores = database.fetch_days_events(chosen_date, session=session)
            events = appointments + tasks + chores
            if welcomed:  # hide the events on the first screen
                prev_type = None
                for i, event in enumerate(events):
                    if event.type != prev_type:
                        print(display.MARGIN, end='')
                        print(f"          {event.type.capitalize()}s:")
                        prev_type = event.type
                    print(display.MARGIN, end='')
                    print(f"            {chr(ord('1') + i)}) "
                          f"{colors.ANSI_COLOR_DICT[event.color]}{colors.ANSI_REVERSE if i == chosen_event_idx else ''}"
                          f"{event.description}"
                          f"{colors.ANSI_RESET}")
                print()
            elif not welcomed:
                display.welcome()
                welcomed = True


            display.display_calendar(from_date=from_date, chosen_date=chosen_date, chosen_event_idx=chosen_event_idx, session=session)
            # print(undo_stack, redo_stack)

            # GET CHARACTER
            c = getch(watch_resize=True)
            if c is None:  # terminal was resized
                display.refresh_term_size()
                continue
            elif c == 'u':
                if undo_stack:
                    chosen_date, chosen_event_idx, _, _ = undo_stack[-1]  # copy coordinates from undo stack
                    redo_stack.append(undo_stack.pop())
                    session.execute(text(f'ROLLBACK TO SP_{len(undo_stack)}'))  # rollback to the savepoint
                    session.expire_all()  # NECESSARY: invalidates all cached objects, must reload them from the database
            elif c == CTRL_R:
                if redo_stack:
                    chosen_date, chosen_event_idx, chosen_action, param = redo_stack[-1]  # replay
                    # redetermine events since redoing is the only way to change the date and the action in the same iteration
                    tasks, appointments, chores = database.fetch_days_events(chosen_date, session=session)
                    events = appointments + tasks + chores
            elif c == '?':
                # open help.txt
                print(colors.ALT_SCREEN + help.help)
                getch()
                print(colors.MAIN_SCREEN)
            elif len(c)==1 and 0 <= (index := ord(c) - ord('A')) < display.NUM_DAYS:
                chosen_date = from_date + index
                chosen_event_idx = None
            elif chosen_date and len(c)==1 and 0 <= (index := ord(c) - ord('1')) < len(events):
                chosen_event_idx = index
            elif c in COMMANDS or c in NEW_TYPES:
                chosen_action = c
            elif c in MOTIONS:
                chosen_action = None
                if c=='j' or c==DOWN:
                    if chosen_date is not None:
                        chosen_date += 1
                        from_date = max(from_date, chosen_date - display.NUM_DAYS + 1)
                elif c=='k' or c==UP:
                    if chosen_date is not None:
                        chosen_date -= 1
                        from_date = min(from_date, chosen_date)
                elif c=='h' or c==LEFT:
                    chosen_event_idx = chosen_event_idx if (chosen_event_idx is not None or not events) else len(appointments)
                    chosen_event_idx -= 1
                    chosen_event_idx %= len(events)
                elif c=='l' or c==RIGHT:
                    chosen_event_idx = chosen_event_idx if (chosen_event_idx is not None or not events) else len(appointments) - 1
                    chosen_event_idx += 1
                    chosen_event_idx %= len(events)
                elif c=='w':
                    if chosen_date is not None:
                        chosen_date += 7
                        from_date = max(from_date, chosen_date - display.NUM_DAYS + 1)
                elif c=='b':
                    if chosen_date is not None:
                        chosen_date -= 7
                        from_date = min(from_date, chosen_date)
                elif c=='<':
                    old_date = datetime.date.fromordinal(chosen_date) # set new_date to the previous month
                    new_date = old_date.replace(year = old_date.year - (old_date.month == 1), month = (old_date.month - 2) % 12 + 1, day=1) # get the number of days in this month n_days (e.g. 28 for Feb)
                    n_days = (new_date.replace(year=new_date.year + (new_date.month == 12), month=(new_date.month) % 12 + 1) - new_date).days
                    new_date = new_date.replace(day=min(old_date.day, n_days)) # try to keep the same day of the month if possible
                    difference = old_date.toordinal() - new_date.toordinal()
                    chosen_date -= difference
                    from_date -= difference
                elif c=='>':
                    old_date = datetime.date.fromordinal(chosen_date)
                    new_date = old_date.replace(year = old_date.year + (old_date.month == 12), month = (old_date.month) % 12 + 1, day=1)
                    n_days = (new_date.replace(year=new_date.year + (new_date.month == 12), month=(new_date.month) % 12 + 1) - new_date).days
                    new_date = new_date.replace(day=min(old_date.day, n_days))  # try to keep the same day of the month if possible
                    difference = new_date.toordinal() - old_date.toordinal()
                    chosen_date += difference
                    from_date += difference
                elif c=='\t':
                    # cycle thru chores
                    if not chores:
                        pass
                    elif chosen_event_idx is None or chosen_event_idx < len(appointments) + len(tasks):
                        chosen_event_idx = len(appointments) + len(tasks)
                    else:
                        residual = chosen_event_idx - len(appointments) - len(tasks)
                        residual += 1
                        residual %= len(chores)
                        chosen_event_idx = len(appointments) + len(tasks) + residual
                elif c=='\n' or c=='\r':
                    # cycle thru tasks
                    if not tasks:
                        pass
                    elif chosen_event_idx is None or not len(appointments) <= chosen_event_idx < len(appointments) + len(tasks):
                        chosen_event_idx = len(appointments)
                    else:
                        residual = chosen_event_idx - len(appointments)
                        residual += 1
                        residual %= len(tasks)
                        chosen_event_idx = len(appointments) + residual
                elif c==' ':  # cycle thru appointments
                    if not appointments:
                        pass
                    elif chosen_event_idx is None or chosen_event_idx >= len(appointments):
                        chosen_event_idx = 0
                    else:
                        chosen_event_idx += 1
                        chosen_event_idx %= len(appointments)
                elif c=='g':
                    submotion = getch()
                    if submotion == 'g':
                        if TODAY < from_date:
                            from_date = TODAY
                            chosen_date = TODAY
                        elif from_date + display.NUM_DAYS <= TODAY:
                            from_date = TODAY - display.NUM_DAYS + 1
                            chosen_date = TODAY
                        else:
                            chosen_date = TODAY
                        chosen_event_idx = None
                    else:
                        pass
                elif c=='z':
                    submotion = getch()
                    if submotion == 'z':
                        from_date = chosen_date - display.NUM_DAYS // 2
                    elif submotion == 'b':
                        from_date = chosen_date - display.NUM_DAYS + 1
                    elif submotion == 't':
                        from_date = chosen_date
                    else:
                        pass
            elif c == '\x1b\x1b' or c == 'q' or c=='\x03':  # ESC ESC or q or ctrl-c
                session.commit()
                if c=='\x03':
                    raise KeyboardInterrupt
                break  # quit
            else:
                pass

            # DETERMINE IF ANYTHING SHOULD BE DONE
            if not chosen_date or not chosen_action or ((chosen_event_idx is None or chosen_event_idx >= len(events)) and not chosen_action in NEW_TYPES):
                continue

            # DO THE THING
            triple = [chosen_date, chosen_event_idx, chosen_action, None]
            if chosen_action in NEW_TYPES:
                assert chosen_date
                new_event = database.Event(date=chosen_date, type=NEW_TYPES[chosen_action][0])
                session.add(new_event)
                session.flush()  # get the id and default values back from the database
                triple[3] = modify.add_event(new_event, session, param=param)
                chosen_event_idx = get_index_of_event_from_id(new_event.id, session)
            elif chosen_action in COMMANDS:
                assert chosen_event_idx is not None
                # save the parameters of the command in case we need to redo
                event = events[chosen_event_idx]
                triple[3] = COMMANDS[chosen_action][0](event, session=session, param=param)
            else:
                raise ValueError(f"Unknown action {chosen_action}")

            # SAVEPOINT
            # create new savepoint
            if redo_stack and triple != redo_stack.pop():
                redo_stack = []
            undo_stack.append(triple)
            session.flush()  # synchronize the database with the session before saving
            session.execute(text(f'SAVEPOINT SP_{len(undo_stack)}'))

            # reset chosen_action
            chosen_action = None  # wait to get a new action
            param = None
except BaseException as e:
    error = e
finally:
    print(colors.CURSOR_ON + colors.WRAP_ON + colors.MAIN_SCREEN, end='')  # turn on cursor and wrap, switch to main screen
    if error:
        raise error
