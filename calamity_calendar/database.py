import sqlalchemy
import datetime
import os

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
db_path = os.path.join(os.path.expanduser('~'), '.local', 'share', 'calamity', 'events.db')
engine = create_engine(f'sqlite:///{db_path}')

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

def fetch_days_events(date, session):
    tasks = session.query(Event).filter_by(date=date, type="task").all()
    appointments = session.query(Event).filter_by(date=date, type="appointment").order_by(
        Event.start_time).all()
    chores = session.query(Event).filter_by(date=date, type="chore").all()
    return tasks, appointments, chores


# Create the table
Base.metadata.create_all(engine)
