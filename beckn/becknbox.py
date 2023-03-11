import json
import time
from enum import Enum
from threading import Thread
from traceback import print_exc
from typing import Any, Dict

import requests

from beckn import utils
from beckn.constants import BecknConstants as BC
from beckn.events import Event, read_experience_id, trigger_event
from beckn.utils import BecknPayloads, get_config
from logger.logger import BotLogger
from utils.datetimeutils import get_local_time, timedelta
from utils.rediscache import Redis

info_logger = BotLogger.logger('infoLogger')
error_logger = BotLogger.logger('errorLogger')


class ResponseFilter(Enum):
    search = 'filter_search_responses'
    select = 'filter_select_responses'
    init = 'filter_init_responses'
    confirm = 'filter_confirm_responses'
    status = 'filter_status_responses'
    track = 'filter_track_responses'
    cancel = 'filter_cancel_responses'
    support = 'filter_support_responses'


class Beckn:
    """This class contains the helper functions for each network call"""
    _code_ = 'beckn'
    key_mediator = BC.KEY_MEDIATOR

    def __init__(self, id: str) -> None:
        self.id = id
        self.cache = Redis.read(id, 'beckn')
        if not self.cache:
            self.cache = {'transaction_id': ''}
        self.session_id = read_experience_id(id.split('_')[0])
        self.config = utils.get_config(self._code_)
        self.constructor = BecknPayloads(self.session_id, self.cache)

    def search(self, pickup_location, drop_location) -> str:
        response = ''
        try:
            action = BC.ACTION.SEARCH.action_name
            payload = self.constructor.search_payload(
                pickup_location, drop_location)
            info_logger.info("Search payload generated")
            url = self.get_url(action)
            resp = self.trigger_request("POST", url, payload=payload)
            transaction_id = resp['context']['transaction_id']
            is_acknowledged = self.acknowledgement(resp)
            if is_acknowledged:
                trigger_event(Event.SEARCH, self.session_id, '1', payload)
                response = resp['context']['message_id']
            self.cache['transaction_id'] = f"{transaction_id}.{self.session_id}"
        except Exception:
            error_logger.error('Error to get the riders', exc_info=True)
        Redis.update(self.id, "beckn", self.cache)
        return response

    def select(self, item: dict):
        response = ""
        try:
            action = BC.ACTION.SELECT.action_name
            url = self.get_url(action)
            payload = self.constructor.select_payload(item)
            resp = self.trigger_request("POST", url, payload=payload)
            p_key = f"{item['provider_id']}{BC.KEY_MEDIATOR}{item['_id'][-3:]}"
            key = f"{self.cache['providers'][p_key]['bpp_id']}"
            for each in resp:
                if key != each['context']['bpp_id']:
                    continue
                self.cache['transaction_id'] = each['context']['transaction_id']
                bpp_id = each['context']['bpp_id']
                is_acknowledged = self.acknowledgement(each)
                if is_acknowledged:
                    subscribers = get_config('subscribers')
                    trigger_event(Event.RIDE_SELECT, self.session_id,
                                  bpp_id, payload)
                    response = each['context']['message_id']
            info_logger.info("Returning select response")
        except Exception:
            error_logger.error(
                f"Error to get the quote for selection", exc_info=True)
        Redis.update(self.id, "beckn", self.cache)
        return response

    def init(self, item_ids, billing_details: dict = {}, delivery_details: dict = {}):
        response = ""
        try:
            action = BC.ACTION.INIT.action_name
            url = self.get_url(action)
            item = self.cache['items'][item_ids]
            payload = self.constructor.init_payload(item_ids,
                                                    billing_details, delivery_details)
            resp = self.trigger_request("POST", url, payload=payload)
            p_key = f"{item['provider_id']}{BC.KEY_MEDIATOR}{item['_id'][-3:]}"
            key = f"{self.cache['providers'][p_key]['bpp_id']}"
            for each in resp:
                if key != each['context']['bpp_id']:
                    continue
                self.cache['transaction_id'] = each['context']['transaction_id']
                bpp_id = each['context']['bpp_id']
                is_acknowledged = self.acknowledgement(each)
                if is_acknowledged:
                    subscribers = get_config('subscribers')
                    trigger_event(Event.RIDE_INITIATE, self.session_id,
                                  bpp_id, payload)
                    response = each['context']['message_id']
        except Exception as e:
            error_logger.error(
                f"Error to initialize the order", exc_info=True)
        info_logger.info(f"Returning init response: {response}")
        Redis.update(self.id, "beckn", self.cache)
        return response

    def confirm(self, item_ids, billing_details: dict = {}, delivery_details: dict = {}):
        response = ""
        try:
            action = BC.ACTION.CONFIRM.action_name
            url = self.get_url(action)
            item = self.cache['items'][item_ids]
            payload = self.constructor.confirm_payload(
                item_ids, billing_details, delivery_details)
            info_logger.info("Confirm payload received")
            resp = self.trigger_request("POST", url, payload=payload)
            p_key = f"{item['provider_id']}{BC.KEY_MEDIATOR}{item['_id'][-3:]}"
            key = f"{self.cache['providers'][p_key]['bpp_id']}"
            for each in resp:
                if key != each['context']['bpp_id']:
                    continue
                assert self.cache['transaction_id'] == each['context']['transaction_id'], "Transaction id mismatch"
                bpp_id = each['context']['bpp_id']
                is_acknowledged = self.acknowledgement(each)
                if is_acknowledged:
                    subscribers = get_config('subscribers')
                    trigger_event(Event.BOOK_RIDE, self.session_id,
                                  bpp_id, payload)
                    response = each['context']['message_id']
        except Exception as e:
            error_logger.error(
                f"Error to confirm the order", exc_info=True)
        info_logger.info(f"Returning confirm response: {response}")
        return response

    def status(self, order_id):
        response = ""
        try:
            assert order_id == self.cache['orders']['id'], 'Invalid order id'
            action = BC.ACTION.STATUS.action_name
            url = self.get_url(action)
            payload = self.constructor.status_payload()
            info_logger.info("Status payload received")
            resp = self.trigger_request("POST", url, payload=payload)
            for each in resp:
                bpp_id = each['context']['bpp_id']
                is_acknowledged = self.acknowledgement(each)
                if is_acknowledged:
                    subscribers = get_config('subscribers')
                    trigger_event(Event.RIDE_STATUS, self.session_id,
                                  bpp_id, payload)
                    response = each['context']['message_id']
        except Exception as e:
            error_logger.error(
                f"Error to get order status", exc_info=True)
        info_logger.info(f"Returning status response: {response}")
        return response

    def track(self):
        response = ""
        try:
            action = BC.ACTION.TRACK.action_name
            url = self.get_url(action)
            payload = self.constructor.track_payload()
            info_logger.info(f'Track payload received: {payload}')
            resp = self.trigger_request("POST", url, payload=payload)
            for each in resp:
                bpp_id = each['context']['bpp_id']
                is_acknowledged = self.acknowledgement(each)
                if is_acknowledged:
                    # subscribers = get_config('subscribers')
                    # trigger_event(Event.Track, self.session_id,
                    #               bpp_id, payload)
                    response = each['context']['message_id']
        except Exception as e:
            error_logger.error(
                f"Error to track the order", exc_info=True)
        info_logger.info(f"Returning track response: {response}")
        return response

    def cancel(self, reason_id):
        response = ""
        try:
            receiver = self.id.split('_')[0]
            if self.cache['orders']['state'].lower() == 'started':
                cancel_msg = 'Sorry, Ride already started, ride cannot be cancelled.'
                update_rider_status(cancel_msg, receiver)
            elif self.cache['orders']['state'].lower() == 'ended':
                cancel_msg = 'Sorry, You have completed the ride cannot be cancelled'
                update_rider_status(cancel_msg, receiver)
            else:
                action = BC.ACTION.CANCEL.action_name
                url = self.get_url(action)
                payload = self.constructor.cancel_payload(reason_id)
                info_logger.info(f'Cancel payload received: {payload}')
                resp = self.trigger_request("POST", url, payload=payload)
                bpp_id = resp['context']['bpp_id']
                is_acknowledged = self.acknowledgement(resp)
                if is_acknowledged:
                    subscribers = get_config('subscribers')
                    trigger_event(Event.CANCEL, self.session_id,
                                  bpp_id, payload)
                msg_id = resp['context']['message_id']
                for i in range(3):
                    time.sleep(5)
                    resp = self.poll(action, msg_id)
                    if resp:
                        cancel_msg = "Your trip has been *Cancelled* successfully. Thank you for using Ride Services!"
                        update_rider_status(cancel_msg, receiver)
                        break
                return resp
        except Exception as e:
            error_logger.error(
                f"Error to cancel the order", exc_info=True)
        info_logger.info(f"Returning track response: {response}")

    def support(self):
        response = ''
        try:
            action = BC.ACTION.SUPPORT.action_name
            url = self.get_url(action)
            payload = self.constructor.support_payload()
            info_logger.info('Support payload received')
            resp = self.trigger_request("POST", url, payload=payload)
            for each in resp:
                bpp_id = each['context']['bpp_id']
                is_acknowledged = self.acknowledgement(each)
                if is_acknowledged:
                    subscribers = get_config('subscribers')
                    trigger_event(Event.SUPPORT, self.session_id,
                                  bpp_id, payload)
                    msg_id = each['context']['message_id']
            while True:
                response = self.poll(action, msg_id)
                if response:
                    break
            return True
        except Exception as e:
            error_logger.error(
                f"Error to support the order", exc_info=True)
        info_logger.info(f"Returning support response: {response}")

    def wait_for_response(self, action):
        time.sleep(self.config[action]['wait_time'])
        return

    def get_url(self, action, is_callback=False):
        if is_callback:
            url = f"{self.config['base_url']}{self.config[action]['cb_path']}"
        else:
            url = f"{self.config['base_url']}{self.config[action]['path']}"
        return url

    def poll(self, action, message_id):
        response = None
        try:
            info_logger.info(f"Collecting {action} callback")
            cb_resp = self.collect_callback(action, message_id)
            resp_filter_as_method = getattr(
                utils, ResponseFilter[action].value)
            response = resp_filter_as_method(cb_resp, self.cache)
            info_logger.info(f"Returning {action} response")
            if action == 'confirm' and response is not None:
                order_id = response['id']
                t1 = Thread(target=trigger_status, args=(self, order_id))
                t1.start()
        except Exception:
            error_logger.error(f'Polling Error for {action}:', exc_info=True)
        Redis.update(self.id, "beckn", self.cache)
        return response

    def collect_callback(self, action: str, message_id):
        try:
            if action in [BC.ACTION.SEARCH.action_name, BC.ACTION.CANCEL.action_name]:
                params = {
                    "messageId": message_id
                }
            elif action == BC.ACTION.STATUS.action_name:
                params = {
                    "orderIds": message_id
                }
            else:
                params = {
                    "messageIds": message_id
                }

            url = self.get_url(action, True)
            search_resp = self.trigger_request(
                'GET', url, params=params, headers=None)
        except Exception as e:
            print_exc()
        return search_resp

    @classmethod
    def acknowledgement(cls, response) -> bool:
        ack = False
        try:
            message = response['message']
            if message['ack']['status'].lower() == BC.ACK.lower():
                ack = True
            return ack
        except KeyError as ke:
            error_logger.error("Error in reading acknowledgement")
            return ack

    def header(self):
        header = {
            'Content-Type': 'application/json'
        }
        return header

    @staticmethod
    def trigger_request(method, url, payload: Any = None, params: dict = {}, headers: dict = {}) -> Dict:
        response = {}
        if isinstance(payload, (dict, list)):
            payload = json.dumps(payload)
            headers.update({
                'Content-Type': 'application/json'
            })

        r = requests.request(method, url, params=params,
                             data=payload, headers=headers)
        if r.status_code == 200:
            response = r.json()
            info_logger.info(
                f"Request details : {url} | {payload} | {r.status_code} | {response}")
        else:
            info_logger.info(
                f"Request details : {url} | {payload} | {r.status_code} | {r.text} ")
            r.raise_for_status()
        return response


def update_rider_status(state, receiver):
    from runner.methods import get_customer_config
    sender = get_customer_config('ondc')
    apikey = sender['apikey']
    headers = {
        'apikey': apikey,
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    post_url = 'https://api.gupshup.io/sm/api/v1/msg'
    data = {
        'channel': 'whatsapp',
        'source': sender['source'],
        'destination': receiver,
        'message': '{"type":"text","text": "' + state + '"}',
        'src.name': sender['appname']
    }
    response = requests.post(post_url, headers=headers, data=data)
    resp_data = response.json()
    print(resp_data)


def return_tracking_url(url):
    response = requests.post(url)
    try:
        track_json = response.json()
        if (track_json):
            print(track_json)
            return track_json['map_url']
        else:
            return ""
    except Exception:
        print("Unable to retrieve track url")
        return ""


def get_track_details(cls: Beckn, msg_id, receiver):
    try:
        info_logger.info("Featching the track details from beckn")
        while True:
            if cls.cache['orders']['state'].lower() in ['canceled', 'ended']:
                break
            track_resp = cls.poll('track', msg_id)
            if track_resp:  
                track_msg: str = get_config('track_msg')
                track_link = return_tracking_url(track_resp['track_url'])
                if track_link:
                    state = track_msg.format(track_link=track_link)
                    update_rider_status(state, receiver)
                    break
    except Exception as e:
        error_logger.error("Exception to get track details", exc_info=True)


def terminate(start, end):
    kill_thread = False
    now = get_local_time()
    if now > end:
        kill_thread = True
    return kill_thread


def trigger_status(cls: Beckn, order_id):
    try:
        terminal_state = ['ended', 'canceled']
        start = get_local_time()
        end = start + timedelta(minutes=3)
        thread_life = start + timedelta(minutes=57)
        sleep_time = 10
        msg_id = cls.status(order_id)
        info_logger.info(f"Order Status requested for order_id: {order_id}")
        status = get_config('ride_status')
        confirmed_state = "Awaiting Driver acceptance"
        last_state = confirmed_state
        receiver = cls.id.split("_")[0]
        while True:
            time.sleep(sleep_time)
            resp = cls.poll('status', order_id)
            if resp:
                state = resp['state']
                if state == last_state:
                    if last_state == confirmed_state:
                        kill_thread = terminate(start, end)
                        terminate_msg = True
                    else:
                        kill_thread = terminate(start, thread_life)
                        terminate_msg = False
                    if kill_thread:
                        if terminate_msg:
                            update_rider_status(
                                status[state.lower()], receiver)
                        break
                else:
                    if state.lower() in terminal_state:
                        if cls.cache['orders']['state'].lower() == 'canceled':
                            break
                        update_rider_status(status[state.lower()], receiver)
                        break
                    if state.lower() in ['reached pickup location', 'reaching pickup location']:
                        msg_id = cls.track()
                        track_thread = Thread(
                            target=get_track_details,  args=(cls, msg_id, receiver))
                        track_thread.start()
                    update_rider_status(status[state.lower()], receiver)
                    last_state = state
    except Exception as e:
        error_logger.error("Error to push the status:", exc_info=True)
        pass
