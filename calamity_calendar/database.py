import sqlalchemy
import datetime
import os
import json

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import logging

# delete the log file
"""
open('sqlalchemy.log', 'w').close()
logger = logging.getLogger('sqlalchemy')
logger.setLevel(logging.INFO)
#redirect to sqlachemy.log
logger.addHandler(logging.FileHandler('sqlalchemy.log', mode='w'))
"""

# logging.basicConfig(filename='sqlalchemy.log', level=logging.INFO)

# Create the events table
# the database file will live in ~/.local/share/calamity/events.db
DB_PATH = os.path.join(os.path.expanduser('~'), '.local', 'share', 'calamity', 'events.db')
engine = create_engine(f'sqlite:///{DB_PATH}')

# Create a session
Session = sessionmaker(bind=engine)

# Declare the base
Base = declarative_base()

# Declare the table of events
class Event(Base):
    __tablename__ = 'events'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    date = sqlalchemy.Column(sqlalchemy.Integer, default=datetime.date.today().toordinal())  # stored as julian date
    description = sqlalchemy.Column(sqlalchemy.String, default="")
    color = sqlalchemy.Column(sqlalchemy.String, default='red')
    recurrence_parent = sqlalchemy.Column(sqlalchemy.Integer) # id of parent event
    type = sqlalchemy.Column(sqlalchemy.String, default='task') # type of event, e.g. appointment, task, etc. # enforce not NULL
    # Appointments
    start_time = sqlalchemy.Column(sqlalchemy.Integer)  # stored as minutes since midnight
    end_time = sqlalchemy.Column(sqlalchemy.Integer)  # stored as minutes since midnight
    # Tasks
    code = sqlalchemy.Column(sqlalchemy.String, default="")

    def __post_init__(self):
        if self.recurrence_parent is None:
            self.recurrence_parent = self.random_group_id()

    @staticmethod
    def random_group_id(self):
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

    def __init__(self):
        self.session = Session()
        self._dict = {row.key: row for row in self.session.query(Config).all()}
        self.__contains__ = self._dict.__contains__
        self.init_defaults()

    def init_defaults(self):
        for key, value in default_config.items():
            if key not in self._dict:
                self._dict[key] = Config(key=key)  # create a new record
                self[key] = value
                self.session.add(self._dict[key])

    def commit(self):
        self.session.commit()

    def __getitem__(self, key):
        return json.loads(self._dict[key].value)  # self._dict[key] is a Config object (sql record)

    def __setitem__(self, key, value):
        assert key in default_config
        self._dict[key].value = json.dumps(value)  # self._dict[key] is a Config object (sql record)

    def __repr__(self):
        return repr({key: self[key] for key in self._dict.keys()})


default_config = {'military_time': False, 'timezone': 0, 'start_hour': 8, 'backup_location': '~/events_backup.db', 'ROT13': False, 'show_help': True}
config = ConfigDict()




def fetch_events(date, session):
    return fetch_appointments(date, session), fetch_tasks(date, session), fetch_chores(date, session)

def fetch_appointments(date, session):
    return session.query(Event).filter_by(date=date, type="appointment").order_by(Event.start_time).all()

def fetch_tasks(date, session):
    return session.query(Event).filter_by(date=date, type="task").all()

def fetch_chores(date, session):
    return session.query(Event).filter_by(date=date, type="chore").all()



# Create the table
Base.metadata.create_all(engine)
