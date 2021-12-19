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
    except ValueError:
        logging.debug("Error while decoding event!")
        return False
    except telnyx.error.SignatureVerificationError:
        logging.debug("Invalid signature!")
        return False
    except Exception as e:
        logging.debug("Unknown Error")
        logging.debug(e)
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
    
@app.route('/Callbacks/Voice/Inbound', methods=['POST'])
def respond():
    event = validate_webhook(request)
    if not event:
        return Response(status=400)
    if os.path.exists('nowdebugging'):
        return Response(status=200)
    sess = Call_Session(event)
    if sess.event_type in Call_Session.event_types: # handle only event types recognized by Call_Session
        method = re.sub(r'\.','_',sess.event_type)
        eval('sess.'+method+'()')
        sess.speak()
    elif sess.state == 'hangup':
        sess.hangup()
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



