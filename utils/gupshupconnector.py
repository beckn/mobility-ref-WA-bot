import json
import re
import traceback
from time import sleep

import requests

from customer.config import constants
from FalconUtils.mongo.mongoutils import MongoDB
from logger.logger import BotLogger
from utils import resource
from utils.fileutils import FileUtils
from utils.model import *

mongodb = FileUtils.get_config('config.yaml', 'mongodb')

info_logger = BotLogger.logger('infoLogger')
err_logger = BotLogger.logger('errorLogger')


MongoDB.mongodb_connect(host=mongodb['host'],
                        port=mongodb['port'], password=mongodb['password'], user=mongodb['user'])


def prepare_list_body(list_msg_title, list_msg_body, button_title, items):
    """Prepares body for sending List message"""

    list_json = ListModel(type="list", title=list_msg_title, body=list_msg_body,
                          globalButtons=[GlobalButton(
                              type="text", title=button_title)],
                          items=items).dict()
    return list_json


def replace_format_characters(msg, db, campaign_id, receiver):
    fmt_list = re.findall(r'{(.*?)}', msg)
    if not fmt_list:
        return msg
    else:
        _id = f'{receiver}_{campaign_id}'
        custdata = db.get_node({'_id': _id}, "transactions")
        for each in fmt_list:
            try:
                each_val = custdata[each]
            except KeyError:
                each_val = each
            msg = msg.replace(f"{{{each}}}", each_val.title())
            print("Modified message is ", msg)
            return msg


def count_words_at_url(url):
    """Just an example function that's called async."""
    resp = requests.get(url)
    return len(resp.text.split())


def create_items_payload(items, provider_name):
    """Create payload in the required format for displaying items in the List message """
    item_template = {
        "title": "",
        "subtitle": "dummy",
        "options": [
            {
                "type": "text",
                "title": "",
                "description": "",
                "postbackText": "Test Postback"
            }
        ]
    }
    item_template["title"] = provider_name
    description_str = ""
    count = 1
    order_total = 0
    for each in items:
        item_str = str(count) + each['item_name'] + " " + str(each['weight']) + \
            each['weight_unit'] + " - " + \
            str(each['selling_price']) + each['currency_type']
        count = count + 1
        order_total = str(order_total) + str(each['selling_price'])
        description_str = description_str + item_str + '\n'

    description_str = description_str[:-1]
    print("Description str is", description_str)
    item_template["options"][0]['description'] = description_str
    item_template['options'][0]['title'] = 'Order Total :' + str(order_total)
    print("Returning item_temlplate:", item_template)

    return item_template


def post_to_gupshup(lang, custdata, receiver, params, campaign_id, prev_state, current_state, flow_name=None):
    """ Posts the data to gupshup to send to a given contact. Given the type of message and required details 
    for the message.Triggers the message sending to the required contacts."""
    try:
        db_name = custdata['db']
        apikey = custdata['apikey']
        appname = custdata['appname']
        custcode = custdata['customer_code']
        db = MongoDB(db_name=db_name)

        # Form the json header
        headers = {
            'apikey': apikey,
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        post_url = 'https://api.gupshup.io/sm/api/v1/msg'

        # Form json body for template message
        if(params['reply'] == constants.TEMPLATE):
            print(
                f"creating the gupsup template message for template_id: {params['template_id']}")
            post_url = "http://api.gupshup.io/sm/api/v1/template/msg"
            if(params['template_type'] == "TEXT"):
                template_str = {
                    "id": params["template_id"],
                    "params": []
                }
                data = {
                    'source': custdata['source'],
                    'destination': receiver,
                    'template': json.dumps(template_str)
                }
            else:
                template_str = {
                    "id": params["template_id"],
                    "params": [params["name"]]
                }

                message_str = {
                    "type": "image",
                    "image": {"link": params["imageurl"]}
                }

                data = {
                    'source': custdata['source'],
                    'destination': receiver,
                    'template': json.dumps(template_str),
                    'message': json.dumps(message_str)
                }

        # Form json body for TEXT message
        elif(params['reply'] == constants.TEXT):
            msg = ''
            if params['message']:
                flow = params['message'].split('_', maxsplit=1)[0]
                message_key = params['message'].split('_', maxsplit=1)[1]
                if message_key == "TXT_1":
                    sleep(15)
                if message_key == "TXT_6":
                    sleep(2)

                print(f"TEXT : flow: {flow}, message key: {message_key}")
                msg = resource.get_resource_string(
                    custcode, flow, message_key, lang)
                msg = replace_format_characters(msg, db, campaign_id, receiver)
            if params.get('validator_value', None):
                msg = str(params['validator_value'])
            elif not msg:
                msg = str(params['handler_value'])
            else:
                msg = msg.format(str(params.get('handler_value', '')))

            data = {
                'channel': 'whatsapp',
                'source': custdata['source'],
                'destination': receiver,
                'message': '{"type":"text","text": "' + msg + '"}',
                'src.name': custdata['appname']
            }
            if params['message'] == "HI_TXT_22":
                data = {
                    'channel': 'whatsapp',
                    'source': custdata['source'],
                    'destination': receiver,
                    'message': f'{msg}',
                    'src.name': custdata['appname']
                }

        # Form json body for Button message
        elif(params['reply'] == constants.BUTTON):
            msg = ''
            flow = ''
            if params['message']:
                flow = params['message'].split('_', maxsplit=1)[0]
                message_key = params['message'].split('_', maxsplit=1)[1]
                print(f"BUTTON flow: {flow}, message key: {message_key}")
                msg = resource.get_resource_string(
                    custcode, flow, message_key, lang)
                msg = replace_format_characters(msg, db, campaign_id, receiver)

            if params.get('validator_value', None):
                msg = str(params['validator_value'])

            if not msg:
                msg = str(params['handler_value'])
            else:
                msg = msg.format(str(params.get('handler_value', '')))

           # print(f"creating the gupsup message")

            button_key = params['buttons'].split('_', maxsplit=1)[1]
            flow = params['buttons'].split('_', maxsplit=1)[0]
            # print("button_key", button_key)
            button_names = resource.get_resource_string(
                custcode, flow, button_key, lang)

            print("Button sg is: ", msg)
            msg = replace_format_characters(msg, db, campaign_id, receiver)
            button_name_pattern = ""
            button_options_list = []
            for each in button_names:
                button_name_pattern = {
                    "type": "text",
                    "title": each
                }
                button_options_list.append(button_name_pattern)

            button_body = params.get("button_body", "text")
            message = {
                "msgid": current_state,
                "type": "quick_reply",
                "content": {
                    "type": button_body,
                    "text": msg,
                    "captions": "",
                },
                "options": button_options_list
            }

            url = ""
            if button_body.lower() == "image":
                button_body = 'image'
                url = params['handler_value'].split("|")[0]
                print(params['handler_value'])
                msg = params['handler_value'].split("|")[1]
                message["content"]["text"] = msg
                message["content"]["url"] = url

            data = {
                'channel': 'whatsapp',
                'source': custdata['source'],
                'destination': receiver,
                'message': json.dumps(message),
                'src.name': custdata['appname']
            }

        elif(params['reply'] == constants.LIST):
            payload = params['handler_value']
            json_template = prepare_list_body(
                payload["list_msg_title"], payload["list_msg_body"], payload["global_button_title"], payload["items"])
            string_template = json.dumps(json_template)

            data = {
                "channel": "whatsapp",
                'source': custdata['source'],
                'destination': receiver,
                'src.name': custdata['appname'],
                "message": string_template
            }
        # Form json body for IMAGE message
        else:
            print(f"Sending images to registered watsapp contact ")
            flow = params['message'].split('_', maxsplit=1)[0]
            message_key = params['message'].split('_', maxsplit=1)[1]
            msg = resource.get_resource_string(
                custcode, flow, message_key, lang)

            data = {
                'channel': 'whatsapp',
                'source': custdata['source'],
                'destination': receiver,
                'message': '{"type":"image","previewUrl":"' + params["image_url"] + '" , "originalUrl":"' + params["image_url"] + '","caption":"' + msg + '"}',
                'src.name': custdata['appname']
            }

        response = requests.post(post_url, headers=headers, data=data)
        resp_data = response.json()

        if params.get('template_type', None) == "TEXT":
            return
        transactions = {}
        state = {}
        state['msg'] = resp_data["messageId"]
        state['response'] = None
        _id = f'{receiver}_{campaign_id}'
        transactions['message_ids'] = {}
        transactions['message_ids'][current_state] = state
        transactions['prev_state'] = prev_state
        transactions['current_state'] = current_state

        if flow_name:
            transactions['_id'] = _id
            transactions['lang'] = lang
            transactions['flow'] = flow_name
            db.create_node("transactions", transactions)
        else:
            msg_ids = db.get_node({'_id': _id}, "transactions")['message_ids']
            msg_ids[current_state] = state
            transactions['message_ids'] = msg_ids
            db.update_node(transactions, {'_id': _id}, 'transactions')

        # Update appropriate collections in DB with details.
        # This helps in tracking state and the flow for a given contact.

        if not (db.update_node({"lastcmpgnid": campaign_id}, {"_id": receiver}, "usercampaigns")):
            db.create_node("usercampaigns", {
                           "_id": receiver, "lastcmpgnid": campaign_id})
        db.create_node("msgcampaigns", {
                       "_id": resp_data["messageId"], "campaign_id": campaign_id})
        return(response)
    except Exception as e:
        print(traceback.print_exc())
