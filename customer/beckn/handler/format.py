
from utils.rediscache import Redis

'''Idea is to bring the required data to be displayed in the format
as specified in the template above.
item_data_template = [
        {
           "title" : "",
           "options": [
                {

                }
           ]

        }
]
'''

postback = []
item_data = [
    {
        'item_name': 'Premium Taxi',
        '_id': '3Ft',
        'id': './mobility/ind.blr/9@taxi.becknprotocol.io.item',
        'provider_id': './mobility/ind.blr/7@taxi.becknprotocol.io.provider',
        'fulfillment_id': './mobility/ind.blr/3983@taxi.becknprotocol.io.fulfillment',
        'code': 'Premium Taxi',
        'images': ['https://taxi.becknprotocol.io/resources/images/car.png'],
        'price': '113.71837687896075',
        'currency': 'INR',
        'category_id': './mobility/ind.blr/1@taxi.becknprotocol.io.category',
        'tags': 'Nexon'
    }
]


def prepare_item_list(item_data, key):
    item_data_template = [
        {
            "title": "",
            "options": [
                {

                }
            ]

        }
    ]

    options = []
    option_indx = 0
    for each in item_data:
        temp = {}
        temp["type"] = "text"
        temp["title"] = "Cab"
        temp["description"] = f'5 min away | Rs {round(float(each["price"]),2)}'
        temp["postbackText"] = each["_id"]
        postback.append(temp["postbackText"])
        options.append(temp)
    if Redis.read(key, 'language') == 'English':
        item_data_template[0]["title"] = "Tap to chose a ride"
    else:
        item_data_template[0]["title"] = "यात्रा  टैप करें"
    item_data_template[0]["options"] = options

    return item_data_template


def prepare_item_list_pay(key):
    item_data_template = [
        {
            "title": "",
            "options": [
                {

                }
            ]

        }
    ]

    options = []
    option_indx = 0
    for each in item_data:
        temp = {}
        temp["type"] = "text"
        temp["title"] = "Cash"
        temp["description"] = f''
        temp["postbackText"] = each["_id"]
        postback.append(temp["postbackText"])
        options.append(temp)
    if Redis.read(key, 'language') == 'English':

        item_data_template[0]["title"] = "Select mode of payment"
    else:
        item_data_template[0]["title"] = "भुगतान का तरीका "

    item_data_template[0]["options"] = options
    return item_data_template


def prepare_item_list_cancel(key):
    item_data_template = [
        {
            "title": "",
            "options": [
                {

                }
            ]

        }
    ]

    options = []
    option_indx = 0

    reasons = ['Plan changed', 'Booked by Mistake',
               'Unable to Contact the driver', 'Driver Denied']
    reasons = {
        1: 'Plan changed',
        2: 'Booked by Mistake',
        3: 'Driver Unreachable',
        4: 'Driver Denied'
    }

    for each in reasons:
        temp = {}
        temp["type"] = "text"

        temp["title"] = reasons[each]
        temp["postbackText"] = f'00{each}'

        temp["description"] = f''

        postback.append(temp["postbackText"])
        options.append(temp)
    if Redis.read(key, 'language') == 'English':

        item_data_template[0]["title"] = "Cancellation Reason"
    else:
        item_data_template[0]["title"] = "रद्द करने का कारण"

    item_data_template[0]["options"] = options
    return item_data_template
