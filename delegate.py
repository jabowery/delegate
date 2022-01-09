###
##
# Copyright (C) 2021 James A. Bowery
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see: <http://www.gnu.org/licenses/>.
##
###

import logging
from dotenv import load_dotenv
load_dotenv(override=True)

import os

TELECOM_PROVIDER = os.getenv('TELECOM_PROVIDER')

LOG_LEVEL = os.getenv('LOG_LEVEL')
log_level = eval('logging.'+LOG_LEVEL) if LOG_LEVEL else logging.WARNING
logging.basicConfig(filename='dynamic_data/system.log', level=log_level)

from application_factory.extensions import scheduler
#from application_factory.tasks import task2
from application_factory import app

import telnyx

from flask import request, Response
import re

from global_utils import PhoneNumber
def validate_webhook(req):
    body = req.data.decode("utf-8")
    signature = req.headers.get("Telnyx-Signature-ed25519", None)
    timestamp = req.headers.get("Telnyx-Timestamp", None)

    try:
        event = telnyx.Webhook.construct_event(body,
                                               signature,
                                               timestamp,
                                               100000000)
#        import pprint
#        pp = pprint.PrettyPrinter(indent=4)
#        pp.pprint(event.__dict__)

    except ValueError:
        logging.error("Error while decoding event!")
        return False
    except telnyx.error.SignatureVerificationError:
        logging.error("Invalid signature!")
        return False
    except Exception as e:
        logging.error("Unknown Error")
        logging.error(e)
        return False

#    logging.debug("Received event: id={id}+str( data={data}".format()
#            id=event.data.id,
#            data=event.data))
    if isinstance(event.data.payload.get('to'), str):
        event.data.payload.to = PhoneNumber(event.data.payload.to)
        event.data.payload.from_ = PhoneNumber(event.data.payload.from_)
    if 'len' in dir(event.data.payload.get('to')):
        for toi in range(0,len(event.data.payload.get('to'))):
            event.data.payload.to[toi].phone_number=PhoneNumber(event.data.payload.to[toi].phone_number)
    if 'from_' in event.data.payload:
        if 'phone_number' in event.data.payload.from_:
            event.data.payload.from_.phone_number = PhoneNumber(event.data.payload.from_.phone_number)
        elif isinstance(event.data.payload.get('from_'), str):
            event.data.payload.from_ = PhoneNumber(event.data.payload.from_)
    return event

from shelves import purge, sessions_shelve
purge('sessions')
from call_session import Call_Session # execute voters_df.py to avoid circular import from voters
    
@app.route('/Callbacks/Voice/Inbound', methods=['POST','GET'])
def respond():
#    import pprint
#    pp = pprint.PrettyPrinter(indent=4)
#    pp.pprint(request.__dict__)
#    logging.debug('incoming post')
    print('TELNYX')
    event = validate_webhook(request)
    if not event:
        return Response(status=400)
    if os.path.exists('nowdebugging'):
        return Response(status=200)
    sess = Call_Session(event)
    logging.debug(f'event type: {sess.event_type}')
    if sess.event_type in Call_Session.event_types: # handle only event types recognized by Call_Session
        method = re.sub(r'\.','_',sess.event_type)
        logging.debug(f'eval(sess.{method}())')
        eval('sess.'+method+'()')
        sess.speak()
    elif sess.state == 'hangup':
        sess.hangup()
    return Response(status=200)

import json
from urllib.parse import urlunsplit
@app.route('/Callbacks/Messaging/Inbound', methods=['POST','GET'])
def inbound_message():
    import pprint
    pp = pprint(indent=4)
    pp.pprint(request.__dict__)
    valid_webhook = validate_webhook(request)
    if not valid_webhook:
        return "Webhook not verified", 400
    body = json.loads(request.data)
    message_id = body["data"]["payload"]["id"]
    print(f"Received inbound message with ID: {message_id}")
    to_number = body["data"]["payload"]["to"][0]["phone_number"]
    from_number = body["data"]["payload"]["from"]["phone_number"]
    webhook_url = urlunsplit((
        request.scheme,
        request.host,
        "/messaging/outbound",
        "", ""))
    telnyx_request = {
        "from_": to_number,
        "to": from_number,
        "webhook_url": webhook_url,
        "use_profile_webhooks": False,
        "text": "Hello from Telnyx!"
    }
    text = body["data"]["payload"]["text"].strip().lower()
    if text == "dog":
        telnyx_request["media_urls"] = ["https://telnyx-mms-demo.s3.us-east-2.amazonaws.com/small_dog.JPG"]
        telnyx_request["text"] = "Here is a doggo!"
    try:
        telnyx_response = telnyx.Message.create(**telnyx_request)
        print(f"Sent message with id: {telnyx_response.id}")
    except Exception as e:
        print("Error sending message")
        print(e)
    return Response(status=200)


@app.route('/Callbacks/Messaging/Outbound', methods=['POST','GET'])
def outbound_message():
    body = json.loads(request.data)
    message_id = body["data"]["payload"]["id"]
    print(f"Received outbound DLR with ID: {message_id}")
    return Response(status=200)



#from application_factory import app
@scheduler.task(
    "interval",
    id="job_sync",
    seconds=10,
    max_instances=1,
    start_date="2000-01-01 12:19:00",
)
def task3():
    """Sample task 3.

    Added when app starts.
    """
#    logging.debug("running task 3!")  # noqa: T001
    from shelves import sessions_shelve as shelve
#    logging.debug('connected to redis')
    import datetime
    now = datetime.datetime.now()
    hangup_if_more_than = datetime.timedelta(seconds = 120 )
    last_heard_time = shelve['live_calls']
    # encached list so its items can be deleted inside hangup()
    live_call_ids = list(last_heard_time.keys())
    for session_id in live_call_ids:
        sess = Call_Session(session_id)
#        logging.debug('is session active? '+str(session_id))
        if ( now - last_heard_time[session_id]) > hangup_if_more_than:
            logging.debug(session_id+str(' is inactive so hangup'))
            sess.hangup()



