import re
import datetime as dt
import pytz

def get_template_name(text):
    result = re.search(r".*?\[(.*?)\]", text)
    if(result):
        return result.group(1)
    else:
        return None

def get_template_title(text):
    title = re.sub("\[.*?\]", "", text)
    return title


def get_numeric_data(text):
    result = re.search(r'(\d+)\s*[a-zA-z]*', text)
    if(result):
        return result.group(1)
    else:
        return None
    

def get_date_time(timestamp):
    time_val = dt.datetime.fromtimestamp(timestamp/1000).strftime(
        '%Y-%m-%d %H:%M:%S')
    return time_val


def get_vars_in_curly_braces(text):
    result = re.search(r'{(.*?)}', text)
    if(result):
        return result.groups


def timestamp2datetime(timestamp, utc=False) -> dt:
    # utc timestamp will have seconds and 10 digits
    # timestamp with 13 digits will be in miliseconds
    if str(timestamp).__len__()>12:
        timestamp = timestamp/1000
    ISTz = pytz.timezone('Asia/Kolkata')
    try:
        if utc:
            print("inside utc")
            return dt.datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        return dt.datetime.fromtimestamp(timestamp, ISTz).strftime("%Y-%m-%d %H:%M:%S")
    except OSError as ose:
        raise ose



print(timestamp2datetime(1644391988944, True))
print(timestamp2datetime(1644391988944))

