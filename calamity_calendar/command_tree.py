from string import ascii_uppercase, digits


from calamity_calendar import database, display



class TrieNode(dict):

    def __init__(self, message=""):
        super().__init__()
        self.message = message

# COMMAND TRIE
# PARENT NODES
R = ROOT = TrieNode("?) HELP    e) EDIT    z) VIEW    g) GROUP")
R['e'] = TrieNode("EDIT:   D) date    d) description    c) code      \n"
                  "        s) start time    f) finish time    t) time\n")
R['z'] = TrieNode("VIEW:    k) up    j) down    h) left    l) right\n"
                  "         z) center    t) top    b) bottom       \n"
                  "         0) toggle 12/24 hour    ?) toggle help \n")
R['g'] = TrieNode("GROUP:  e) EDIT   r) repeat   x) delete    X) delete future    m) move    y) yank")
R['g']['e'] = TrieNode(message=R['e'].message)
R['\x1b'] = TrieNode("ESC) quit")
R['\x1b']['['] = TrieNode()
# CAPITAL LETTERS
for c in ascii_uppercase:
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
R['z']['b'] = lambda self: setattr(self, 'from_date', self.chosen_date - display.NUM_DAYS + 1)
R['z']['z'] = lambda self: setattr(self, 'from_date', self.chosen_date - display.NUM_DAYS // 2)
R['z']['k'] = lambda self: setattr(self, 'from_date', self.from_date - 1)
R['z']['j'] = lambda self: setattr(self, 'from_date', self.from_date + 1)
R['z']['h'] = lambda self: database.config.__setitem__('start_hour', database.config['start_hour'] - 1)
R['z']['l'] = lambda self: database.config.__setitem__('start_hour', database.config['start_hour'] + 1)
R['z']['0'] = lambda self: database.config.__setitem__('military_time', not database.config['military_time'])
R['z']['?'] = lambda self: database.config.__setitem__('show_help', not database.config['show_help'])
R['\x1b']['[']['A'] = R['z']['k']
R['\x1b']['[']['B'] = R['z']['j']
R['\x1b']['[']['D'] = R['z']['h']
R['\x1b']['[']['C'] = R['z']['l']
# MISC_COMMANDS (INTRANSITIVE)
R['u'] = lambda self: self.undo()  # TODO undo/redo/undo should work
R['\x12'] = lambda self: self.redo()
R['?'] = lambda self: self.show_help()
R['q'] = lambda self: self.quit()  # TODO do I really need a lambda here?
R['\x1b']['\x1b'] = R['q']
R['\x03'] = lambda self: self.quit(save=False)
R['v'] = lambda self: self.make_backup()
R['g']['?'] = lambda self: database.config.__setitem__('ROT13', not database.config['ROT13'])
R['p'] = lambda self: self.checkpoint_wrapper(self.paste)
# NEW_TYPES
for key, event_type in zip('atc', ('appointment', 'task', 'chore')):
    R[key] = lambda self, event_type=event_type: self.checkpoint_wrapper(self.add_event, date=self.chosen_date, type=event_type)
# MODIFY
# toggle type
# EDIT
for key, field in zip('Ddcsf', ('date', 'description', 'code', 'start_time', 'end_time')):
    R['e'][key] = lambda self, field=field: self.checkpoint_wrapper(self.edit_field, field=field)
    R['g'][key] = lambda self, field=field: self.checkpoint_wrapper(self.edit_field, field=field, group=True)
    R['g']['e'][key] = R['g'][key]
R['e']['t'] = lambda self: self.checkpoint_wrapper(self.edit_time)
R['g']['t'] = lambda self: self.checkpoint_wrapper(self.edit_time, group=True)
R['g']['e']['t'] = R['g']['t']

# COMMANDS (TRANSITIVE)
# color cycle
cmds = {'-': 'prepone_one', '+' : 'postpone_one', '=': 'postpone_one',
        ';' : 'cycle_color_forward', ',': 'cycle_color_backward', '~': 'toggle_type',
        'r': 'repeat_event', 'x': 'kill_event', 'm': 'move_event'}
for key, func in cmds.items():
    R[key] =     lambda self, func=func, group=False: self.checkpoint_wrapper(getattr(self, func), group=group)
    R['g'][key] = lambda self, func=func, group=True: self.checkpoint_wrapper(getattr(self, func), group=group)

# postpone / prepone
R['s'] = lambda self: self.checkpoint_wrapper(
    lambda: setattr(self.chosen_event, 'recurrence_parent', database.Event.random_group_id()))
R['g']['X'] = lambda self: self.checkpoint_wrapper(self.kill_future_events)