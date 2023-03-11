from enum import Enum
import json
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4
import requests
from beckn.constants import BecknConstants as BC
from utils.fileutils import FileUtils as fu
from utils.datetimeutils import get_utc_iso_datetime
from logger.logger import BotLogger
from beckn.utils import get_config

info_logger = BotLogger.logger('infoLogger')
error_logger = BotLogger.logger('errorLogger')


class Event(Enum):
    """
    List of events with value as a tuple Example
    event_name = event_message_key, source, destination, event_code
    """
    BEGIN = 'begin', 'mbwa_init_chat'
    READ_NAME = 'read_name', 'mbwa_enter_name'
    SELECT_LANG = 'select_lang', 'mbwa_language_selection'
    ENTER_PICKUP_LOC = 'read_pickup_loc', 'mbwa_pickup_loc'
    ENTER_DROP_LOC = 'read_drop_loc', 'mbwa_drop_loc'
    OTP_VERIFY = '5', 'E005'
    SEARCH = 'search', 'mbwa_srch_init'
    RIDE_SELECT = 'select', 'mbwa_ride_slectd'
    RIDE_INITIATE = 'init', 'mbwa_init_ride'
    BOOK_RIDE = 'confirm', 'mbwa_bkng_ride'
    RIDE_STATUS = 'status', 'mbwa_fetch_status'
    CANCEL = 'cancel', 'mbwa_cncl_ride'
    SUPPORT = 'support', 'mbwa_support_req'

    def __new__(cls, key: str, code: str):
        obj = object.__new__(cls)
        obj._value_ = key
        obj._code_ = code
        return obj

    # Ensure that the description is read-only
    @property
    def code(self):
        return self._code_


def get_event_messages(field=None) -> dict:
    file_path = Path('beckn/events.json').resolve(strict=True)
    modified_time = file_path.stat().st_mtime
    data = fu.read_json_file(file_path, modified_time)
    if field:
        return data[field]
    return data

class ServerBus:

    @staticmethod
    def comunicate(method, url, payload: Any = None, params: dict = {}, headers: dict = {}) -> Dict:
        response = {}
        if isinstance(payload, (dict, list)):
            payload = json.dumps(payload)
            headers.update(
                {
                    'Content-Type': 'application/json'
                }
            )
        r = requests.request(method, url, params=params,
                             data=payload, headers=headers)
        if r.status_code == 200:
            if 'text/plain' in r.headers.get('Content-Type', ''):
                response =  r.text
            else:
                response = r.json()
            info_logger.info(
                f"Request details : {url} | {payload} | {r.status_code} | {response}")
        else:
            info_logger.info(
                f"Request details : {url} | {payload} | {r.status_code} | {r.text} ")
            r.raise_for_status()
        return response


def generate_experience_id(contact):
    try:
        with open('beckn/sessions.json', 'r') as f:
            data = json.load(f)
        url = get_config('session_url')
        resp = ServerBus.comunicate('GET', url)
        if resp:
            experience_id = resp
        else:
            info_logger.info('Local experience id used')
            experience_id = str(uuid4())
        data[contact] = experience_id
        with open('beckn/sessions.json', 'w') as f:
            json.dump(data, f, indent=4)
        return experience_id
    except Exception:
        error_logger.error(f"Error to generate the experence_id", exc_info=True)

def read_experience_id(contact):
    try:
        with open('beckn/sessions.json', 'r') as f:
            data = json.load(f)
        experience_id = data.get(contact, None)
        return experience_id
    except Exception as e:
        error_logger.error(f"Error to read the experence_id", exc_info=True)



def trigger_event(event: Event, exp_id, event_destination_id, payload=None):
    try:
        info_logger.info('Triggering the event')
        config = get_config('events')
        if str(event_destination_id) == '4':
            event_destination_id = 'mobilityreferencebap-staging.becknprotocol.io'
        if str(event_destination_id) == '1':
            event_destination_id = 'gateway.becknprotocol.io'
        data = {
            "experienceId": exp_id,
            "eventCode": event.code,
            "eventSourceId": "mobilityreferencebap-staging.becknprotocol.io",
            "eventDestinationId": event_destination_id,
            "eventAction": "",
            "eventStart_ts": get_utc_iso_datetime(),
            "payload": ""
        }
        if event.value in BC.ACTION.list():
            data["eventAction"]= event.value
        if payload is not None:
            data['payload'] = json.dumps(payload)
        url = f"{config['base_url']}{config['path']}"
        ServerBus.comunicate('POST', url, data)
    except Exception as e:
        error_logger.error(
            f"Error to log the event:{event.name}", exc_info=True)

