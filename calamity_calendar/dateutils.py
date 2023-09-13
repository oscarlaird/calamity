import datetime


def n_days_in_month(date: datetime.date):
    """Get the number of days in a given month"""
    date = date.replace(day=1)
    next_month = date.replace(year=date.year + (date.month == 12), month=date.month % 12 + 1)
    return (next_month - date).days


def add_month(date: int, back=False):
    """Add a month to a given date (ordinal), keeping the day of the month the same if possible"""
    # get the number of days in this month n_days (e.g. 28 for Feb)
    date = datetime.date.fromordinal(date)
    if back:
        new_date = date.replace(year=date.year - (date.month == 1), month=(date.month - 2) % 12 + 1, day=1)
    else:
        new_date = date.replace(year=date.year + (date.month == 12), month=date.month % 12 + 1, day=1)
    # use the same day of the month if possible
    new_date = new_date.replace(day=min(date.day, n_days_in_month(new_date)))
    return new_date.toordinal()
