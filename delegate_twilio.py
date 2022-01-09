from flask import request
from twilio.twiml.voice_response import Gather, VoiceResponse, Say
from application_factory import app

#app = Flask(__name__)


@app.route("/Callbacks/Voice/Inbound", methods=['GET', 'POST'])
def voice():
    response = VoiceResponse()
    gather = Gather(input='speech', action='/Callbacks/Voice/completed')
    gather.say('Welcome to Twilio, please tell us why you\'re calling')
    response.append(gather)

    print(response)
    return str(response)

@app.route("/Callbacks/Voice/completed", methods=['POST'])
def completed():
    import pprint
#    pp = pprint.PrettyPrinter(indent=4)
#    pp.pprint(request.__dict__)
    print(request.form.get('SpeechResult'))
    response = VoiceResponse()
    response.say('Thank you!')
    return str(response)
