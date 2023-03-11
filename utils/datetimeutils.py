from datetime import datetime, timedelta

from dateutil import parser, tz


def get_utc_datetime():
    utc_dt = datetime.now(tz=tz.gettz('UTC'))
    return utc_dt


def get_local_time(dt_string=None):
    local_tz = tz.gettz('Asia/Kolkata')
    if not dt_string:
        return datetime.now(local_tz)
    dt = parser.parse(dt_string)
    return dt.astimezone(local_tz)


def get_utc_iso_datetime():
    utc_datetime = get_utc_datetime()
    iso_datetime = utc_datetime.isoformat(
        timespec="milliseconds").replace("+00:00", 'Z')
    return iso_datetime
