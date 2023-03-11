import json
from datetime import datetime
from pathlib import Path

import pytz

from FalconUtils.mongo.mongoutils import MongoDB
from logger.logger import BotLogger
from utils.gupshupconnector import post_to_gupshup
from utils.gupshuphelper import opt_in_user

info_logger = BotLogger.logger('infoLogger')
err_logger = BotLogger.logger('errorLogger')


def schedule_task(flow_name, message, job_date, job_time, contact, images, user_name, user_email, db_name, customer_code=None):
    """Schedules a task . flow_name, describes the flow to be triggered
    which is set in dashboard.py . Entry is made in MongoDB that a flow is triggered and 
    the first state of the flow is sent to post_to_gupshup() for triggering.
    """
    try:
        # Get sender details from config file customer/<custcode>/<custcode>.json
        info_logger.info(f"scheduling the task for title {flow_name}")
        info_logger.info(f"db name received is {db_name}")

        sender = get_customer_config(customer_code)
        db = MongoDB(db_name=db_name)

        # Get logging details
        datetimeobj = datetime.strptime(
            f'{job_date}T{job_time}', "%Y-%m-%dT%H:%M")
        cmpgntime = int(datetime.timestamp(datetime.now()))
        cmpgnid = f'campaign_{cmpgntime}'

        # Get message details
        params = {
            "message": "ONDC_TXT_START",
            "reply": "TEXT",
            "next_state": "0_ondc",
            "store_to_db": True,
            "intent": "customer_name"

        }

        lang = 'en'

        #### Display request parameters ####
        info_logger.info(f"Message type :{type}")
        info_logger.info(f"Flowname  :{flow_name}")
        info_logger.info(f"Message: {message}")
        info_logger.info(f"Scheduled_time :{datetimeobj}")
        info_logger.info(f"Campaign ID :{ cmpgnid}")
        #####################################

        info_logger.info(f"Creating a node in job collection")
        IST = pytz.timezone("Asia/Kolkata")

        message = {flow_name}

        campaign_details = {"campaign_id": cmpgnid,
                            "title": flow_name,
                            "message": "beckn_flow",
                            "created_date": str(datetime.now(IST).isoformat()),
                            "scheduled_time": f'{job_date}T{job_time}',
                            "number": contact,
                            }
        db.create_node('job', campaign_details)
        opt_in_user(sender['apikey'], sender['appname'], contact)
        post_to_gupshup(lang, sender, contact, params, cmpgnid, prev_state=None,
                        current_state=f"{flow_name.lower()}_origin", flow_name=flow_name)
    except Exception as e:
        err_logger.error("Exception while scheduling a task", exc_info=True)
        raise e


def get_customer_config(customer_code) -> dict:
    customer_data = {}
    info_logger.info(
        f"reading the configuration file for the customer {customer_code}")
    try:
        customer_config_file = Path(
            f"./customer/{customer_code}/{customer_code}.json").resolve(strict=True)
        print(customer_config_file)
        with open(customer_config_file, 'r') as fp:
            customer_data = json.load(fp)
        info_logger.info("returning customer data")
        return customer_data
    except FileNotFoundError as e:
        err_logger.error(f"Customer configuration not found", exc_info=True)
        return customer_data


class InvalidExcelError(Exception):
    pass
