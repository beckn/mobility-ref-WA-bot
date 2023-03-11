import requests
from logger.logger  import BotLogger

info_logger = BotLogger.logger('infoLogger')
err_logger = BotLogger.logger('errorLogger')


def opt_in_user(apikey, appname, contact):
    headers = {
        'apikey': apikey,
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    data = {
        'user': contact
    }

    post_url = 'https://api.gupshup.io/sm/api/v1/app/opt/in/'+ appname
    response = requests.post(post_url, headers=headers, data=data)
    return True