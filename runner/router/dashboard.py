import json
from datetime import datetime
from pathlib import Path
from pprint import pprint

from dateutil import tz
from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import Response

from beckn.becknbox import Beckn
from beckn.events import (Event, generate_experience_id, read_experience_id,
                          trigger_event)
from customer.beckn.handler.FlowHandler import FlowHandler
from FalconUtils.mongo.mongoutils import MongoDB
from logger.logger import BotLogger
from utils.gupshupconnector import post_to_gupshup
from utils.intent_util import is_greeting
from utils.rediscache import Redis

from ..methods import get_customer_config, schedule_task

info_logger = BotLogger.logger('infoLogger')
err_logger = BotLogger.logger('errorLogger')
db_logger = BotLogger.logger('dbLogger')

key = "secret"

tracker = {

}


router = APIRouter()


def flow_excecuter(customer_code, lang, flow_data, prev_state, custdata, receiver, campaign_id, current_state, db, bgtask):
    """ Reads flow data for a given state and executes it """
    try:
        info_logger.info(
            f"flow excecuter current state: {current_state}\nFlow excecuter prev state: {prev_state}")
        params = flow_data[current_state]
        pprint(params)
        handler = params.get('handler', None)
        cust_key = f'{receiver}_{campaign_id}'

        if handler:
            info_logger.info(
                f"*********************{params['handler']}******************")
            handler_as_method = getattr(FlowHandler, params['handler'], None)
            params['handler_value'] = handler_as_method(
                receiver, campaign_id, db)
            info_logger.info(
                f'Value from handler is {params["handler_value"]}')

            # handler error in bap_select
            if params['handler_value'] == 'Error' and params['handler'] == 'bap_select':
                info_logger.info(f'Sending fail message to gupshup trigger')
                params["reply"] = 'TEXT'
                params['message'] = ''
                Redis.update(cust_key, "flow_status", "END")
                curr = current_state.split('_')[1]
                params = {
                    "message": f"{curr.upper()}_TXT_END",
                    "reply": "TEXT",
                    "next_state": "5_ondc",
                    "continue": True
                }
                current_state = f'endlistride_{curr}'
                bgtask.add_task(post_to_gupshup, lang, custdata, receiver, params,
                                campaign_id, prev_state, current_state)
                if params.get('continue', False):
                    flow_excecuter(customer_code, lang, flow_data, current_state, custdata,
                                   receiver, campaign_id, params['next_state'], db, bgtask)
                return

            # handler error in bap_search
            if params['handler_value'] == 'Error' and params['handler'] == 'bap_search':
                info_logger.info(f'Sending fail message to gupshup trigger')
                params["reply"] = 'TEXT'
                params['message'] = ''
                info_logger.info(f'Params is {params}')
                Redis.update(cust_key, "flow_status", "END")
                curr = current_state.split('_')[1]
                params = {
                    "message": f"{curr.upper()}_TXT_END",
                    "reply": "TEXT",
                    "next_state": "END",
                    "continue": True
                }

                current_state = f'endfail_{curr}'
                bgtask.add_task(post_to_gupshup, lang, custdata, receiver, params,
                                campaign_id, prev_state, current_state)
                if params.get('continue', False):
                    flow_excecuter(customer_code, lang, flow_data, current_state, custdata,
                                   receiver, campaign_id, params['next_state'], db, bgtask)
                return

            # handle error in bap_init
            if params['handler_value'] == 'Error' and params['handler'] == 'bap_init':
                info_logger.info(f'Sending fail message to gupshup trigger')
                params["reply"] = 'TEXT'
                params['message'] = ''
                info_logger.info(f'Params is {params}')
                Redis.update(cust_key, "flow_status", "END")
                curr = current_state.split('_')[1]
                params = {
                    "message": f"{curr.upper()}_TXT_END",
                    "reply": "TEXT",
                    "next_state": "END",
                    "continue": True
                }

                current_state = f'endfail_{curr}'
                bgtask.add_task(post_to_gupshup, lang, custdata, receiver, params,
                                campaign_id, prev_state, current_state)
                if params.get('continue', False):
                    flow_excecuter(customer_code, lang, flow_data, current_state, custdata,
                                   receiver, campaign_id, params['next_state'], db, bgtask)
                return
            if params['handler_value'] == 'IssueError':
                keylang = f'{receiver}_{campaign_id}'
                info_logger.info('Lang is', Redis.read(keylang, 'language'))
                info_logger.info(f'Sending fail message to gupshup trigger')
                params["reply"] = 'TEXT'
                params['message'] = ''
                info_logger.info(f'Params is {params}')
                Redis.update(cust_key, "flow_status", "END")
                curr = current_state.split('_')[1]
                if Redis.read(keylang, 'language') == 'English':
                    params = {
                        "message": f"{curr.upper()}_TXT_FAIL",
                        "reply": "TEXT",
                        "next_state": "END"

                    }
                else:
                    params = {
                        "message": f"HI_TXT_FAIL",
                        "reply": "TEXT",
                        "next_state": "END"

                    }

                current_state = f'endfail_{curr}'
                bgtask.add_task(post_to_gupshup, lang, custdata, receiver, params,
                                campaign_id, prev_state, current_state)
                if params.get('continue', False):
                    flow_excecuter(customer_code, lang, flow_data, current_state, custdata,
                                   receiver, campaign_id, params['next_state'], db, bgtask)
                return

            if params['handler_value'] == 'LocationErrorStart':
                info_logger.info('Parameters received:', params)
                if params['next_state'] == '3_ondc':
                    info_logger.info(
                        f'Sending fail message to gupshup trigger')
                    params["reply"] = 'TEXT'
                    params['message'] = ''
                    info_logger.info(f'Params is {params}')
                    Redis.update(cust_key, "flow_status", "END")
                    curr = current_state.split('_')[1]
                    params = {
                        "message": f"ONDC_TXT_LOC_END",
                        "reply": "TEXT",
                        "next_state": "2a_ondc"

                    }

                    current_state = f'start_{curr}'
                    bgtask.add_task(post_to_gupshup, lang, custdata, receiver, params,
                                    campaign_id, prev_state, current_state)
                    if params.get('continue', False):
                        flow_excecuter(customer_code, lang, flow_data, current_state, custdata,
                                       receiver, campaign_id, params['next_state'], db, bgtask)
                    return
                if params['next_state'] == '13_ondc':
                    info_logger.info(
                        f'Sending fail message to gupshup trigger')
                    params["reply"] = 'TEXT'
                    params['message'] = ''
                    info_logger.info(f'Params is {params}')
                    Redis.update(cust_key, "flow_status", "END")
                    curr = current_state.split('_')[1]
                    params = {
                        "message": f"HI_TXT_LOC_END",
                        "reply": "TEXT",
                        "next_state": "12a_ondc"

                    }

                    current_state = f'1start_{curr}'
                    bgtask.add_task(post_to_gupshup, lang, custdata, receiver, params,
                                    campaign_id, prev_state, current_state)
                    if params.get('continue', False):
                        flow_excecuter(customer_code, lang, flow_data, current_state, custdata,
                                       receiver, campaign_id, params['next_state'], db, bgtask)
                    return
            if params['handler_value'] == 'LocationErrorEnd':
                info_logger.info('Parameters received:', params)
                if params['next_state'] == '4_ondc':
                    info_logger.info(
                        f'Sending fail message to gupshup trigger')
                    params["reply"] = 'TEXT'
                    params['message'] = ''
                    info_logger.info(f'Params is {params}')
                    Redis.update(cust_key, "flow_status", "END")
                    curr = current_state.split('_')[1]
                    params = {
                        "message": f"ONDC_TXT_LOC_END",
                        "reply": "TEXT",
                        "next_state": "3_ondc"

                    }

                    current_state = f'endloc_{curr}'
                    bgtask.add_task(post_to_gupshup, lang, custdata, receiver, params,
                                    campaign_id, prev_state, current_state)
                    if params.get('continue', False):
                        flow_excecuter(customer_code, lang, flow_data, current_state, custdata,
                                       receiver, campaign_id, params['next_state'], db, bgtask)
                    return
                if params['next_state'] == '14_ondc':
                    info_logger.info(
                        f'Sending fail message to gupshup trigger')
                    params["reply"] = 'TEXT'
                    params['message'] = ''
                    info_logger.info(f'Params is {params}')
                    Redis.update(cust_key, "flow_status", "END")
                    curr = current_state.split('_')[1]
                    params = {
                        "message": f"HI_TXT_LOC_END",
                        "reply": "TEXT",
                        "next_state": "13_ondc"

                    }

                    current_state = f'1endloc_{curr}'
                    bgtask.add_task(post_to_gupshup, lang, custdata, receiver, params,
                                    campaign_id, prev_state, current_state)
                    if params.get('continue', False):
                        flow_excecuter(customer_code, lang, flow_data, current_state, custdata,
                                       receiver, campaign_id, params['next_state'], db, bgtask)
                    return

            if params['handler_value'] == 'Error' and params['handler'] == 'bap_pay':
                info_logger.info(f'Sending fail message to gupshup trigger')
                params["reply"] = 'TEXT'
                params['message'] = ''
                info_logger.info(f'Params is {params}')
                Redis.update(cust_key, "flow_status", "END")
                curr = current_state.split('_')[1]
                params = {
                    "message": f"{curr.upper()}_TXT_END",
                    "reply": "TEXT",
                    "next_state": "5a_ondc",
                    "continue": True
                }

                current_state = f'endlistpay_{curr}'
                bgtask.add_task(post_to_gupshup, lang, custdata, receiver, params,
                                campaign_id, prev_state, current_state)
                if params.get('continue', False):
                    flow_excecuter(customer_code, lang, flow_data, current_state, custdata,
                                   receiver, campaign_id, params['next_state'], db, bgtask)
                return

            info_logger.info('handler value caculated')

        #  case when next state to be triggered is button message
        if params['reply'] == "BUTTON":
            if current_state == prev_state:
                curr = current_state.split('_')[1]
                current_state = f'endbutton_{curr}'
                bgtask.add_task(post_to_gupshup, lang, custdata, receiver, params,
                                campaign_id, prev_state, current_state)
            else:
                bgtask.add_task(post_to_gupshup, lang, custdata, receiver, params,
                                campaign_id, prev_state, current_state)
            if params.get('continue', False):
                flow_excecuter(customer_code, lang, flow_data, current_state, custdata,
                               receiver, campaign_id, params['next_state'], db, bgtask)

        # case when next state to be triggered is text/image message
        if params['reply'] == 'TEXT' or params['reply'] == 'IMAGE':
            bgtask.add_task(post_to_gupshup, lang, custdata, receiver, params,
                            campaign_id, prev_state, current_state)
            if params.get('continue', False):
                flow_excecuter(customer_code, lang, flow_data, current_state, custdata,
                               receiver, campaign_id, params['next_state'], db, bgtask)

        # case when next state to be triggered is list message
        if params['reply'] == 'LIST':
            if current_state == prev_state:
                curr = current_state.split('_')[1]
                if current_state == f'5_{curr}':
                    current_state = f'endlistride_{curr}'
                elif current_state == f'5a_{curr}':
                    current_state = f'endlistpay_{curr}'
                info_logger.info(current_state)

                bgtask.add_task(post_to_gupshup, lang, custdata, receiver, params,
                                campaign_id, prev_state, current_state)
            else:
                bgtask.add_task(post_to_gupshup, lang, custdata, receiver, params,
                                campaign_id, prev_state, current_state)
            if params.get('continue', False):
                flow_excecuter(customer_code, lang, flow_data, current_state, custdata,
                               receiver, campaign_id, params['next_state'], db, bgtask)
        return

    except KeyError as ke:
        raise ke
    except Exception as e:
        raise e


class FlowFileError(Exception):
    pass


# @lru_cache(typed=True, maxsize=50)
def get_customer_flow(customer_code, flow_name) -> dict:

    flow_file_path = ""
    try:
        flow_file_path = Path(
            f'./customer/{customer_code}/resource/{flow_name}.json').resolve(strict=True)
        with open(flow_file_path, 'r') as f:
            flow_data = json.load(f)
        return flow_data
    except FileNotFoundError as e:
        print(f"Error raised: Missing file {flow_file_path}")
        raise FlowFileError(flow_file_path)
    except json.JSONDecodeError as e:
        return {}


def build_flow(customer_code, sender, contact, campaign_id, db, bgtask, user_text=None, user_option=None, btn_reply_state=None, latitude=None, longitude=None):
    """Builds the flow, identifies the state and passes details to flow_executor to execute the flow"""
    try:
        cust_key = f'{contact}_{campaign_id}'

        # Read flow for the current customer, get the current/previous states
        data = db.get_node({'_id': cust_key}, 'transactions')
        lang = data['lang']
        flow_name = data['flow']
        current_state = data.get('current_state', None)
        prev_state = data.get('prev_state', None)

        tracker[cust_key] = Redis.read(cust_key)
        if tracker[cust_key] is None:
            Redis.write(cust_key, {})
            tracker[cust_key] = Redis.read(cust_key)

        info_logger.info(f"Flow : {flow_name}")
        info_logger.info(f"Current_state: {current_state}")

        if current_state == 'ondc_origin':
            exp_id = read_experience_id(contact)
            trigger_event(Event.READ_NAME, exp_id, '4')
        message_ids = data['message_ids']

        flow_data = get_customer_flow(customer_code, flow_name)

        if flow_data[current_state].get('next_state') == "prev_state":
            db.update_node({'current_state': prev_state}, {
                           '_id': cust_key}, 'transactions')
            current_state = prev_state

        if user_option and current_state != btn_reply_state:
            # 1. User clicks on cancel , completes cancel flow, then clicks on support
            # 2. User clicks on support and then clicks on cancel
            if message_ids[btn_reply_state]['response'] and not flow_data[btn_reply_state].get('switch_state', False):
                return
            else:
                current_state = btn_reply_state
        if message_ids[current_state]['response'] and not flow_data[btn_reply_state].get('switch_state', False):
            return

        message_ids[current_state]['response'] = user_text
        db.update_node({'message_ids': message_ids}, {
                       '_id': cust_key}, 'transactions')

        if flow_data[current_state].get('store_to_db', False):
            intent_name = ""
            if flow_data[current_state]['intent'].startswith('location'):
                intent_name = flow_data[current_state]['intent'].split('_')[1]
                user_text = f'{latitude}_{longitude}'
            if flow_data[current_state]['intent'].startswith('customer'):
                intent_name = flow_data[current_state]['intent']

            dict_ = {intent_name: user_text}
            db.update_node(dict_, data, 'transactions')
            print(f"Storing to DB: {flow_data[current_state]['intent']}")

        if flow_data[current_state].get('store_to_dict', False):
            Redis.update(
                cust_key, flow_data[current_state]['intent'], user_text)

        params = flow_data[current_state]

        if flow_data:
            if params.get('reply', None) == "BUTTON":
                if current_state == '1_ondc':
                    exp_id = read_experience_id(contact)
                    trigger_event(Event.SELECT_LANG, exp_id, '4')
                info_logger.info("Button reply calling flow excecuter")
                flow_excecuter(customer_code, lang, flow_data, current_state, sender, contact,
                               campaign_id, params[f"{user_option}_option_state"], db, bgtask)

            elif params.get('reply', None) == "TEXT" or params.get('reply', None) == "IMAGE":
                info_logger.info("Text reply calling flow excecuter")
                flow_excecuter(customer_code, lang, flow_data, current_state, sender,
                               contact, campaign_id, params['next_state'], db, bgtask)

            elif params.get('reply', None) == "LIST":
                info_logger.info("List reply calling flow executor")

                from customer.ondc.handler.format import postback

                if user_text not in postback:

                    if current_state == f'5_{flow_name.lower()}':
                        current_state = f'endlistride_{flow_name.lower()}'
                    elif current_state == f'5a_{flow_name.lower()}':
                        current_state = f'endlistpay_{flow_name.lower()}'
                    elif current_state == f'15_{flow_name.lower()}':
                        current_state = f'1endlistride_{flow_name.lower()}'
                    elif current_state == f'15a_{flow_name.lower()}':
                        current_state = f'1endlistpay_{flow_name.lower()}'
                    flow_excecuter(customer_code, lang, flow_data, current_state, sender,
                                   contact, campaign_id, current_state, db, bgtask)
                else:
                    if current_state == '10a_ondc' or current_state == '110a_ondc':
                        key = f'{contact}_{campaign_id}'
                        bobj = Beckn(key)
                        bobj.cancel(user_text)
                        return Response(status_code=200)
                    flow_excecuter(customer_code, lang, flow_data, current_state, sender,
                                   contact, campaign_id, params['next_state'], db, bgtask)

            else:
                flow_excecuter(customer_code, lang, flow_data, current_state, sender,
                               contact, campaign_id, params[user_text], db, bgtask)
        return
    except FlowFileError as e:
        raise e

    except KeyError as ke:
        #raise ke

        if ke:
            print(params['reply'])
            print(flow_data[current_state])
            if Redis.read(cust_key, 'language') == 'English':
                if params['reply'] == 'BUTTON' and 'TXT_1' in flow_data[current_state]['message']:
                    current_state = f'endbutton_{flow_name.lower()}'
                    print(current_state)
                    flow_excecuter(customer_code, lang, flow_data, current_state, sender,
                                   contact, campaign_id, current_state, db, bgtask)

                elif params['reply'] == 'BUTTON' and 'TXT_8' in flow_data[current_state]['buttons']:
                    current_state = f'endhelp_{flow_name.lower()}'
                    print(current_state)
                    flow_excecuter(customer_code, lang, flow_data, current_state, sender,
                                   contact, campaign_id, current_state, db, bgtask)
            else:
                if params['reply'] == 'BUTTON' and 'TXT_1' in flow_data[current_state]['message']:
                    current_state = f'1endbutton_{flow_name.lower()}'
                    print(current_state)
                    flow_excecuter(customer_code, lang, flow_data, current_state, sender,
                                   contact, campaign_id, current_state, db, bgtask)

                elif params['reply'] == 'BUTTON' and 'TXT_8' in flow_data[current_state]['buttons']:
                    current_state = f'1endhelp_{flow_name.lower()}'
                    print(current_state)
                    flow_excecuter(customer_code, lang, flow_data, current_state, sender,
                                   contact, campaign_id, current_state, db, bgtask)
                elif params['reply'] == 'BUTTON' and 'bap_select' in flow_data[current_state]['handler']:
                    current_state = f'1endproceed_{flow_name.lower()}'
                    print(current_state)
                    flow_excecuter(customer_code, lang, flow_data, current_state, sender,
                                   contact, campaign_id, current_state, db, bgtask)


@ router.post("/{customer_code}/webhook")
async def response_from_gupshup(customer_code: str, request: Request, bgtask: BackgroundTasks):
    """ Gupshup webhook - ie. callbacks from gupshup are received here """
    try:
        data = await request.json()
        print("payload : ", data)

        # all non message-events, do nothing
        if (data.get("type", None) != "message"):
            return Response(status_code=200)
        payload = data['payload']
        sender = get_customer_config(customer_code)
        db = MongoDB(db_name=sender['db'])
        contact = payload['sender']['phone']
        cc = payload['sender']['country_code']

        # user has responded to a quick_reply
        if payload['type'] == 'quick_reply':
            info_logger.info("Processing quick_reply")
            gs_id = payload['context']['gsId']
            state_response = payload['payload']['text']
            cmpgnid = db.get_node({'_id': gs_id}, 'msgcampaigns').get(
                'campaign_id', None)
            build_flow(customer_code,  sender,
                       contact, cmpgnid, db, bgtask, state_response)

        # user has responded in text
        elif payload['type'] == 'text':
            info_logger.info("Processing text response")
            state_response = payload['payload']['text']
            state_response = state_response.lower()
            cmpg_node = db.get_node({'_id': contact}, 'usercampaigns')
            if cmpg_node is not None:
                cmpgnid = cmpg_node['lastcmpgnid']

            if is_greeting(state_response):
                experience_id = generate_experience_id(contact)
                localtz = tz.gettz('Asia/Kolkata')
                dt = str(datetime.now(localtz).isoformat()).split("T")
                d = dt[0]
                t = ":".join(dt[1].split(":", maxsplit=2)[:2])
                ct = contact
                trigger_event(Event.BEGIN, experience_id, '4')
                bgtask.add_task(schedule_task, "beckn", state_response, d, t, ct, {
                }, None, None, sender['db'], customer_code)
                return Response(status_code=200)

            cust_key = f'{contact}_{cmpgnid}'
            build_flow(customer_code, sender,
                       contact, cmpgnid, db, bgtask, state_response)

        # user has entered a location data
        elif payload['type'] == 'location':
            info_logger.info("Processing location response")
            latitude = payload['payload']['latitude']
            longitude = payload['payload']['longitude']
            cmpgnid = db.get_node({'_id': contact}, 'usercampaigns')[
                'lastcmpgnid']
            build_flow(customer_code, sender,
                       contact, cmpgnid, db, bgtask, latitude=latitude, longitude=longitude)

        # user has responded to a button message
        elif payload['type'] == 'button_reply':
            info_logger.info("Processing button reply")
            gs_id = payload['context']['gsId']
            state_response = payload['payload']['title']
            btn_reply_state = payload['payload']['id']
            user_option = payload['payload']['reply'].split(" ")[-1]
            cmpgnid = db.get_node({'_id': gs_id}, 'msgcampaigns').get(
                'campaign_id', None)
            build_flow(customer_code, sender, contact,
                       cmpgnid, db, bgtask, state_response, user_option, btn_reply_state)

        # user has responded to a list message
        elif payload['type'] == 'list_reply':
            info_logger.info("Processing list reply")
            gs_id = payload['context']['gsId']
            cmpgnid = db.get_node({'_id': gs_id}, 'msgcampaigns').get(
                'campaign_id', None)
            cust_key = f"{payload['source']}_{cmpgnid}"
            select_list_val = payload['payload']['postbackText']
            build_flow(customer_code, sender, contact,
                       cmpgnid, db, bgtask, select_list_val)

        return Response(status_code=200)

    except FlowFileError as e:
        err_logger.error(f"File Not found {e.args[0]}")
        return Response(status_code=200)
    except KeyError as ke:
        err_logger.error(f'Key error in webhook : {ke}')
        if ke.args[0] == 'END':
            info_logger.info("Terminal state reached")
        return Response(status_code=200)
    except Exception as e:
        err_logger.error("Exception in webhook", exc_info=True)
        return Response(status_code=200)
