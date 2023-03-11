import ast
import time

import requests

from beckn.becknbox import Beckn
from beckn.events import Event, read_experience_id, trigger_event
from runner.methods import get_customer_config
from utils.maputils import (get_image_url_for_lat_long,
                            get_mapped_address_from_lat_long)
from utils.rediscache import Redis

from .format import (prepare_item_list, prepare_item_list_cancel,
                     prepare_item_list_pay)


class FlowHandler:

    @staticmethod
    def get_start_address(receiver, campaign_id, db):

        data = db.get_node(
            {'_id': f"{receiver}_{campaign_id}"}, 'transactions')

        lat = data["start"].split('_')[0]
        long = data["start"].split('_')[1]

        exp_id = read_experience_id(receiver)
        trigger_event(Event.ENTER_PICKUP_LOC, exp_id, '4')
        add_dict = get_mapped_address_from_lat_long(lat, long)
        if add_dict:
            Redis.update(f'{receiver}_{campaign_id}',
                         "pickup_location", add_dict["formatted_address"])
            Redis.update(f'{receiver}_{campaign_id}',
                         "pickup_locality", add_dict["locality"])
            Redis.update(f'{receiver}_{campaign_id}',
                         "pickup_pin", add_dict["pin"])
            Redis.update(f'{receiver}_{campaign_id}',
                         "pickup_gps", f"{lat},{long}")
            if Redis.read(f'{receiver}_{campaign_id}', 'language') == 'English':
                return f'Your pickup spot is: \n *{add_dict["formatted_address"]}*'
            else:
                return f'आपका पिकअप स्थान है: \n *{add_dict["formatted_address"]}*'
        else:
            return 'LocationErrorStart'

    def get_name(receiver, campaign_id, db):

        data = db.get_node(
            {'_id': f"{receiver}_{campaign_id}"}, 'transactions')

        return data['customer_name']

    @staticmethod
    def get_destination_address(receiver, campaign_id, db):

        data = db.get_node(
            {'_id': f"{receiver}_{campaign_id}"}, 'transactions')

        lat = data["end"].split('_')[0]
        long = data["end"].split('_')[1]
        exp_id = read_experience_id(receiver)
        trigger_event(Event.ENTER_DROP_LOC, exp_id, '4')
        add_dict = get_mapped_address_from_lat_long(lat, long)
        if add_dict:
            Redis.update(f'{receiver}_{campaign_id}',
                         "drop_location", add_dict["formatted_address"])
            Redis.update(f'{receiver}_{campaign_id}',
                         "drop_locality", add_dict["locality"])
            Redis.update(f'{receiver}_{campaign_id}',
                         "drop_pin", add_dict["pin"])
            Redis.update(f'{receiver}_{campaign_id}',
                         "drop_gps", f"{lat},{long}")
            if Redis.read(f'{receiver}_{campaign_id}', 'language') == 'English':
                return f'Your drop off spot is: \n *{add_dict["formatted_address"]}*'
            else:
                return f'आपका ड्रॉप ऑफ़ स्पॉट है: \n *{add_dict["formatted_address"]}*'
        else:
            return 'LocationErrorEnd'

    @staticmethod
    def bap_search(receiver, campaign_id, db):
        try:
            key = f'{receiver}_{campaign_id}'
            bobj = Beckn(key)

            # trigger_yatri_search and return list results:
            msg_id = bobj.search(Redis.read(
                key, 'pickup_gps'), Redis.read(key, 'drop_gps'))

            items = beckn_poll(bobj, 'search', msg_id, receiver, campaign_id)
            Redis.update(f'{receiver}_{campaign_id}',
                         "ride_list", f"{items}")

            if not items:
                print('item error')
                return 'IssueError'

            data = {
                "list_msg_title": " ",
                "list_msg_body": "Tap the button to see your ride options",
                "global_button_title": "Ride Options",
                "items":  prepare_item_list(items, key)
            }
            if Redis.read(key, 'language') != 'English':
                data['list_msg_body'] = 'राइड विकल्प देखने के लिए बटन पर टैप करें'
            return data
        except Exception as e:
            return 'Error'

    @staticmethod
    def bap_select(receiver, campaign_id, db):
        try:
            key = f'{receiver}_{campaign_id}'
            bobj = Beckn(key)

            # trigger_yatri_select and return list results:
            selected_item_id = Redis.read(key, "selected_item_id")
            print(f"Key {key}, {selected_item_id}")
            print("***********************************")
            print(Redis.read(key))
            item = Redis.read(key, "beckn").get(
                "items", {}).get(selected_item_id, None)

            print(f"Item details sent to bap select {item}")
            if item:
                msg_id = bobj.select(item)
                resp = beckn_poll(bobj, 'select', msg_id,
                                  receiver, campaign_id)
                if not resp:
                    return 'IssueError'
                price = round(float(resp['price']), 2)
                # "https://gfmarketing.s3.ap-south-1.amazonaws.com/whatsapp/sample_map.jpg"
                url = get_image_url_for_lat_long(Redis.read(
                    key, "pickup_gps"), Redis.read(key, "drop_gps"))
                if Redis.read(key, 'language') == 'English':
                    review_str = "\nReview your trip ...\n\n"
                    pickupstr = f'*Pick up:-* 📍 {Redis.read(key,"pickup_location")}\n\n'
                    dropstr = f'*Drop off:-* 📍 {Redis.read(key,"drop_location")}\n\n'
                    vehiclestr = f'*Vehicle Type:* {item["tags"]["VehicleType"]}\n*Fare:* {price}\n*ETA:* 5 min'
                    msg = f'{url}|{review_str}{pickupstr}{dropstr}{vehiclestr}'
                else:
                    review_str = "\nअपनी यात्रा की समीक्षा करें...\n\n"
                    pickupstr = f'* पिक अप: -* 📍 {Redis.read(key, "pickup_location")}\n\n'
                    dropstr = f'*ड्रॉप स्थान:-* 📍 {Redis.read(key,"drop_location")}\n\n'
                    vehiclestr = f'* वाहन का प्रकार: * {item["tags"]["VehicleType"]}\n*किराया: * {price}\n*ETA: * 5 मिनट'
                    msg = f'{url}|{review_str}{pickupstr}{dropstr}{vehiclestr}'
                return msg
        except Exception as e:
            return 'IssueError'

    @staticmethod
    def bap_pay(receiver, campaign_id, db):
        try:
            key = f'{receiver}_{campaign_id}'
            bobj = Beckn(key)

            # trigger_yatri_search and return list results:
            data = {
                "list_msg_title": " ",
                "list_msg_body": "Tap the button to modes of payment",
                "global_button_title": "Payment Options",
                "items":  prepare_item_list_pay(key)
            }
            if Redis.read(key, 'language') != 'English':
                data['list_msg_body'] = 'भुगतान के लिए बटन पर टैप करें'
            return data
        except Exception as e:
            return 'Error'

    @staticmethod
    def bap_cancel(receiver, campaign_id, db):
        try:
            key = f'{receiver}_{campaign_id}'
            # trigger_yatri_search and return list results:
            data = {
                "list_msg_title": " ",
                "list_msg_body": "Tap to choose cancellation reason",
                "global_button_title": "Reasons",
                "items":  prepare_item_list_cancel(key)
            }
            if Redis.read(key, 'language') != 'English':
                data['list_msg_body'] = 'रद्द करने का कारण चुनने के लिए टैप करें'
            return data
        except Exception as e:
            return 'Error'

    @staticmethod
    def bap_support(receiver, campaign_id, db):
        try:
            key = f'{receiver}_{campaign_id}'
            bobj = Beckn(key)
            resp = bobj.support()
            return resp
        except Exception as e:
            return 'Error'

    @staticmethod
    def bap_init(receiver, campaign_id, db):
        try:
            # time.sleep(5)
            key = f'{receiver}_{campaign_id}'
            bobj = Beckn(key)

            billing_info = {
                'door': '',
                'country': 'IND',
                'city': 'Bangalore',
                'area_code': Redis.read(key, "pickup_pin"),
                'state': 'Karnataka',
                'building': 'Building',
                'name': Redis.read(key, "customer_name"),
                'locality': Redis.read(key, "pickup_locality"),
                'phone': receiver,
                'email': f'{Redis.read(key, "customer_name")}@mail.com'
            }
            # building is mandatory.
            delivery_info = {
                'door': '',
                'country': 'IND',
                'city': 'Bangalore',
                'area_code': Redis.read(key, "drop_pin"),
                'state': 'Karnataka',
                'building': 'Building',
                'name': Redis.read(key, "customer_name"),
                'locality': Redis.read(key, "drop_locality"),
                'phone': receiver,

                'email': f'{Redis.read(key, "customer_name")}@mail.com',
                'drop_gps': Redis.read(key, 'drop_gps'),
                'street': 'Bangalore'
            }

            # trigger_yatri_init and return list results:
            selected_item_id = Redis.read(key, "selected_item_id")
            msg_id = bobj.init(selected_item_id, billing_info, delivery_info)
            init_resp = beckn_poll(bobj, 'init', msg_id, receiver, campaign_id)
            print('init_resp:', init_resp)
            if not init_resp:
                return 'IssueError'

            if Redis.read(key, 'language') == 'English':

                return 'We are processing your request, kindly wait!'
            else:
                return 'हम आपके अनुरोध पर कार्रवाई कर रहे हैं, कृपया प्रतीक्षा करें!'

        except Exception as e:
            return 'Error'

    @staticmethod
    def list_ride(receiver, campaign_id, db):
        try:
            key = f'{receiver}_{campaign_id}'
            bobj = Beckn(key)
            items = Redis.read(key, 'ride_list')
            items = ast.literal_eval(items)

            # trigger_yatri_search and return list results:

            data = {
                "list_msg_title": " ",
                "list_msg_body": "Tap the button to see your ride options",
                "global_button_title": "Ride Options",
                "items":  prepare_item_list(items, key)
            }
            if Redis.read(key, 'language') != 'English':
                data['list_msg_body'] = 'राइड विकल्प देखने के लिए बटन पर टैप करें'
            return data
        except Exception as e:
            return 'Error'

    @staticmethod
    def bap_confirm(receiver, campaign_id, db):
        try:
            # time.sleep(5)
            key = f'{receiver}_{campaign_id}'
            bobj = Beckn(key)

            billing_info = {
                'door': '',
                'country': 'IND',
                'city': 'Bangalore',
                'area_code': Redis.read(key, "pickup_pin"),
                'state': 'Karnataka',
                'building': 'Building',
                'name': Redis.read(key, "customer_name"),
                'locality': Redis.read(key, "pickup_locality"),
                'phone': receiver,
                'email': f'{Redis.read(key, "customer_name")}@mail.com'
            }
            # building is mandatory.
            delivery_info = {
                'door': '',
                'country': 'IND',
                'city': 'Bangalore',
                'area_code': Redis.read(key, "drop_pin"),
                'state': 'Karnataka',
                'building': 'Building',
                'name': Redis.read(key, "customer_name"),
                'locality': Redis.read(key, "drop_locality"),
                'phone': receiver,

                'email': f'{Redis.read(key, "customer_name")}@mail.com',
                'drop_gps': Redis.read(key, 'drop_gps'),
                'street': 'Bangalore'
            }

            # trigger_yatri_init and return list results:
            selected_item_id = Redis.read(key, "selected_item_id")
            msg_id = bobj.confirm(
                selected_item_id, billing_info, delivery_info)

            conf_resp = beckn_poll(
                bobj, 'confirm', msg_id, receiver, campaign_id)

            if not conf_resp:
                return 'IssueError'
            print('init_resp:', conf_resp)

            arrival_time = "2 min"
            vehicle_detail = f"{conf_resp['vehicle_number']}"
            driver_name = conf_resp.get('agent_name', '')
            phone = conf_resp.get('agent_phone', '')

            tripconfmstr = f"{conf_resp['state']}"
            if Redis.read(key, 'language') == "English":
                tripdetails = f"{tripconfmstr}\nArriving in:{arrival_time} minutes\nVehicle Details: {vehicle_detail}\nDriver: {driver_name}\nPh No: {phone}"
            else:
                tripdetails = f"{tripconfmstr}\nआगामी: {arrival_time} मिनट\nवाहन विवरण: {vehicle_detail}\nचालक: {driver_name}\nफ़ोन नंबर: {phone}"

            return tripdetails

        except Exception as e:
            return 'IssueError'


def beckn_poll(bobj: Beckn, action, msg_id, receiver, campaign_id):
    resp = None
    for i in range(3):
        time.sleep(5)
        resp = bobj.poll(action, msg_id)
        key = f'{receiver}_{campaign_id}'
        if resp:
            break
        else:
            # from runner.methods import get_customer_config
            sender = get_customer_config('ondc')
            apikey = sender['apikey']
            headers = {
                'apikey': apikey,
                'Content-Type': 'application/x-www-form-urlencoded',
            }
            post_url = 'https://api.gupshup.io/sm/api/v1/msg'
            if Redis.read(key, 'language') == 'English':

                data = {
                    'channel': 'whatsapp',
                    'source': sender['source'],
                    'destination': receiver,
                    'message': 'Processing your request',
                    'src.name': sender['appname']
                }
            else:
                data = {
                    'channel': 'whatsapp',
                    'source': sender['source'],
                    'destination': receiver,
                    'message': 'हम आपके निवेदन पर कार्यवाही कर रहे हैं',
                    'src.name': sender['appname']
                }

            response = requests.post(
                post_url, headers=headers, data=data)
            resp_data = response.json()
            print(resp_data)
    return resp
