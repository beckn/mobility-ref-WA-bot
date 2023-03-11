from typing import Any
from uuid import uuid4

from shortuuid import ShortUUID

from beckn.constants import BecknConstants as BC
from logger.logger import BotLogger
from utils.fileutils import FileUtils as fu
from utils.rediscache import Redis

info_logger = BotLogger.logger('infoLogger')
error_logger = BotLogger.logger('errorLogger')


def get_id(digits=3):
    s = ShortUUID()
    _id = s.random(digits)
    return _id


def filter_search_responses(search_resp, cache) -> dict:
    print("Collecting bpp onsearch responses")
    resp = None
    data = {
        'bpp': {},
        'providers': {},
        'categories': {},
        'items': {}
    }
    try:
        counter = 0
        for each in search_resp['message']['catalogs']:
            try:
                _id = get_id()

                # consolidate bpp detail
                bpp_id = each['bpp_id']
                bpp = {
                    f'{bpp_id} | {_id}': {
                        'bpp_id': bpp_id,
                        'bpp_name': each['bpp_descriptor']['name'],
                        'bpp_code': each['bpp_descriptor']['code'],
                        'bpp_uri': each['bpp_uri']
                    }
                }

                # consolidate provider detail
                provider = {}
                providers = each['bpp_providers']
                if not providers:
                    raise ValueError('providers not found')
                for p in providers:
                    temp = {}
                    pid = p['id']
                    temp['id'] = pid
                    temp['bpp_id'] = bpp_id
                    temp['name'] = p['descriptor']['name']
                    temp['images'] = p['descriptor']['images']
                    temp['location_id'] = p['locations'][0].get('id', "")
                    temp['gps'] = p['locations'][0].get('gps', "")
                    provider.update({
                        f'{pid} | {_id}': temp
                    })

                    # consolidate categories
                    category = {}
                    for cat in p.get('categories', []):
                        temp = {}
                        cid = cat['id']
                        temp['name'] = cat['descriptor']['name']
                        category.update({
                            f'{cid} | {_id}': temp
                        })

                    # consolidate items
                    items = p['items']
                    if not items:
                        info_logger.info("No Items received")
                        continue
                    for key, item in enumerate(items, start=counter):
                        _key = f'{key}{BC.KEY_MEDIATOR}{_id}'
                        t2 = {}
                        t2['name'] = item['descriptor']['name']
                        t2['_id'] = _key
                        t2['id'] = item['id']
                        t2['provider_id'] = pid
                        t2['fulfillment_id'] = item['fulfillment_id']
                        t2['code'] = item['descriptor']['code']
                        t2['images'] = item['descriptor']['images']
                        t2['price'] = item['price']['value']
                        t2['currency'] = item['price']['currency']
                        t2['category_id'] = item['category_id']
                        t2['tags'] = item.get('tags', {})
                        data['items'].update({_key: t2})
                    data['categories'].update(category)
                    data['providers'].update(provider)
                    data['bpp'].update(bpp)
            except Exception as e:
                error_logger.error(
                    "Exception raised while collecting the bpp search responses", exc_info=True)
    except Exception as e:
        print("Error to collect bpp responses in backnbox")
    cache.update(data)
    response = list(data['items'].values())
    return response


def filter_select_responses(select_response, cache):
    _id = cache['user_cart']['_id']
    cache['quotes'] = {}
    response = {}
    for each in select_response:
        bpp_id = each['context']['bpp_id']
        bpp_key = f'{bpp_id}{BC.KEY_MEDIATOR}{_id[-3:]}'
        quote = {}
        if bpp_key in cache['bpp']:
            q = each['message']['quote']
            provider_id = q['provider']['id']
            key = f'{provider_id}{BC.KEY_MEDIATOR}{_id[-3:]}'
            if key in cache['providers']:
                items = q['items']
                has_invalid_item = False
                for item in items:
                    item_id = item['id']
                    if item_id in cache['user_cart']['items']:
                        if q['quote']['price']['value'] != cache['items'][_id]['price']:
                            info_logger.info(f"Quote mismatch for {item_id}")
                            has_invalid_item = True
                else:
                    if has_invalid_item:
                        continue
                    else:
                        quote['provider_id'] = provider_id
                        quote['price'] = q['quote']['price']['value']
                        breakup = []
                        for b in q['quote']['breakup']:
                            t = {
                                'title': b['title'],
                                'price': b['price']['value']
                            }
                            breakup.append(t)
                        quote['break_up'] = breakup
                        response = quote
        cache['quotes'][bpp_key] = quote
    return response


def filter_init_responses(init_resp, cache):
    response = {}
    for each in init_resp:
        if each['context']['transaction_id'] != cache['transaction_id']:
            continue
        fulfilment = each['message']['order']['fulfillment']
        ref_id = f'ref_{get_id(digits=5)}'
        response = {
            'bpp_id': each['context']['bpp_id'],
            'bpp_uri': each['context']['bpp_uri'],
            'id': each['message']['order'].get('id'),
            'state': each['message']['order'].get('state'),
            'agent_name': fulfilment.get('agent', {}).get('name', ''),
            'vehicle_number': fulfilment.get('vehicle', {}).get('registration', ''),
            'ref_id': ref_id
        }
    cache['orders'] = response
    return response


def filter_confirm_responses(confirm_resp, cache):
    response = {}
    for each in confirm_resp:
        if each['context']['transaction_id'] != cache['transaction_id']:
            continue
        fulfilment = each['message']['order']['fulfillment']
        response = {
            'id': each['message']['order'].get('id'),
            'state': each['message']['order'].get('state'),
            'agent_name': fulfilment.get('agent', {}).get('name', ''),
            'vehicle_number': fulfilment.get('vehicle', {}).get('registration', ''),
            'parent_order_id': each.get('parent_order_id', '')
        }
    cache['orders'].update(response)
    return response


def filter_status_responses(status_resp, cache: dict):
    response = {}
    for each in status_resp:
        if 'message' not in each:
            continue
        fulfilment = each['message']['order']['fulfillment']
        print("Creating the status Response")
        state = each['message']['order'].get('state', cache['orders']['state'])
        cache['orders']['state'] = state
        response = {
            'id': each['message']['order'].get('id'),
            'state': state,
            'agent_name': fulfilment.get('agent', {}).get('name', ''),
            'vehicle_number': fulfilment.get('vehicle', {}).get('registration', ''),
            'parent_order_id': each.get('parent_order_id', cache['orders']['parent_order_id'])
        }
    return response


def filter_track_responses(track_resp, cache: dict):
    response = {}
    for each in track_resp:
        if 'message' not in each:
            continue
        response = {
            'track_url': each['message']['tracking']['url'],
            'track_url_state': each['message']['tracking']['status']
        }
        cache.update(response)
    return response


def filter_cancel_responses(cancel_resp, cache):
    response = None
    try:
        if 'message' in cancel_resp:
            state = cancel_resp['message']['order']['state']
            if state.lower() == 'canceled':
                cache['orders']['state'] = state
                response = state.lower()
    except Exception as e:
        error_logger.error('Error to filter cancel response:', exc_info=True)
    return response


def filter_support_responses(support_resp, cache):
    response = False
    try:
        if isinstance(support_resp, list):
            for each in support_resp:
                if 'message' not in each: 
                    continue
                else:
                    response = True
        else:
            if 'message' in support_resp:
                response = True
    except Exception as e:
        error_logger.error('Error to filter cancel response:', exc_info=True)
    return response


def get_config(field=None) -> Any:
    data = fu.get_config('beckn/config.yaml', field)
    return data

def write_cache(key, data):
    cache_data = Redis.read(key)
    cache_data['beckn'] = data
    Redis.update(key, cache_data)


# Quote

class BecknPayloads:
    key_mediator = BC.KEY_MEDIATOR

    def __init__(self, session_id, cache) -> None:
        self.session_id = session_id
        self.cache = cache

    def search_payload(self, pickup_location, drop_location) -> dict:
        payload = {
            "context": {
                "transaction_id": f"{str(uuid4())}.{self.session_id}"
            },
            "message": {
                "criteria": {
                    "pickup_location": pickup_location,
                    "drop_location": drop_location
                }
            }
        }
        return payload

    def select_payload(self, item):
        payloads = []
        item_id = item['id']
        key = item['_id']
        self.cache['user_cart'] = {'_id': key, 'items': [item_id]}
        item = self.cache['items'][key]
        key = f"{item['provider_id']}{self.key_mediator}{key[-3:]}"
        provider = self.cache['providers'][key]
        key = f"{provider['bpp_id']}{self.key_mediator}{key[-3:]}"
        bpp = self.cache['bpp'][key]
        payload = {
            'context': {
                'transaction_id': self.cache['transaction_id'],
                'bpp_id': bpp['bpp_id'],
                'bpp_uri': bpp['bpp_uri']
            },
            'message': {
                "cart": {
                    "items": [
                        {
                            "id": item['id'],
                            "fulfillment_id": item['fulfillment_id'],
                            "descriptor": {
                                "name": item['name'],
                                "code": item['code']
                            },
                            "price": {
                                "currency": item['currency'],
                                "value": item['price']
                            },
                            "category_id": item['category_id'],
                            "tags": item['tags']
                        }
                    ]
                }
            }
        }
        payloads.append(payload)
        return payloads

    def init_payload(self, item_ids, billing_details, delivery_details):
        payloads = []
        key = item_ids
        item = self.cache['items'][key]
        key = f"{item['provider_id']}{self.key_mediator}{key[-3:]}"
        provider = self.cache['providers'][key]
        key = f"{provider['bpp_id']}{self.key_mediator}{key[-3:]}"
        bpp = self.cache['bpp'][key]
        context = {
            'transaction_id': f"{self.cache['transaction_id']}",
            'bpp_id': bpp['bpp_id'],
            'bpp_uri': bpp['bpp_uri']
        }
        message = {
            "items": [
                {
                    "id": item['id'],
                    "bpp_id": bpp['bpp_id'],
                    "fulfillment_id": item['fulfillment_id'],
                    "descriptor": {
                        "name": item['name'],
                        "code": item['code']
                    },
                    "price": {
                        "currency": item['currency'],
                        "value": item['price']
                    },
                    "category_id": item['category_id'],
                    "tags": item['tags'],
                    'provider': {
                        'id': provider['id'],
                        'locations': [
                            provider['location_id']
                        ]
                    }
                }
            ],
            'billing_info': {
                "address": {
                    "door": billing_details['door'],
                    "country": billing_details['country'],
                    "city": billing_details['city'],
                    "area_code": billing_details['area_code'],
                    "state": billing_details['state'],
                    "building": billing_details['building'],
                    "name": billing_details['name'],
                    "locality": billing_details['locality'],
                },
                "phone": billing_details['phone'],
                "name": billing_details['name'],
                "email": billing_details['email'],
            },
            'delivery_info': {
                "type": "HOME-DELIVERY",
                "name": delivery_details['name'],
                "phone": delivery_details['phone'],
                "email": delivery_details['email'],
                "location": {
                    "address": {
                        "name": delivery_details['name'],
                        "locality": delivery_details['locality'],
                        "door": delivery_details['door'],
                        "country": delivery_details['country'],
                        "city": delivery_details['city'],
                        "street": delivery_details['street'],
                        "area_code": delivery_details['area_code'],
                        "state": delivery_details['state'],
                        "building": delivery_details['building'],
                    },
                    "gps": delivery_details['drop_gps'],
                }
            }
        }
        payload = {
            'context': context,
            'message': message
        }
        payloads.append(payload)
        return payloads

    def confirm_payload(self, item_ids, billing_details, delivery_details):
        payloads = []
        key = item_ids
        item = self.cache['items'][key]
        key = f"{item['provider_id']}{self.key_mediator}{key[-3:]}"
        provider = self.cache['providers'][key]
        key = f"{provider['bpp_id']}{self.key_mediator}{key[-3:]}"
        bpp = self.cache['bpp'][key]
        context = {
            'transaction_id': f"{self.cache['transaction_id']}",
            'bpp_id': bpp['bpp_id'],
            'bpp_uri': bpp['bpp_uri']
        }
        message = {
            "items": [
                {
                    "id": item['id'],
                    "bpp_id": bpp['bpp_id'],
                    "fulfillment_id": item['fulfillment_id'],
                    "descriptor": {
                        "name": item['name'],
                        "code": item['code']
                    },
                    "price": {
                        "currency": item['currency'],
                        "value": item['price']
                    },
                    "category_id": item['category_id'],
                    "tags": item['tags'],
                    'provider': {
                        'id': provider['id'],
                        'locations': [
                            provider['location_id']
                        ]
                    },
                    'quantity': {
                        'count': 1
                    }
                }
            ],
            'billing_info': {
                "address": {
                    "door": billing_details['door'],
                    "country": billing_details['country'],
                    "city": billing_details['city'],
                    "area_code": billing_details['area_code'],
                    "state": billing_details['state'],
                    "building": billing_details['building'],
                    "name": billing_details['name'],
                    "locality": billing_details['locality'],
                },
                "phone": billing_details['phone'],
                "name": billing_details['name'],
                "email": billing_details['email'],
            },
            'delivery_info': {
                "type": "HOME-DELIVERY",
                "name": delivery_details['name'],
                "phone": delivery_details['phone'],
                "email": delivery_details['email'],
                "location": {
                    "address": {
                        "name": delivery_details['name'],
                        "locality": delivery_details['locality'],
                        "door": delivery_details['door'],
                        "country": delivery_details['country'],
                        "city": delivery_details['city'],
                        "street": delivery_details['street'],
                        "area_code": delivery_details['area_code'],
                        "state": delivery_details['state'],
                        "building": delivery_details['building'],
                    },
                    "gps": delivery_details['drop_gps'],
                }
            },
            'payment': {
                'paid_amount': item['price'],
                'currency': 'INR',
                'status': 'PAID',
                'transaction_id': str(uuid4())
            }
        }
        payload = {
            'context': context,
            'message': message
        }
        payloads.append(payload)
        return payloads

    def status_payload(self):
        payloads = []
        context = {
            'transaction_id': f"{self.cache['transaction_id']}",
            'bpp_id': self.cache['orders']['bpp_id'],
            'bpp_uri': self.cache['orders']['bpp_uri']
        }
        message = {
            'order_id': self.cache['orders']['id']
        }
        payload = {
            'context': context,
            'message': message
        }
        payloads.append(payload)
        return payloads

    def cancel_payload(self, cancel_reason_code):
        data = {
            "context": {
                'transaction_id': f"{self.cache['transaction_id']}",
                'bpp_id': self.cache['orders']['bpp_id'],
                'bpp_uri': self.cache['orders']['bpp_uri']
            },
            "message": {
                "order_id": self.cache['orders']['id'],
                "cancellation_reason_id": cancel_reason_code
            }
        }
        return data

    def track_payload(self):
        data = [
            {
                "context": {
                    'transaction_id': f"{self.cache['transaction_id']}",
                    'bpp_id': self.cache['orders']['bpp_id'],
                    'bpp_uri': self.cache['orders']['bpp_uri']
                },
                "message": {
                    "order_id": self.cache['orders']['id']
                }
            }
        ]
        return data

    def support_payload(self):
        data = [
            {
                "context": {
                    'transaction_id': f"{self.cache['transaction_id']}",
                    'bpp_id': self.cache['orders']['bpp_id'],
                    'bpp_uri': self.cache['orders']['bpp_uri']
                },
                "message": {
                    "uri": self.cache['orders'].get('track_url', ''),
                    "ref_id": self.cache['orders']['ref_id']
                }
            }
        ]

        return data
