from geopy.geocoders import Nominatim
from pprint import pprint
import traceback




def build_whatsapp_reply_data(option_list, contact):
    print('creating whatsapp response json for list reply')
    whatsapp_resp = {
        'modes': []
    }
    
    whatsapp_resp['modes'].append({
        "Auto": "2 min away| Rs 30"
    })
    whatsapp_resp['modes'].append({
        "Auto": "2 min away| Rs 60"
    })
    return whatsapp_resp



def build_whatsapp_reply_data_orig(data, contact):
    print('creating whatsapp response json for list reply')
    transaction_id = data['transaction_id']
    whatsapp_resp = {
        'providers': []
    }
    i = 1
    for provider in data['providers']:
        print(f"provider no {1}")
        pprint(provider)
        provider['transaction_id'] = transaction_id
        try:
            temp = {}
            if provider['provider_name'].__len__() > 20:
                raise ValueError()
            temp['provider_name'] = provider['provider_name'].split(
                "-")[0].title()
            items = []
            received_items = provider['items']
            for each in received_items:
                item_name = each['item_name'].split("-")[0].title()
                if item_name.__len__() > 20:
                    item_name = item_name[:20]
                    #raise ValueError()
                each['item_name'] = item_name
                items.append(each)
            temp['items'] = items
            temp['whatsapp_list_id'] = i
            i = i + 1
            whatsapp_resp['providers'].append(temp)
            print(whatsapp_resp)
        except Exception as e:
            print(traceback.print_exc())
    return whatsapp_resp



def get_details_from_gps(latitude, longitude):
    locator = Nominatim(user_agent="myapilocation")
    location = locator.reverse(f"{latitude}, {longitude}")
    return location.address, location.raw