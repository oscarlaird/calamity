import sqlalchemy
import datetime
import os
import json

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from calamity_calendar import colors

# Declare the base
Base = declarative_base()

# Declare the table of events
class Event(Base):
    __tablename__ = 'events'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    date = sqlalchemy.Column(sqlalchemy.Integer, default=datetime.date.today().toordinal())  # stored as julian date
    description = sqlalchemy.Column(sqlalchemy.String, default="")
    color = sqlalchemy.Column(sqlalchemy.String, default=None)
    recurrence_parent = sqlalchemy.Column(sqlalchemy.Integer) # id of parent event
    type = sqlalchemy.Column(sqlalchemy.String, default='task') # type of event, e.g. appointment, task, etc. # enforce not NULL
    # Appointments
    start_time = sqlalchemy.Column(sqlalchemy.Integer)  # stored as minutes since midnight
    end_time = sqlalchemy.Column(sqlalchemy.Integer)  # stored as minutes since midnight
    # Tasks
    code = sqlalchemy.Column(sqlalchemy.String, default="")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__post_init__()

    def __post_init__(self):
        if self.recurrence_parent is None:
            self.recurrence_parent = self.random_group_id()
        if self.color is None:
            # cycle to the next color
            config['color'] = colors.CYCLE_DICT[config['color']]
            self.color = config['color']

    @staticmethod
    def random_group_id():
        # return a random 4 byte integer
        return int.from_bytes(os.urandom(4), byteorder='big')

    def copy(self):
        return Event(date=self.date,
                     description=self.description,
                     color=self.color,
                     recurrence_parent=self.recurrence_parent,
                     type=self.type,
                     start_time=self.start_time,
                     end_time=self.end_time,
                     code=self.code)

    def __repr__(self):
        return f"Event({self.date}, {self.description}, {self.color}, {self.recurrence_parent}, {self.type}, {self.start_time}, {self.end_time}, {self.code})"

    def to_dict(self):
        return {key: getattr(self, key) for key in self.__table__.columns.keys()}


class Config(Base):
    __tablename__ = 'config'

    key = sqlalchemy.Column(sqlalchemy.String, default="", primary_key=True)
    value = sqlalchemy.Column(sqlalchemy.String, default="")
    # keys: military_time, timezone, start_hour, backup_location


class ConfigDict:

    def __init__(self, defaults):
        self.defaults = defaults
        self.session = Session()
        self._dict = {row.key: row for row in self.session.query(Config).all()}
        self.__contains__ = self._dict.__contains__
        self.init_defaults()

    def init_defaults(self):
        for key, value in self.defaults.items():
            if key not in self._dict:
                self._dict[key] = Config(key=key)  # create a new record
                self[key] = value
                self.session.add(self._dict[key])

    def commit(self):
        self.session.commit()

    def __getitem__(self, key):
        return json.loads(self._dict[key].value)  # self._dict[key] is a Config object (sql record)

    def __setitem__(self, key, value):
        assert key in self.defaults
        self._dict[key].value = json.dumps(value)  # self._dict[key] is a Config object (sql record)

    def __repr__(self):
        return repr({key: self[key] for key in self._dict.keys()})


def fetch_events(date, session):
    return fetch_appointments(date, session), fetch_tasks(date, session), fetch_chores(date, session)

def fetch_appointments(date, session):
    return session.query(Event).filter_by(date=date, type="appointment").order_by(Event.start_time).all()

def fetch_tasks(date, session):
    return session.query(Event).filter_by(date=date, type="task").all()

def fetch_chores(date, session):
    return session.query(Event).filter_by(date=date, type="chore").all()



# Create the file if it doesn't exist
# the database file will live in ~/.local/share/calamity/events.db
DB_PATH = os.path.join(os.path.expanduser('~'), '.local', 'share', 'calamity', 'events.db')
if not os.path.exists(os.path.dirname(DB_PATH)):
    os.makedirs(os.path.dirname(DB_PATH))

# Connect to the database
engine = create_engine(f'sqlite:///{DB_PATH}')

# Create the tables if they don't exist
Base.metadata.create_all(engine)

# Create a session factory
Session = sessionmaker(bind=engine)

# Create globally shared config object
default_config = {'military_time': False, 'timezone': 0, 'start_hour': 8, 'backup_location': '~/events_backup.db', 'ROT13': False, 'show_help': True, 'color': 'cyan'}
config = ConfigDict(default_config)
