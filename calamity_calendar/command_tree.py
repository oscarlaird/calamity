from string import ascii_uppercase, digits

from calamity_calendar import database, display


class TrieNode(dict):

    def __init__(self, message=""):
        super().__init__()
        self.message = message


# COMMAND TRIE
# PARENT NODES
R = ROOT = TrieNode("?) HELP     e) EDIT     z) VIEW     g) GROUP")
R['e'] = TrieNode("   EDIT:    D) date     c) code     d) description      \n"
                  "            t) time     s) start    f) finish           \n")
R['z'] = TrieNode("   VIEW:    l) right    h) left     j) down     k) up   \n"
                  "            z) center   b) bottom   t) top              \n")
R['g'] = TrieNode("   GROUP:   e) EDIT     r) repeat   x) delete           \n"
                  "            m) move     y) yank     X) delete future    \n")
R['g']['e'] = TrieNode(message=R['e'].message)
R['\x1b'] = TrieNode(message=R.message)
R['\x1b']['['] = TrieNode()
# CAPITAL LETTERS
for c in ascii_uppercase + '[\\]^_`':
    R[c] = lambda self, c=c: setattr(self, 'chosen_date', self.from_date + ord(c) - ord('A'))
# NUMBERS
for c in digits[1:]:
    R[c] = lambda self, c=c: setattr(self, 'chosen_event_idx', int(c) - 1)
# MOTIONS
R['j'] = lambda self: setattr(self, 'chosen_date', self.chosen_date + 1)
R['k'] = lambda self: setattr(self, 'chosen_date', self.chosen_date - 1)
R['l'] = lambda self: self.move_horizontal()
R['h'] = lambda self: self.move_horizontal(back=True)
R['w'] = lambda self: setattr(self, 'chosen_date', self.chosen_date + 7)
R['b'] = lambda self: setattr(self, 'chosen_date', self.chosen_date - 7)
R['<'] = lambda self: self.move_month(back=True)
R['>'] = lambda self: self.move_month()
R['\t'] = lambda self: self.cycle_event_by_type('chore')
R[' '] = lambda self: self.cycle_event_by_type('appointment')
R['\n'] = lambda self: self.cycle_event_by_type('task')
R['\r'] = lambda self: self.cycle_event_by_type('task')
R['/'] = lambda self: self.get_search_term()
R['n'] = lambda self: self.search_motion()
R['N'] = lambda self: self.search_motion(back=True)
R['*'] = lambda self: self.get_search_group()
R['#'] = lambda self: self.get_search_group(back=True)
R['0'] = lambda self: setattr(self, 'chosen_event_idx',
                              (len(self.appointments) + len(self.tasks)) if self.chores else 0)
R['$'] = lambda self: setattr(self, 'chosen_event_idx', len(self.appointments) + len(self.tasks) - 1)
R['y'] = lambda self: self.yank()
R['g']['g'] = lambda self: setattr(self, 'chosen_date', self.today)
R['g']['y'] = lambda self: self.yank(group=True)
R['z']['t'] = lambda self: setattr(self, 'from_date', self.chosen_date)
R['z']['b'] = lambda self: setattr(self, 'from_date', self.chosen_date - display.get_num_days() + 1)
R['z']['z'] = lambda self: setattr(self, 'from_date', self.chosen_date - display.get_num_days() // 2)
R['z']['k'] = lambda self: setattr(self, 'from_date', self.from_date - 1)
R['z']['j'] = lambda self: setattr(self, 'from_date', self.from_date + 1)
# display config
R['z']['h'] = lambda self: database.config.__setitem__('start_hour', database.config['start_hour'] - 1)
R['z']['l'] = lambda self: database.config.__setitem__('start_hour', database.config['start_hour'] + 1)
R['z']['0'] = lambda self: database.config.__setitem__('military_time', not database.config['military_time'])
R['z']['?'] = lambda self: database.config.__setitem__('show_help', not database.config['show_help'])
R['g']['?'] = lambda self: database.config.__setitem__('ROT13', not database.config['ROT13'])
R['\x1b']['[']['A'] = R['z']['k']
R['\x1b']['[']['B'] = R['z']['j']
R['\x1b']['[']['D'] = R['z']['h']
R['\x1b']['[']['C'] = R['z']['l']

# MISC_COMMANDS
# HELP_TEXT
R['?'] = lambda self: self.show_help()
# quit
R['q'] = lambda self: self.quit()  # TODO do I really need a lambda here?
R['\x1b']['\x1b'] = R['q']
R['\x03'] = lambda self: self.quit(ask=True)
# backup
R['v'] = lambda self: self.make_backup()
# undo/redo
R['u'] = lambda self: self.undo()  # TODO undo/redo/undo should work
R['\x12'] = lambda self: self.redo()
R['.'] = lambda self: self.repeat()

# NEW_TYPES
for key, event_type in zip('atc', ('appointment', 'task', 'chore')):
    R[key] = lambda self, event_type=event_type: self.checkpoint_wrapper(self.add_event, type=event_type)
# COMMANDS (TRANSITIVE)
cmds = {'-': 'prepone_one', '+': 'postpone_one', '=': 'postpone_one',
        ';': 'cycle_color_forward', ',': 'cycle_color_backward', '~': 'toggle_type',
        'r': 'repeat_event', 'x': 'kill_event', 'm': 'move_event',
        'p': 'paste', 's': 'separate'}
for key, func in cmds.items():
    R[key] = lambda self, func=func, group=False: self.checkpoint_wrapper(getattr(self, func), group=group)
    R['g'][key] = lambda self, func=func, group=True: self.checkpoint_wrapper(getattr(self, func), group=group)
# edit
for key, field in zip('Ddcsf', ('date', 'description', 'code', 'start_time', 'end_time')):
    R['e'][key] = lambda self, field=field: self.checkpoint_wrapper(self.edit_field, field=field)
    R['g'][key] = lambda self, field=field: self.checkpoint_wrapper(self.edit_field, field=field, group=True)
    R['g']['e'][key] = R['g'][key]
R['e']['t'] = lambda self: self.checkpoint_wrapper(self.edit_time)
R['g']['t'] = lambda self: self.checkpoint_wrapper(self.edit_time, group=True)
R['g']['e']['t'] = R['g']['t']
# alias edit description
R['d'] = R['e']['d']
# delete future events
R['g']['X'] = lambda self: self.checkpoint_wrapper(self.kill_future_events)
