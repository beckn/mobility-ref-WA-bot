from datetime import datetime
from urllib.parse import quote

import googlemaps
import requests

from utils.fileutils import FileUtils

maps = FileUtils.get_config('config.yaml', 'maps')
apikey = maps['apikey']


def get_image_url_for_lat_long(pickup_lat_long, drop_lat_long):
    gmaps = googlemaps.Client(key=apikey)

    # Request directions via public transit
    now = datetime.now()
    directions = gmaps.directions(
        pickup_lat_long, drop_lat_long, mode="driving", departure_time=now)
    print('Directions error:', directions)
    url_str = directions[0].get('overview_polyline').get('points')

    url_str = quote(url_str)
    url = "https://maps.googleapis.com/maps/api/staticmap?size=300x300&key=AIzaSyDj_jBuujsEk8mkIva0xG6_H73oJEytXEA&path=enc:" + url_str
    print(f"url : {url}")
    return(url)




def get_mapped_address_from_lat_long(lat, long):

    url = "https://maps.googleapis.com/maps/api/geocode/json"

    params = {
        "latlng": f"{lat},{long}",
        "key": apikey 
    }

    headers = {}
    response = requests.request("GET", url, headers=headers, params=params)
    response_json = response.json()
    add_dict = {
        "locality": "",
        "pin": "",
        "formatted_address": ""
    }

    elements_found = 0
    try:
        response_json = response_json["results"][0]
        add_dict["formatted_address"] = response_json["formatted_address"]
        for each in response_json["address_components"]:
            if elements_found == 2:
                break
            if "postal_code" in each["types"]:
                add_dict["pin"] = each["long_name"]
                elements_found = elements_found + 1
            if "sublocality" in each["types"]:
                add_dict["locality"] = each["long_name"]
                elements_found = elements_found + 1
        return(add_dict)
    except Exception as e:
        return None

