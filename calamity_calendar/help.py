HELP_TEXT = """\
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                           HELP                                                      │
├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                     │
│ Principles:                                                                                         │
│   • Three kinds of events: appointments, tasks, and chores.                                         │
│       ○ Appointments: start time and end time.                                                      │
│       ○ Tasks: have a deadline (e.g. homework).                                                     │
│       ○ Chores: performed on the day they're scheduled (e.g. hygiene)                               │
│                                                                                                     │
│   • Selection:                                                                                      │
│       ○ Coordinate system: Day (A-Z), Event (1-9).                                                  │
│       ○ Vim motions (e.g. j, k, h, l) to navigate.                                                  │
│                                                                                                     │
│   • Repetitions (Groups):                                                                           │
│       ○ 'r': Create GROUP. E.g. r followed by 7+13 creates 13 weekly repetitions.                   │
│       ○ y/p: Yank & paste a repetition or event.                                                    │
│                                                                                                     │
│   • Group Prefix:                                                                                   │
│       ○ Prefix 'g': Applies edit command to the entire repetition group (e.g. g+, gx, ged).         │
│                                                                                                     │
├─────────────────────────────────────── New Event Types ─────────────────────────────────────────────┤
│                                                                                                     │
│      a) APPOINTMENT                      c) CHORE                               t) TASK             │
│                                                                                                     │
├──────── Selection ────────┬───────────── Edit Commands ─────────────┬──────────── View ─────────────┤
│ A-Z) Day                  │   eD) Edit date                         │  zk) Up                       │
│ 1-9) Event                │   ed) Edit description                  │  zj) Down                     │
│ j) Down                   │   ec) Edit code (task)                  │  zh) Left                     │
│ k) Up                     │   es) Edit start time (appointment)     │  zl) Right                    │
│ l) Right (Event)          │   ef) Edit finish time (appointment)    │  zz) Center                   │
│ h) Left (Event)           │   et) Edit time (appointment)           │  zt) Top                      │
│ <) Previous month         │   ;) Cycle color forwards               │  zb) Bottom                   │
│ >) Next month             │   ,) Cycle color backwards              │  z0) Toggle 12/24 hour        │
│ b) Previous week          │   +) Postpone one day                   │  z?) Toggle help visibility   │
│ w) Next week              │   -) Prepone one day                    │  g!) Toggle ROT13 encryption  │
│ TAB) Next chore           │   x) Delete event                       │                               │
│ SPC) Next appointment     │   r) Repeat event                       ├─────────── Undo ──────────────┤
│ RET) Next task            │   m) Move event                         │  u) Undo                      │
│ gg) Jump to today         │   ~) Toggle chore / task                │  CTRL-R) Redo                 │
│                           │   gX) Kill future repetitions           │  .) Repeat last action        │
├───────────────────────────┴─────────────────────────────────────────┴───────────────────────────────┤
│                                                                                                     │
│      ANY EDIT COMMAND CAN BE GIVEN THE PREFIX [g] TO APPLY TO THE ENTIRE REPETITION GROUP           │
│                                                                                                     │
├─────────────────── Search ────────────────────┬────────────────── Miscellaneous ────────────────────┤
│ /) Search                                     │  y) Yank event (gy to yank group)                   │
│ n) Next match                                 │  p) Paste yanked event/group                        │
│ N) Previous match                             │  s) Separate from repetition group                  │
│ *) Next repetition                            │  v) Backup calendar                                 │
│ #) Previous repetition                        │  q) Quit                                            │
└───────────────────────────────────────────────┴─────────────────────────────────────────────────────┘
"""