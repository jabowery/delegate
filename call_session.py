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
import datetime
from voters import Voter
import voters
from global_utils import select_indirect, PhoneNumber,  not_None, phonemes_idx_sigma_match, just_numbers 
#from application_factory.extensions import scheduler
#from application_factory.tasks import task2
import random
import voters_df
from voters_df import my_phonemize_cached, my_phonemes_distance_cached, my_phonemize, all_possibilities, my_phonemes_distance, nicknames_of_homonyms
from shelves import sessions_shelve as shelve
import os
import telnyx
from threading import Thread
import pandas as pd
import re
from word2number import w2n
from dotenv import load_dotenv
load_dotenv(override=True)
STATE_OR_PROVINCE = os.getenv("STATE_OR_PROVINCE")
exec(open(f'static_data/country/usa/{STATE_OR_PROVINCE}/county_name_to_auditor_phone.py').read())

shelve['live_calls'] = dict()
logging.debug(f'initializing class {shelve}')
def pick_keywords(some_words, num = 3):
    from static_data.stop_words import stop_words
    logging.debug(some_words)
     
    filtered_sentence = [w for w in some_words.lower().split(' ') if not w.lower() in stop_words]
    filtered_sentence = [w for w in filtered_sentence if len(w)>3]
    logging.debug(filtered_sentence)
    picked_keywords = ' '.join(random.sample(set(filtered_sentence), num))
    logging.debug(picked_keywords)
    return picked_keywords
     

def get_current_bills():
    ###
    ## Get bills
    #
    from bs4 import BeautifulSoup
    import requests
    url = requests.get('https://docs.house.gov/BillsThisWeek-RSS.xml')

    soup = BeautifulSoup(url.content, features='lxml')
    entries = soup.find_all('entry')
    billdict = dict()
#    for i in [entries[-1]]:
#      title = re.sub(r'[^0-9a-zA-Z]',' ',i.title.text)
#      link = i.link['href']
#      content = i.content.text
#      logging.debug(f'Title: {title}\n\nSummary: {content}\n\nLink: {link}\n\n------------------------\n')
    htmlentry = BeautifulSoup(BeautifulSoup(str(entries[-1]), features='lxml').content.text,'html.parser')
    blank_bill_number_count = 0
    bill_numbers = [re.sub(r'[^0-9]','',x.text) for x in htmlentry.select('.legisNum')],
    bill_titles = [x.text.lower() for x in htmlentry.select('.floorText')]
    for x in bill_numbers[0]:
        print(x)
        bill_title = bill_titles.pop(0)
        if not(x): # Sometimes the House throws in an item with no number
            x = 'abcdefghijklmnopqrstuvwxyz'[blank_bill_number_count]
            blank_bill_number_count += 1
            continue # TODO find a better identifier than an arbitrary letter of the alphabet
        billdict[x] = re.sub(r'[^0-9a-zA-Z]',' ',bill_title)
        logging.debug(f'Bill Number: {x}, Title: {billdict[x]}')
#    billdict = dict(
#        zip(
#            [re.sub(r'[^0-9]','',x.text) for x in htmlentry.select('.legisNum')],
#            [x.text.lower() for x in htmlentry.select('.floorText')]
#        )
#    )
    #
    ## Got bills
    ###
    return billdict

class Call_Session:
    event_types = {
        'call.transcription',
        'call.answered',
        'call.initiated',
        'call.recording.saved'
    }
    ###
    ## Action naming conventions for methods are as follows:
    ## f'{action}q' asks the user for information required to take that f'{action}, 
    ## sometimes after asking for confirmation with f'{action}confirmq', confirmed with f'{action}confirm'
    ## For instance delegateq asks who they want as their delegate.
    ## f'{voting_action}confirmq' asks for a yes or no confirmation.
    ## f'{voting_action}confirm' checks for a yes confirmation, otherwise, cycles back to f'{voting_action}q'
    ## f'{voting_action}' executes the voting_action (upon 'yes' confirmation)
    ## These naming conventions must be followed for the state machine to work.
    ##
    ## The state of the state machine is a stack of menus along with other properties persisting in the Call_Session.
    ## When a menu's item is selected, the item is pushed on top of the stack and the machine enters the new state. 
    ## A menu's lifecycle is:
    ##  1) calleval(f'self.{action}q()') #Enter the menu's context
    ##  2) self.push_state()         #save the menu's context 
    ##  3) self.state = f'{action}()'  #and perform the action in its own context
    ##  4) Exit to send voice prompt.
    ##  5) Receive transcripted voice response.
    ##  6) eval(f'self.{self.state}()')  #Resume execution to take the action on the voice response's transcript.
    ##  7) eval(f'self.{self.pop_state()}') # Pop the stack back to the f'{action}q' state and execute immediately.
    ##
    ## 
    ## 
    #
    store_actions = ['money','politics','tell_me_about']#
    voting_actions = ['delegate','audit','vote','register','tell_me_about']
    #
    ##
    ###
#    res = telnyx.OutboundVoiceProfile.retrieve(os.environ["TELNYX_OUTBOUND_VOICE_PROFILE_ID"])

    def __init__(self,event):
        Call_Session.sovereign_phones = eval(os.getenv('SOVEREIGN_PHONES')) # can change sovereigns on the fly
        if type(event) == str: # if this is a session id
            # initialize only ._id and return the object
            # don't initialize .id as that updates the activity timer
            # and will inhibit the call hangup on inactivity
            self._id = event
            return

        self.event = event
        self.data = event.data
        TELNYX_CONNECTION_ID = os.getenv('TELNYX_APP_CONNECTION_ID')
        call = telnyx.Call(connection_id=TELNYX_CONNECTION_ID) 
        # call_control_id for use in telnyx API URL endpoints
        call.call_control_id = self.data.payload.call_control_id
        self._call = call # later self.call will return telnyx query of call status 
        self.id = str(self.data.payload.call_control_id) #must be set before other properties
#        logging.debug('call control id class is '+str(self.data.payload.call_control_id.__class__))
        self.call_control_id = self.data.payload.call_control_id
        self.event_type = self.data.event_type
        self.speech_prompt = '' # Assuming successful initiation of some intervoting_action

    @classmethod
    def delete_headntail_sp(cls,trs):
        trs = re.sub(r'^\s+','',trs)
        trs = re.sub(r'\s+$','',trs)
        return trs
        
    @classmethod
    def extract_ten_digit_hyphenated_phone(cls,trs):
        # trs should not contain any numerals not a part of a phone number
        # otherwise it will confound the pattern recognition in PhoneNumber()
        mgrp = re.search(r'(\d\d\d-\d\d\d-\d\d\d\d)',trs)
        if mgrp:
            return mgrp.group(1)
        trs = re.sub(r' ?to ?','2',trs) # compensate for bad transcription of the numeral 2
        logging.debug(trs)
        trs = re.sub(r' ?(or|for) ?','4',trs) # compensate for bad transcription of the numeral 4
        logging.debug(trs)
        trs = re.sub(r'^7 ','',trs) # compensate for bad transcription of leading 'send' as 7
        logging.debug(trs)
        numbers = just_numbers(trs)
        logging.debug(numbers)
        numbers = re.sub(r'(2|4)(\d{10})',r'\2',numbers) #compensate for bad transcription of the word 'to' and 'for'
        logging.debug(numbers)
        phonetrs = str(PhoneNumber(numbers))
        logging.debug(phonetrs)
        mgrp = re.search(r'(\d\d\d-\d\d\d-\d\d\d\d)',phonetrs)
        if mgrp:
            return mgrp.group(1)
        else:
            return ""
#    def add(self):
#        """Add a task.
#        :url: /add/
#        :returns: job
#        """
#        job = scheduler.add_job(
#            func=task2,
#            trigger="interval",
#            seconds=10,
#            id="test job 2",
#            name="test job 2",
#            replace_existing=True,
#        )
#        return "%s added!" % job.name


    def call_recording_saved(self):
        self.payload = self.data.payload
#        self.id = self.payload.call_control_id

        recording_url = self.data.payload.recording_urls.mp3
        recording_name = 'mp3s/'+self.payload.recording_id+".mp3"
        import urllib
        urllib.request.urlretrieve(recording_url, recording_name)
        with open("dynamic_data/transcripts.txt", "a") as file_object:
            print(f'{self.id}: {recording_name}',file=file_object)
        self.log(recording_name)

    def call_initiated(self):
        # Must use _call because call is not yet 
        # available from telnyx.Call.retrieve
        res =self._call.answer()
        logging.debug('answering: '+str(res))

    @classmethod
    def call_transcription_thread(cls, self):
        def evalnewstate(self):
            self.speak_stop()
            logging.debug('evalnewstate: '+str(self.state))
            eval('self.'+self.state+'()')
#            logging.debug('speak: '+str(self.speech_prompt))
            self.speak()

        self.payload = self.data.payload
#        self.id = self.payload.call_control_id
        try:
            self.speak_stop() # the user wants to do something so stop yammering at him and get on with it.
        except Exception as e:
            logging.debug(e)
        self.transcript = self.payload.transcription_data.transcript.lower()
        self.transcript_confidence = self.payload.transcription_data.confidence
        self.log(f'confidence {self.transcript_confidence}: {self.transcript}')
        if self.transcript.find('help')>-1: # help should always be available once we're listening
            logging.debug(f'needs help for {self.state}')
            if self.state[-1] != 'q':
                logging.debug('no q ending '+str(self.state))
                self.state = self.state+'q'
            else:
                logging.debug('q ending '+str(self.state))
            self.make_need_help(self.state, True)
            logging.debug(f'{self.state} with self.need_help[{self.state}] == {self.need_help[self.state]}.')
            self.say('Say')
            self.say('menu')
            self.say('to return to the main menu')
        elif self.transcript.find('menu')>-1:
            logging.debug('returning to main menu')
            self.say('returning to main menu')
            self.transcript=''
            self.reset_state_to('store_actionq')  # Discard any stacked states.  This is the main menu.
        else:
            logging.debug(f'{self.transcript} contains neither help nor menu')
        logging.debug(self.transcript)
        logging.debug('Transcription Confidence: '+str(self.transcript_confidence))
        with open("dynamic_data/transcripts.txt", "a") as file_object:
#                print(f'{self.id} {self.transcript_confidence}: {self.transcript}',file=file_object)
            print(f'{self.id} {self.transcript_confidence}: {self.payload.transcription_data.transcript}',file=file_object)
        self.transcript = Call_Session.delete_headntail_sp(self.transcript)

        evalnewstate(self)

    def call_transcription(self):
        thread = Thread(target=Call_Session.call_transcription_thread,args=(self,)) # this evaluates to the next state's function (method) but doesn't call it except via Thread's targeting
        thread.start()
        logging.debug("Thread started on "+str('self.'+self.state))
        return # immediately respond with success to preempt telnyx from bouncing the transcript again (telnyx API bug?)

    def log(self,msg):
        log = self.get('log')
        log[datetime.datetime.now()] = msg
        self.set('log',log)


    def say(self,text_to_add_to_speech_prompt, end=None):
        # the actual call to speak is just before exiting from an execution of a self.state
        # only call this when the text is complete enough to justify a pause, as at the end of a paragraph
        text_to_add_to_speech_prompt = re.sub('_',' ',text_to_add_to_speech_prompt)
        text_to_add_to_speech_prompt = text_to_add_to_speech_prompt+("""

        """ if end==None else '') # that was the pause
        logging.debug('queuing up: '+str(text_to_add_to_speech_prompt))
        self.speech_prompt += text_to_add_to_speech_prompt

    def speak(self): ## called just before a successful exit from a *q self.state (one that queries the user for speech input)
        if not(self.speech_prompt):
            return

        logging.debug("NOW SPEAKING"+str(self.speech_prompt))
        self._call.speak(language='en-US', voice='male', payload =  self.speech_prompt)
        self.log(self.speech_prompt)
        self.speech_prompt = ''

    def get(self,prop):
        return shelve[self.id][prop] if prop in shelve[self.id] else None

    def set(self,prop,val):
        pdict = shelve[self._id]
        pdict[prop] = val
#        logging.debug(prop,val+str(pdict[prop]))
        shelve[self._id] = pdict
        shelve.sync()

    def vr_count(self):
        return len([x for x in self.voters_with_phone if x.is_registered()])

    @property
    def whoms(self):
        whoms = self.get('whoms')
        return whoms
    @whoms.setter
    def whoms(self,whoms):
        self.set('whoms',whoms)

    @property
    def which_whom_query(self):
        which_whom_query = self.get('which_whom_query')
        return which_whom_query
    @which_whom_query.setter
    def which_whom_query(self,which_whom_query):
        self.set('which_whom_query',dict(which_whom_query) if not_None(which_whom_query) else None) #normalize to dict rather than series

    @property
    def first_whom_query(self):
        first_whom_query = self.get('first_whom_query')
        return first_whom_query
    @first_whom_query.setter
    def first_whom_query(self,first_whom_query):
        self.set('first_whom_query',dict(first_whom_query) if not_None(first_whom_query) else None) #normalize to dict rather than series

    @property
    def phone(self):
        phone = PhoneNumber(self.get('phone'))
        return phone
    @phone.setter
    def phone(self,numberofclassPhone):
        self.set('phone',numberofclassPhone)

    @property
    def id(self):
        return self._id # 'def get' above needs this so it can't call 'def get'
    @id.setter
    def id(self,idval):
        self._id = idval
        # if not found in the shelve database
        # (the should initialize only the first time id is set)
        if not(idval in shelve):
        ## initialize
            shelve[idval]={} # this enables the above 'def set' method as well as 'def get'
            shelve.sync()
            self.set('log',dict())  # log of this session's dialogue 
            self.phone = self.data.payload.from_.ten_digit_hyphenated
            logging.debug('initializing session for '+str(self.phone))
            logging.debug(f"1self.voters_with_phone = Voter.select({'PHONENO:'+str(self.phone)})")
            self.voters_with_phone = Voter.select({'PHONENO':str(self.phone)}) #returns a list of voters
            logging.debug(self.voters_with_phone)
            if(len(self.voters_with_phone)==0):
                self.voter = Voter()
                self.voter.PHONENO = str(self.phone)
                logging.debug(f"2self.voters_with_phone = Voter.select({'PHONENO:'+str(self.phone)})")
                self.voters_with_phone = Voter.select({'PHONENO':str(self.phone)})
            else:
                self.voter = self.voters_with_phone[0] # if multiple possible voters at this phone pick the first one
            self.need_introduction = True
            # TODO: states relating to "gifts" are for "christmas money" 
            self.need_help = {qstate:not(self.voter.is_active) for qstate in [ 'giftq', 'votingq', 'store_actionq', 'voting_actionq', 'whomq', 'delegateconfirmq', 'voteq', 'votebillq', 'recallconfirmq', 'registerwhomconfirmq', 'payq', 'payconfirmq']}
            self.make_need_help('payq', True) # Always provide the caveat speech for paying.
            self.state = 'initialized'
        else:
            logging.debug(f"3self.voters_with_phone = Voter.select({'PHONENO:'+str(self.phone)})")
            self.voters_with_phone = Voter.select({'PHONENO':str(self.phone)})
        live_calls = shelve['live_calls']
        live_calls[idval] = datetime.datetime.now()
        shelve['live_calls'] = live_calls

    @property
    def need_help(self):
        need_help = self.get('need_help')
        return need_help
    @need_help.setter
    def need_help(self,nh):
        self.set('need_help',nh)

    @property
    def voter(self):
#        vtr = self.get('voter')
#        if vtr != None:
#            logging.debug('get ',vtr.id,' voter.__class__'+str(vtr.__class__))
        return self.get('voter')
    @voter.setter
    def voter(self,votervalue):
        self.set('voter',votervalue)

    @property
    def bill(self):
        return self.get('bill')
    @bill.setter
    def bill(self,billvalue):
        self.set('bill',billvalue)

    @property
    def call(self):
        TELNYX_CONNECTION_ID = os.getenv('TELNYX_APP_CONNECTION_ID')
        call = telnyx.Call(connection_id=TELNYX_CONNECTION_ID) 
        call.call_control_id = self._id
        logging.debug('attempting to retrieve call with id '+str(self._id))
        return call.retrieve(self._id)
#        return self.get('call')
    @call.setter
    def call(self,callvalue):
        # this is invalid
        # raise exception?
        return

    @property
    def is_alive(self):
        TELNYX_CONNECTION_ID = os.getenv('TELNYX_APP_CONNECTION_ID')
        call = telnyx.Call(connection_id=TELNYX_CONNECTION_ID) 
        # call_control_id for use in telnyx API URL endpoints
        call.call_control_id = self._id
        return call.retrieve(self._id).is_alive

    @property
    def state(self):
        logging.debug('get(state): '+str(self.get('state') )) # 'None' if None)
        state = self.get('state') # 'None' if None
        logging.debug(f'state: {state}')
        return None if state == None else str(state[-1]) # 'None' if None
    @state.setter
    def state(self, new_state):
        state = self.get('state')
        self.set('state',[new_state] if state == None else self.get('state')[:-1]+[new_state]) #replace top of stack

    def push_state(self): # This pushes the current state and leaves placeholder for the new state that must be filled
        state = self.get('state')
        state.append(None)
        self.set('state', state)

    def pop_state(self):
        state_stack = self.get('state')
        state_stack.pop() # toss the state we're returning from
        self.set('state', state_stack)
        state = self.state # return only the state to which we're returning
        return state if state[-1]==')' else state+'()' # return in eval form only the state to which we're returning

    def reset_state_to(self,new_state):
        self.set('state',[new_state])

    @property
    def call_control_id(self):
        logging.debug('get(call_control_id): '+str(self.get('call_control_id') )) # 'None' if None)
        return str(self.get('call_control_id') ) # 'None' if None
    @call_control_id.setter
    def call_control_id(self, new_call_control_id):
        self.set('call_control_id',new_call_control_id)

    @property
    def billdict(self):
        billdict = self.get('billdict')
        if not(billdict):
            self.billdict = get_current_bills()
        return self.get('billdict')
    @billdict.setter
    def billdict(self, new_billdict):
        self.set('billdict',new_billdict)

    @property
    def whom(self):
        whom_id = self.get('whom_id')
        return Voter(self.get('whom_id')) if whom_id else None
    @whom.setter
    def whom(self, new_whom):
        self.set('whom_id',new_whom.id if new_whom else None)

    @property
    def amount(self):
        return self.get('amount')
    @amount.setter
    def amount(self, new_amount):
        self.set('amount',new_amount)

    def best_phoneme_match(self, astring, phoneme_options):
        astring_phonemes = my_phonemize(astring)
        phds = pd.Series({optstr:my_phonemes_distance_cached(optphn,astring_phonemes,optstr,astring) for optstr, optphn in phoneme_options.items()}).sort_values(ascending=False)
        logging.debug(phds)
        mv = phds.min()
        mi = phds.idxmin()
        logging.debug(mv+str( mi))
        return mi

    def match_transcript(self,options, sigma=1):
        logging.debug('matching transcript: '+self.transcript)
        for option in options:
            logging.debug(f'option "{option}" == "{self.transcript}"')
            if self.transcript.find(option)>-1:
                return option
        # exact match failed, so try phoneme distance

        tph = my_phonemize(self.transcript)
        phds = pd.Series({option:my_phonemes_distance(my_phonemize(option),tph) for option in options})
        logging.debug(phds)
        return phonemes_idx_sigma_match(phds,sigma=sigma)
#        logging.debug(phds)
#        mv = min(phds)
#        logging.debug(mv)
#        mi = phds.index(mv)
#        logging.debug(mi)
#        logging.debug(options[mi])
#        return options[mi]


    def hangup(self):
        if self.is_alive:
            self.call.hangup()
        ###
        ## Start critical section
        #
        try:
            live_calls = shelve['live_calls']
            del live_calls[self.id]
            shelve['live_calls'] = live_calls
        except Exception as e:
            logging.debug('The hangup method failed to delete session id '+str(self.id))
            logging.debug('The Exception was '+str(e))
        #
        ## End critical section
        ###

        ####
        ## State Machine
        #
        # initialized -> answered/welcomed -> voting_action?
    def call_answered(self):
#        if not(self.data.payload.from_.area in {'712', '515','641', '402','319','563'}): # TODO configuration 
#            logging.debug('hanging up on area code '+str(self.data.payload.from_.area))
#            self.hangup()
#            return 
        self.payload = self.data.payload
        transcription_url = f'https://api.telnyx.com/v2/calls/{self.call_control_id}/actions/transcription_start'
        headers2 = {'Content-Type':'application/json','Accept': 'application/json;charset=utf-8','Authorization': f'Bearer {telnyx.api_key}',}
        data2 = '{"language":"en"}'
        import requests
        response2 = requests.post(transcription_url, headers=headers2, data=data2)
        if response2:
            logging.debug(response2)
        start_recording = self._call.record_start(format="mp3", channels="single")
        logging.debug(start_recording)
        self.say("Welcome to the demo test version of the delegate network for Iowa.  The delegate network is publicly auditable at all times.") # TODO configuration
        self.say("To see the audit log, see http://delegate.network/audit")
        self.say("All actions taken in the demo test will be erased without notice.")
        self.store_actionq()
    def make_need_help(self,qstate,boolval):
            nh = self.need_help
            nh[qstate] = boolval
            self.need_help = nh
    def store_actionq(self):
        self.state="store_actionq"
        if not(self.voter.balance):
            # Bypass the store if no delegate money
            self.push_state() #but come back after voting action complete in the event the balance becomes nonzero
            self.voting()
            return

        if self.need_help['store_actionq']:
            self.say("You can interrupt me at any time.")
            self.say("Say. money.  if you would like to send someone delegate money.")
            self.say("Say. politics. to participate in the delegate network.")
            self.say("Say. tell me about. to hear about this service.")
            self.make_need_help('store_actionq',False)
            if self.sovereign:
                self.say("since you are calling from a sovereign's phone, you are privileged to create delegate money when you say, 'money'!") 
        # store_action? (delegate, vote, recall, audit, register) -> store_action
        else:
            self.say( "If you need help, just say so.")
        self.say("Please choose: ")
        self.sayor(Call_Session.store_actions)
        self.state="store_action"

    @property
    def sovereign(self):
        return self.phone in Call_Session.sovereign_phones

    def store_action(self):
        self.state = 'store_action'
        take_store_action = self.match_transcript(Call_Session.store_actions,sigma=0)
        if not(take_store_action):
            self.say("I didn't quite get that.")
            self.store_actionq()
            return
        logging.debug(take_store_action)
        dispatch_dict = {"money":self.payq, "politics":self.voting,"tell_me_about":self.tell_me_about}
        logging.debug(dispatch_dict[take_store_action])
        self.state="store_actionq()"#come back after store action complete
        self.push_state() 
        (dispatch_dict[take_store_action])()
    def store_actionhelp(self):
        self.make_need_help('store_actionq', True)
        self.store_actionq()
    def tell_me_about(self):
        self.say("the, delegate money and political networks are Services of the Berkana Ecclesium of The Fair Church") # TODO configuration
        self.say("both are intended to revitalize the heritage of local autonomy that founded the United States")
        self.say("please visit http://delegate.network")
        eval('self.'+self.pop_state()) #entire method call string must have been pushed except object context

    def giftq(self):
        # TODO: See "christmas money"
        self.say("Your gift will be distributed by the sovereigns ")
        self.say("Please tell us who you are and describe your gift.")
        self.state='gift'

    def gift(self):
        # TODO: See "christmas money"
        self.say("Thank you for making, Operation SANTA, a success with your gift.")
        self.say("a sovereign will contact you for further information.")
        prop = self.voter.create_property(self.transcript)
        prop.session = self
        eval('self.'+self.pop_state()) #entire method call string must have been pushed except object context
#        self.store_actionq()

    def voting(self):
        # This is called only at the end of call_answered.
        # If this is the first time for this voter, push voting_actionq to get his delegate from him and then pop back to voting_actionq, otherwise, just go to voting_actionq.
        if not(self.voter.is_active):
#            self.say("Here, Registered voters may, at will")
#            self.say("vote directly on bills before the US House of Representatives.")
#            self.say("delegate their power")
#            self.say("audit how that power is being used, and")
#            self.say("recall that delegation of power.")
#            self.say("At any time, you may interrupt me")
#            self.say("say, help, for additional instructions")
#            self.say("or say, menu, to return to the main menu")
#            self.say("or just hang up on me.")
            self.say("Let's get started!")
            self.say("first")
            self.state='voting_actionq' #
            self.push_state() #come back to voting_actionq after delegating
            self.delegateq()
        else:
            self.voting_actionq()
        if False:
            speech_prompt = "According to our latest update from the Iowa Secretary of State," #TODO configuration
            if self.vr_count():
                if self.vr_count() == 1:
                    self.say(speech_prompt + " there is one person registered to vote at your caller ID phone number.")
                    self.say("I'll assume you are that person unless you tell me your name and it doesn't match.")
                else:
                    self.say(speech_prompt + f" there are {self.vr_count()} registered voters at your caller ID phone number.")
                    self.say("For now I'll assume you are one of them.")
            else:
                self.say(speech_prompt + " there is no one registered to vote with your caller ID phone number.  ")
                self.say("Your delegations and votes will have effect once the delegate network verifies you are a registered voter.")
        self.speak()

    def voting_actionq(self):
        self.state='voting_actionq'  # Discard any stacked states.  This is the main menu.
        if self.need_help['voting_actionq']:
            self.say("You can interrupt me at any time.")
            self.say("Say. delegate. if, in the absence of your vote on a bill, you would like to delegate your voting power to another registered voter.")
            self.say("Say. vote. if you would like to vote on a bill.")
            self.say("Say. audit. if you would like to audit votes.")
            self.say("Say. register. ",end='')
            if self.voter.is_registered():
                self.say("to update your voter registration.")
            else:
                self.say(f"if you want your delegate network actions to count when calling from your current phone number: {self.voter.PHONENO}.")
            self.say("Say. tell me about. to hear about this service.")
#            self.say("say. pay. if you would like to to send someone in simulated property money.")
            self.make_need_help('voting_actionq',False)
        # voting_action? (delegate, vote, audit, register, tell_me_about) -> voting_action
        else:
            self.say( "If you need help, just say so.")
        self.say("Would you like to ")
        self.sayor(Call_Session.voting_actions)
        self.state="voting_action"

    def voting_action(self):
        self.state = 'voting_action'
        take_voting_action = self.match_transcript(Call_Session.voting_actions,sigma=1.6)
        if not(take_voting_action):
            self.say("I didn't quite get that.")
            self.voting_actionq()
            return
        logging.debug(take_voting_action)
        dispatch_dict = {"delegate":self.delegateq, "vote":self.voteq, "audit":self.auditq, "register":self.registerq, "tell_me_about":self.tell_me_about}
        logging.debug(dispatch_dict[take_voting_action])
        (dispatch_dict[take_voting_action])()
    def voting_actionhelp(self):
        self.make_need_help('voting_actionq', True)
        self.voting_actionq()
    def whomhelp(self,theiryour='their'):
        self.say(f"Just say {theiryour} 10 digit phone number or their name as it appears in {theiryour} voter registration.")
        self.say(f"If you say {theiryour} name, please also provide any of {theiryour} town, county, zip and/or street name.")
        self.say("Please speak slowly and distinctly.")

    def delegateq(self):
        self.state = 'delegateq'
        if self.need_help['whomq']:
            self.say("In your absence on a vote, tell me to whom you delegate your voting power. ")
            self.whomhelp()
            self.make_need_help('whomq',False)
        if self.voter.default_delegate:
            self.say("Curently, your delgate is "+self.voter.default_delegate.name_identification_string()+".")
        self.say("To whom do you wish to delegate your vote when absent?")
        self.state = 'delegate'

    def delegate(self):
        self.state = 'delegate'
        self.act_whom_match_and_disambiguate('delegate')

    def act_whom_match_and_disambiguate(self,voting_action,voting_action_modifier=''):
        returnfrompmt = self.person_match_transcript() # saves matched person(s) in self.whoms and if just one, then in self.whom
        logging.debug(returnfrompmt)
        if returnfrompmt: # saves matched person(s) in self.whoms and if just one, then in self.whom
            #### confirm?
            if self.ambiguouswhom():
                self.state=f"say_confirm_voting_action_on_person('{voting_action}',self.whoms,'{voting_action_modifier}')"
                self.push_state() #come back to confirm after disambiguation
                self.disambiguatewhomq()
            else:
                logging.debug('unambiguous')
                self.say_confirm_voting_action_on_person(voting_action,self.whom,voting_action_modifier)
        else:
            self.say("unable to identify")
            self.say("You might need to spell a name.")
            self.say("For example, instead of saying:")
            self.say("JOHN, Doe, OF, Warren, County,")
            self.say("You might spell out the name, Doe," )
            self.say("JOHN, D. O. E.  , OF, Warren, County,")
            eval(f'self.{voting_action}q()')

    def yn_transcript(self):
        return self.match_transcript(['yes','no'])
    def delegateconfirm(self):
        self.state = 'delegateconfirm'
        ##### "yes" -> voting_action?  
        yn = self.yn_transcript()
        if yn == 'yes':
            self.voter.delegate(self.whom)
            self.say(f'You have delegated {self.voter.default_delegate.first_middle_last_of_city_string()} to vote on your behalf in your absence on a vote. ')
            eval('self.'+self.pop_state()) #entire method call string must have been pushed except object context
#            self.voting_actionq()
        ##### "no" -> delegate(whom)?
        elif yn == "no":
            self.delegateq()
        else:
            self.state='delegateconfirmq' # y/n if only one matched. pick a, b, c, d... if multiple
            self.say("I didn't quite catch that.")
            self.say_confirm_voting_action_on_person('delegate',self.whom)
    def disambiguatewhomq(self):
        self.state = 'disambiguatewhomq'
        self.say(f'There are {len(self.whom)} registered at that number.')
        first_names = [x.FIRST_NAME for x in self.whom]
        logging.debug(first_names)
        self.sayor(first_names)
        self.say('Which did you intend?')
        self.state = 'disambiguatewhom'
    def disambiguatewhom(self):
        self.state = 'disambiguatewhom'
        first_names = [x.FIRST_NAME for x in self.whom]
        first_name = self.match_transcript(first_names)
        if not(first_name):
            self.say("I didn't quite get that.")
            self.disambiguatewhomq()
            return
        self.whom = self.whom[first_names.index(first_name)]
        eval('self.'+self.pop_state()) #entire method call string must have been pushed except object context

    def sayor(self,options):
        try:
            self.say(', '.join(options[:-1])+', or, '+options[-1])
        except:
            logging.debug(f'failed sayor with options: {options}')
        
    def ambiguouswhom(self):
        return self.whoms != None and len(self.whoms)>1

    def payq(self):
        self.state = 'payq'
        self.say("")
#        self.say("spelled, c. h. r. i. s. m. o. n.")
        if self.voter.balance:
            self.say(f'Your delegate bank balance is ${self.voter.balance}')
        if self.need_help['payq']:
#            self.say("to discover what you can buy with delegate money")
#            self.say("visit http://delegate.network/money")
            self.say("let's say you want to send $10.25 in delegate money to delegate john doe of montgomery county.")
            self.say("say, $10.25 to john doe of montgomery county.")
            self.say("or, if his voter registered phone number is 712-321-9876,")
            self.say("say, $10.25 to 712-321-9876")
            self.make_need_help('payq',False)
#        if self.sovereign:
#            self.say("You, calling from an authorized phone, can create delegate money simply by paying others.")
#            self.say("Charge-backs should be handled in other ways.")
        elif not(self.voter.balance):
            self.say("You don't yet have any delegate money")
#            self.speak()
            self.state='hangup'
#            eval('self.'+self.pop_state()) #entire method call string must have been pushed except object context
            return

    #        self.whomhelp()
        self.say("send how much delegate money to what delegate?")
        self.push_state()
        self.state = 'pay' 

    def pay(self):
        self.state = 'pay'
        trs = self.transcript
        trs = re.sub(r'^(send|pay|give|transfer)','',trs)
        ###
        ## Compensate for bad money transcription via w2n library.
        #
        dollars = '0'
        cents = '00'
        if trs.find('dollars')>-1:
            ds = re.search(r'(.*)dollars',trs)
            try:
                dollars = w2n.word_to_num(ds.group(1))
                logging.debug(f'word_to_num({ds.group(1)})=={dollars} dollars')
            except:
                dollars_match= re.search(r'([0-9,]+) dollars',ds.group(0))
                if dollars_match:
                    dollars = dollars_match.group(1)
                    logging.debug(f'{ds.group(0)} -> {dollars}')
                else:
                    self.say("I'm sorry, but I didn't understand.")
                    self.say("I thought I heard you say")
                    self.say(self.transcript)
                    self.make_need_help('payq',True) # provide help again
                    self.payq() # and re-prompt for the amount
                    return

            logging.debug(f'nullify commas: {dollars}')
            trs = re.sub(re.escape(ds.group(1)),'',trs)
            trs = re.sub('dollars','',trs)
        if trs.find('cents')>-1:
            cs = re.search(r'(.*)cents',trs)
            try:
                cents = w2n.word_to_num(cs.group(1))
            except:
                cents = re.search(r'(\d+) cents',ds.group(0)).group(1)
            trs = re.sub(re.escape(cs.group(1)),'',trs)
            trs = re.sub('cents','',trs)
        if int(dollars) or int(cents):
            if len(cents)==1:
                cents = '0'+cents
            logging.info(f'compensating for bad transcription of dollar value ${dollars}.{cents}')
            trs = f'${dollars}.{cents} '+trs
        #
        ## Compensated for bad money transcription via w2n library.
        ###
        trs = re.sub(',','',trs) # deal with thousands, eg $1,000
        logging.debug(trs)
        amt = re.search(r'\$((\d+)\.(\d\d)|\.(/d/d)|(\d+)|)',trs)
        if not(amt):
            self.say("I'm sorry, but I didn't hear an amount.")
            self.say("I thought I heard you say")
            self.say(self.transcript)
            self.make_need_help('payq',True) # provide help again
            self.payq() # and re-prompt for the amount
            return
        self.amount = amt.group(1)
        logging.debug(str(amt))
        trs = re.sub(re.escape('$'+amt.group(1)),'',trs, count=1) # get rid of non-phone number numerals before extracing problematic transcriptions of phone number
        logging.debug(trs)
        self.transcript = re.sub(r'^\s*to\S*','',trs)
        self.act_whom_match_and_disambiguate('pay',voting_action_modifier=f' ${self.amount} to ')
        return
        # the following code was written when "christmas money" was being considered.
        # it permits sending to any phone number regardless of voter registration of that phone number
    def payconfirmq(self):
        self.state='payconfirmq' # y/n if only one matched. pick a, b, c, d... if multiple
        self.say_confirm_voting_action_on_person('pay',self.whom,f' ${self.amount} to')

    def payconfirm(self):
        self.state = 'payconfirm'
        ##### "yes" -> voting_action?  
        yn = self.yn_transcript()
        if yn == 'yes':
            self.voter.pay(self.whom,self.amount)
            self.say(f'You have paid ${self.amount} in Delegate money to {self.whom.first_middle_last_of_city_string()}')
            eval('self.'+self.pop_state()) #entire method call string must have been pushed except object context
#            self.voting_actionq()
        ##### "no" -> pay(whom)?
        elif yn == "no":
            eval('self.'+self.pop_state()) 
        else:
            self.say("I didn't quite catch that.")
            self.payconfirmq() # y/n if only one matched. pick a, b, c, d... if multiple

    def say_confirm_voting_action_on_person(self,voting_action,voter,voting_action_modifier=''):
        if self.which_whom_query and self.first_whom_query != self.which_whom_query:
            if 'MIDDLE_NAME' in self.which_whom_query and not('FIRST_NAME' in self.which_whom_query):
#                and self.first_whom_query['FIRST_NAME'] == self.which_whom_query['MIDDLE_NAME']:
                self.say("Do you call that person by their middle name?")
        self.say(f'Please confirm, that you want to {voting_action}{voting_action_modifier} {voter.first_middle_last_of_city_string()}. ',end='')
        if self.which_whom_query and 'COUNTY' in self.which_whom_query:
            self.say(f'in {voter.COUNTY} county')
        self.say('Yes or No?')
        self.state = f'{voting_action}confirm'

    def billhelp(self):
        self.say('To see the bills being considered, visit the documents webpage for the House of Representatives at:')
        self.say('http://, d, o, c, s, dot, house, dot, gov,')
        self.say('Please say a number or some keywords to identify a bill')
        billindex = random.randint(0,len(list(self.billdict))-1)
        billnumber = list(self.billdict)[billindex]
        billtitle = list(self.billdict.values())[billindex]
        self.say('For example,')
        try:
            billno = int(billnumber)
            self.say(f' the bill number, {billnumber}, is',end='')
        except:
            billno = 0
            self.say('for a bill',end='')
        self.say(f' titled {billtitle}')
        if(billno):
            self.say(f'So you could say its number, {billnumber}. or,')
        self.say(f'you could say a few words in its title, like, {pick_keywords(billtitle)}')
#        self.say('or, say, list, to hear the titles and numbers of the bills being voted on.')
#        self.say('or, for a list of the bill numbers being considered, just say, numbers,')

    def voteq(self):
        self.state = 'voteq'

                #### "<bill>"?
        if self.need_help['voteq']:
#            self.say('on which bill before the house of representatives do you wish to vote?')
            self.billhelp()
            self.make_need_help('voteq',False)
        self.say("vote on what bill?")
        self.state = 'vote'
    def vote(self):
        self.state = 'vote'
        if self.transcript in ['numbers','number']:
            # 'list' is excluded for now.  the length of synthesized speech is too long.
            self.say('You can interrupt this list at any time by saying a bill number.')
            self.say(f'Delegates are voting on these bill{"s" if self.transcript == "list" else " numbers"} before the US House of Representatives.')
            for num,text in self.billdict.items():
                if self.transcript == 'list':
                    self.say('Title:')
                    self.say(text)
                    self.say('is bill number')
                self.say(re.sub(r'[^0-9]','',num))
            self.voteq()
        else:
            if self.match_transcript_bill(): # saves matched bill in self.bill
                self.votebillq()
            else:
                self.say("unable to identify bill")
                self.voteq()
    def match_transcript_bill(self):
        billmatch = re.search(r'(hr|h r|house resolution)?\s*([0-9]+)',self.transcript)
        self.bill =  billmatch.group(2) if billmatch else False
        if not(self.bill):
            transcript_set = set(self.transcript.split(' '))
            logging.debug(','.join([x for x in self.billdict]))
            intersection_lengths = [len(set(self.billdict[x].split(' ')).intersection(transcript_set)) for x in self.billdict]
            max_value = max(intersection_lengths)
            if max_value:
                self.bill = list(self.billdict)[intersection_lengths.index(max_value)]
        return self.bill 

    def votebillq(self):
        self.state = 'votebillq'
        ##### votebill?(yay, nay, abstain, absent)
        self.say("how do you want to vote on "+self.bill+', titled, '+self.billdict[self.bill]+"?")
        self.say("yes, no, abstain, or, absent?")
        self.state = 'votebill'
    def votebill(self):
        self.state = 'votebill'
        ###### "yay" -> voting_action?
        cast = self.match_transcript(['yes','no','abstain','absent'])
        if cast:
            self.voter.vote(self.bill, cast)
            self.votebillacknowledge()
        else:
            logging.debug(f'"{self.transcript}"')
            self.say("I didn't quite catch that.")
            self.votebillq()
    def votebillacknowledge(self):
        self.say(f'Your vote on house resolution {self.bill} is now')
        if self.bill in self.voter.votes:
            self.say(f'{self.voter.votes[self.bill]}')
            self.say('Thank you for voting')
        else:
            self.say("absent")
            self.say(f"you may audit your delegation to see how your vote is cast in your absence on {self.bill}.")
        eval('self.'+self.pop_state()) #entire method call string must have been pushed except object context
        #self.voting_actionq()

    ## "recallconfirmq" 
    def recallconfirmq(self):
        self.state = 'recallconfirmq'
        if self.voter.default_delegate:
            self.say_confirm_voting_action_on_person("recall",self.voter.default_delegate)
#            self.say("Do you want to recall "+self.voter.default_delegate.name_identification_string()+"?")
#            self.say("Please say, yes or no.")
        else:
            self.say("you have not delegated anyone to vote in your absence")
            eval('self.'+self.pop_state()) #entire method call string must have been pushed except object context
            #self.voting_actionq()

    def recallconfirm(self):
        self.state = 'recallconfirm'
        yn = self.match_transcript(['yes','no'])
        if yn=="yes":
            self.say(f'You have recalled your delegate {self.voter.default_delegate.first_middle_last_of_city_string()}. ')
            self.voter.recall()
            eval('self.'+self.pop_state()) #entire method call string must have been pushed except object context
            #self.voting_actionq()
        elif yn=="no":
            self.say(f'You have retained {self.voter.default_delegate.first_middle_last_of_city_string()} as your delegate. ')
            eval('self.'+self.pop_state()) #entire method call string must have been pushed except object context
            #self.voting_actionq()
        else:
            self.say("unrecognized")
            self.recallconfirmq()

    def registerq(self):
        self.state = 'registerq'
        self.say('In what county do you live?')
        self.state = 'registercounty'

    def registercounty(self):
        self.state = 'registercounty'
        county = self.match_transcript(all_possibilities['county'].keys())
        if county:
            ph = county_name_to_auditor_phone[county]
            self.say('For your delegate network power to count, your voter registration must contain the phone number you use here.')
            self.say(f'You can update your official phone number on your voter registration by calling the {county} county auditors office at.')
            self.say(ph)
            self.say('that number again is,')
            self.say(ph)
            self.say('once more, slowly, that number again is,')
            self.say(', '.join(ph) + '.')
            eval('self.'+self.pop_state()) #entire method call string must have been pushed except object context
            #self.voting_actionq()
        else:
            self.say('I didnt quite catch that.')
            self.registerq()
            
    def registerwhoq(self):
        self.state = 'registerwhomq'
        if self.need_help['whomq']:
            self.say("")
            self.whomhelp('your')
            self.make_need_help('whomq',False)
        if self.voter.default_delegate:
            self.say(f"I {'currently' if self.voter.id < Voter.first_tentative_vid else 'tentatively'} believe you are registered as "+self.voter.name_identification_string()+".")
        self.say("Which registered voter are you?")
        self.state = 'registerwhom'
    ## "registerwhoconfirmq" 
    def registerwhoconfirmq(self):
        self.state = 'registerwhomconfirmq'
        if self.voter.default_delegate:
            self.say_confirm_voting_action_on_person("registerwhom",self.voter.default_delegate)
#            self.say("Do you want to be registered to vote as "+self.voter.default_delegate.name_identification_string()+"?")
#            self.say("Please say, yes or no.")
        else:
            self.say("you have not delegated anyone to vote in your absence")
            eval('self.'+self.pop_state()) #entire method call string must have been pushed except object context
            #self.voting_actionq()

    def registerwhomconfirm(self):
        self.state = 'registerwhomconfirm'
        yn = self.yn_transcript()
        if yn=="yes":
            self.voter.registerwhom()
            eval('self.'+self.pop_state()) #entire method call string must have been pushed except object context
            #self.voting_actionq()
        elif yn=="no":
            eval('self.'+self.pop_state()) #entire method call string must have been pushed except object context
            #self.voting_actionq()
        else:
            self.say("unrecognized")
            self.registerwhomconfirmq()

        ## "audit"
    def auditq(self):
        self.state = 'auditq'
        if self.need_help['whomq']:
#            self.say('To audit the vote on a bill') 
#            self.billhelp()
            self.say('To audit a delegate')
            self.whomhelp('')
            self.say('or')
            self.make_need_help('whomq',False)
        self.say("you can say")
        self.say('me')
        self.say("to see how your voting power is being used.")
        self.say('which delegate would you like to audit?')
        self.state = 'auditwhom'

    def auditwhom(self):
        self.state = 'auditwhom'
        logging.debug(f'auditwhom {self.transcript}')
        if len(self.transcript.split(' '))==1 and not(PhoneNumber(self.transcript)):
            # only one word uttered (apparently) so don't try to look up a person
            if self.transcript in ['me','myself','self','i']:
                perform_audit(self, None, self.voter.id)
                eval('self.'+self.pop_state()) #entire method call string must have been pushed except object context
                #self.voting_actionq()
            else:
                self.say("I didn't quite catch that.")
                self.auditq()
        else:
            if self.person_match_transcript(): # saves matched person(s) in self.whom
            #### confirm?
                self.auditconfirmq()
            else:
                self.say("unable to identify")
                self.auditq()
    def auditconfirmq(self):
        self.say_confirm_voting_action_on_person('audit',self.whom)

    def auditconfirm(self):
        self.state='auditconfirm' # y/n if only one matched. pick a, b, c, d... if multiple
        yn = self.yn_transcript()
        if yn=="yes":
            perform_audit(self, None,self.whom)
            eval('self.'+self.pop_state()) #entire method call string must have been pushed except object context
            #self.voting_actionq()
        elif yn=="no":
            self.auditq()
        else:
            self.say("unrecognized")
            self.auditconfirmq()

    def speak_stop(self):
        self._call.playback_stop()
    def series_to_query(self,ser):
        query = ' and '.join([index+'=='+'"'+value+'"' for index,value in ser.items()])
        logging.debug(query)
        return query
    def person_match_transcript(self):
        ###
        ## Convet: S p e l l e d - o u t   w o r d s => Spelled-out words
        #
        transcript = ' '+self.transcript+' '   # need surrounding spaces so the following 
        # also to compensate for end of line in the following regex that does the conversion
        transcript = re.sub(r'\b(\S) (?=\S )',r'\1',transcript)
        transcript = Call_Session.delete_headntail_sp(transcript)
        trs = transcript
        #
        ## Conveted: S p e l l e d - o u t   w o r d s => Spelled-out words
        ###
        phone_trs = Call_Session.extract_ten_digit_hyphenated_phone(trs)
        if phone_trs:
            self.say("I heard you say "+phone_trs)
            self.which_whom = {'PHONENO':phone_trs}
            self.whoms = Voter.select(self.which_whom)
            if len(self.whoms) == 0:
                self.say("I wasn't able to find that caller ID phone number in the voter registration records.")
                self.say("You might ask them to call their county auditor to update their voter registration's phone number.")
                self.whom = None
                self.which_whom = None
            elif not(self.ambiguouswhom()):
#                len(self.whoms) == 1:
                self.whom = self.whoms[0]
            return self.whom
        self.say("I heard you say "+self.transcript)
        trs = re.sub(r'^gym(\S)',r'jim \1',trs)
        first, last, city, county = ['']*4
        whom_queries = []
        resides = dict()
        df_narrowed = Voter.indexed_ids()
        zipsplitlist= re.split(r' (zip|zipcode|zip code)\s+', trs)
        if len(zipsplitlist)>1:
            logging.debug(zipsplitlist[1])
            trs = re.sub(zipsplitlist[1],'',trs) # prevent the word zip from confounding further text recognition
            if len(zipsplitlist)>2:
                logging.debug(zipsplitlist[2])
                zipcodematch = re.match(r'(\d{5})[- ]?(\d{4})?',zipsplitlist[2])
                trs = re.sub(zipsplitlist[2],'',trs) # prevent the digits from confounding further text recognition
                if zipcodematch:
                    logging.debug('matched')
                    zip_code = zipcodematch.group(1)
                    zip_plus = zipcodematch.group(2)
                    resides = {'ZIP_CODE':zip_code}
                    logging.debug(resides)
                    df2_narrowed = df_narrowed.query(self.series_to_query(pd.Series(resides)))
                    if len(df2_narrowed):
                        logging.debug('narrowed')
                        df_narrowed  = df2_narrowed
                    if zip_plus:
                        logging.debug('plus')
                        resides |= {'ZIP_PLUS':zip_plus}
                        df2_narrowed = df_narrowed.query(self.series_to_query(pd.Series(resides)))
                        if len(df2_narrowed):
                            logging.debug('narrowed plus')
                            df_narrowed  = df2_narrowed
            logging.debug('whats left '+str(trs))
        countymatch = re.search(r'(\s+(on|of|in)\s+)?([^ ]*)(\s+county)',trs)
        if countymatch:
            county = countymatch.group(3)
            logging.debug('county '+str(county))
            logging.debug('this '+str(trs))
            trs = re.sub(countymatch.group(),'', trs)
            logging.debug('whats left '+str(trs))
            resides = {'COUNTY':county}
            logging.debug(resides)
        else:
            citycountymatch = re.search(r'(\s+(of|in)\s+)(.+)',trs) # grab city/county leave street
            if citycountymatch:
                citycountyrest = citycountymatch.group(3)
                ofcitycountyrest = citycountymatch.group()
                streetmatch = re.search(r'\s+on\s+.*',citycountyrest)
                if streetmatch: # strip off street so its not included in the citycounty
                    ofcitycounty = re.sub(streetmatch.group(),'',ofcitycountyrest)
                    citycounty =   re.sub(streetmatch.group(),'',citycountyrest)
                else:
                    ofcitycounty = ofcitycountyrest
                    citycounty = citycountyrest # rest can't have zip as it was removed above
                    citycounty = re.sub(r' iowa\s*$','',citycounty) # ignore iowa as a citycounty refinement
                if not(citycounty in  all_possibilities['city']) and citycounty in all_possibilities['county']:
                    resides = {'COUNTY':citycounty}
                elif citycounty in all_possibilities['city']:
                    resides = {'CITY':citycounty}
                else: # find best phoneme match for citycounty
                    citycountyph = my_phonemize(citycounty)
                    phdists = all_possibilities['city'].apply(lambda x:my_phonemes_distance_cached(citycountyph,x))
                    city = phdists.idxmin()
                    citymin = phdists.min()
                    phdists = all_possibilities['county'].apply(lambda x:my_phonemes_distance_cached(citycountyph,x))
                    county = phdists.idxmin()
                    countymin = phdists.min()
                    resides = {'CITY':city} if citymin<countymin else {'COUNTY':county}
                    citycounty = list(resides.values())[0]
                logging.debug(resides)
                trs = re.sub(ofcitycounty,'',trs) # if there, preserving 'on' street name in whats left
                logging.debug('whats left '+str(trs))
        if resides !={}:
            df2_narrowed = df_narrowed.query(self.series_to_query(pd.Series(resides)))
            if len(df2_narrowed):
                logging.debug('narrowed '+str(resides))
                df_narrowed  = df2_narrowed
        if trs.find(' on ')>-1:
            onlist = trs.split(' on ')
            logging.debug('on list '+str(onlist))
            stlist = onlist[1].split(' ')
            if len(stlist)>1:
                if re.match(r'st|street|ave|avenue|rd|road|hwy|hw|highway|ln|lane|dr|drv|drive',stlist[-1]):
                    stlist.pop()
            street = ' '.join(stlist)
            trs = onlist[0]
            logging.debug('whats left '+str(trs))
            resides |= {'STREET_NAME':street}
            logging.debug(resides)
            df2_narrowed = df_narrowed.query(self.series_to_query(pd.Series(resides)))
            if len(df2_narrowed):
                logging.debug('narrowed street '+str( street))
                df_narrowed = df2_narrowed
            else:
                # Was this a city mistakenly proceeded by the word "on"?
                city_resides = {'CITY':resides['STREET_NAME']}
                df2_narrowed = df_narrowed.query(self.series_to_query(pd.Series(city_resides)))
                if len(df2_narrowed):
                    logging.debug('The user mistakenly said "on" in reference to a city.')
                    df_narrowed = df2_narrowed # yes
                    resides = city_resides # so replace the resides criterion with CITY
                else: # or perhaps a county?
                    county_resides = {'COUNTY':resides['STREET_NAME']}
                    df2_narrowed = df_narrowed.query(self.series_to_query(pd.Series(county_resides)))
                    if len(df2_narrowed):
                        logging.debug('The user mistakenly said "on" in reference to a county.')
                        df_narrowed = df2_narrowed # yes
                        resides = city_resides # so replace the resides criterion with COUNTY 
                if 'STREET_NAME' in resides: # if neither county nor city found, shoehorn a street name with similar spelling
                    street_name = resides['STREET_NAME']
                    self.say(f"I couldn't locate a street named {street_name}, nor even a city or county by that name.")   
                    street_names = df_narrowed['STREET_NAME'].unique()
                    import Levenshtein as lev
                    phdists = pd.Series({sname:lev.distance(sname,street_name) for sname in street_names})
                    street = phdists.idxmin()
                    self.say(f"{street} has the closest spelling to {street_name}.")   
                    resides['STREET_NAME'] = street
                    df_narrowed = df_narrowed.query(self.series_to_query(pd.Series(resides)))
                else:
                    CITYorCOUNTY= list(resides)[0]
                    rname = resides[CITYorCOUNTY]
                    self.say(f"There is no street named {rname}, but there is a {CITYorCOUNTY} by that name.")
                    self.say("I'm assuming that's what you meant even though you said")
                    self.say(f"ON  {rname}")
                    self.say("rather than saying")
                    self.say(f"OF {rname}")
        # presume first [middle] last is all there is left in the trs reduction of transcript to process
        trs=Call_Session.delete_headntail_sp(trs)
        fls = trs.split(' ')
        if fls[-1]=='iowa':  # "iowa" is a redundant ending that people reflexively use for locations
            # TODO make this use the configurable environment variable 
            fls.pop()   # drop the trailing 'iowa' that may have been left over from the residence specification (probably zip)
        if resides == {} and len(fls)>2: # if no "resides" restriction as yet and 3 or more names, suspect all but the first two are city or county
            for wordnum in range(2,len(fls)):
                resname = ' '.join(fls[wordnum:])
                for column_name in ['CITY','COUNTY']:
                    tmp_resides = {column_name:resname}
                    df2_narrowed = df_narrowed.query(self.series_to_query(pd.Series(tmp_resides)))
                    if len(df2_narrowed):
                        df_narrowed  = df2_narrowed
                        resides = tmp_resides
                        break
                if resides != {}:
                    break
            if resides !={}:
                fls = fls[:wordnum]
                trs = ' '.join(fls)
        logging.debug('fls: '+str( fls))
        logging.debug('df_narrowed')
        logging.debug(df_narrowed)
        ###
        ## Initialize return variables to assume failure.
        #
        other_id = None # Return None on failure
        self.whom_query = other_id # object property for person matched
        self.whom_queries = [] # if multiple returns, this is
        #
        ## Initialized return variables to assume failure.
        ###
        logging.debug('START preparing homonym queries')
        if len(fls)==1:
            self.say("I thought I heard only one name")
            self.say(f"It sounded like the word {fls[0]}.")
            self.say("I need at least a first and last name.")
            self.say("Please say them slowly and distinctly like this.")
            self.say("John")
            self.say("Doe")
            return self.whom_query
        elif len(fls)==2:
            first, last = fls
            for fn in [first]+list(nicknames_of_homonyms(first)):
                whom_query = resides.copy()
                whom_query |= {'FIRST_NAME':fn, 'LAST_NAME':last}
                logging.debug(whom_query)
                whom_queries.append(pd.Series(whom_query))
                whom_query = resides.copy()
                whom_query |= {'MIDDLE_NAME':fn, 'LAST_NAME':last}
                logging.debug(whom_query)
                whom_queries.append(pd.Series(whom_query))
        elif len(fls)==3:
            #f m l
            first, middle, last = fls
            for fn in [first]+list(nicknames_of_homonyms(first)):
                # fn must remain untouched in this loop body
                #f m l
                middle,last = fls[1:]
                whom_query = resides.copy()
                whom_query|={'FIRST_NAME':fn, 'MIDDLE_NAME':middle, 'LAST_NAME':last}
                logging.debug(whom_query)
                whom_queries.append(pd.Series(whom_query))
                #f l-l
                last = '-'.join(fls[1:])
                whom_query = resides.copy()
                whom_query|={'FIRST_NAME':fn, 'LAST_NAME':last}
                logging.debug(whom_query)
                whom_queries.append(pd.Series(whom_query))
                #f ll
                last = ''.join(fls[1:])
                whom_query = resides.copy()
                whom_query|={'FIRST_NAME':fn, 'LAST_NAME':last}
                logging.debug(whom_query)
                whom_queries.append(pd.Series(whom_query))
                #ff l
                last = fls[2]
                whom_query = resides.copy()
                whom_query|={'FIRST_NAME':''.join(fls[:2]), 'LAST_NAME':last}
                logging.debug(whom_query)
                whom_queries.append(pd.Series(whom_query))
                # The following case actually happened during testing in two cases both democrats:
                # Nichole Piondexter-Wilson is registered as erin nichole poindexter
                # So you must use the first name as the middle name and
                # the first half of the hyphenated name as the last name to find her.
                # Also, Jean Kaul-Brown was registered as Pamela Jean Kaul
                # The phonetic search failed.
                last = fls[1]
                whom_query = resides.copy()
                whom_query|={'MIDDLE_NAME':fn, 'LAST_NAME':last}
                logging.debug(whom_query)
                whom_queries.append(pd.Series(whom_query))
        logging.debug('DONE preparing homonym queries')
        self.whom_queries = whom_queries
        other_id=None
        logging.debug('START searching for exact match')
        self.which_whom_query = None
        self.first_whom_query = None
        for whom_query in whom_queries: # exit at the first query result that provides a match
            df = df_narrowed.query(self.series_to_query(whom_query))
            if len(df):
#                other_ids = df.REGN_NUM
                other_id  = df.iloc[0].REGN_NUM
                self.which_whom_query = whom_query # this is the variant found
                self.first_whom_query=whom_queries[0] # this is what they expected to find, but it may be some variant
                break
        logging.debug('DONE searching for exact match')
        if other_id == None:
            ###
            ## Prepare to do phoneme match by narrowing the search to the 
            ## of the union of the following sets of voters with matching phonemes
            ## from the names actually spoken:
            ## * last of last name
            ## * first of last name
            ## * last of first name
            ## * first of first name
            #
#            try:
            if True:
                logging.debug('START try phoneme match')
                ln = whom_queries[0]['LAST_NAME']
                lnph = all_possibilities['last'][ln] if ln in all_possibilities['last'] else my_phonemize_cached(ln, 'last')
                lnph = re.sub(r'[ˈˌː]','',lnph) # ignore diacritics
                name_df = voters.voters_df.loc[df_narrowed.REGN_NUM]
                lnph_sr = name_df['LAST_PHONEMES'].dropna().str
                i1 = df_narrowed[lnph_sr.endswith  (lnph[-1])].index
                i2 = df_narrowed[lnph_sr.startswith(lnph[ 0])].index
                if 'FIRST_NAME' in whom_queries[0]:
                    fn = whom_queries[0]['FIRST_NAME']
                    fnph = all_possibilities['last'][fn] if fn in all_possibilities['last'] else my_phonemize_cached(fn, 'last')
                    fnph = re.sub(r'[ˈˌː]','',fnph) # ignore diacritics
                    i3 = df_narrowed[name_df['FIRST_PHONEMES'].str.startswith(fnph[ 0])].index
                    i2 = i2.union(i3)
                df_narrowed = df_narrowed.loc[i1.union(i2)]
                logging.debug('DONE try phoneme match')
#            except:
            else:
                logging.debug('ABORT try phoneme match') 
                pass
            #
            ## Narrowed (unless there was an exception.
            ###
            self.transcript = trs
            logging.debug('df_narrowed just before process_transcript')
            logging.debug(df_narrowed)
            if len(df_narrowed)>50000:
                if ({'CITY','COUNTY','STREET','ZIP_CODE'}.intersection(list(resides)))==set():
#                    self.say(f"As I detected no location information in your description of {self.transcript}")
                    self.say("I did not understand a location from what I heard, which was:")
                    self.say(self.transcript)
                    self.whom = None
                    return self.whom
                self.say(f"I'm looking through {len(df_narrowed)} registered voters for {self.transcript}.")
                self.say("Just a moment...")
                self.speak()
            other_id = self.process_transcript(df_narrowed)
            self.say("I didn't find an exact match with what I heard.")

        if other_id == None:
            self.whom = None
        else:
            logging.debug('id found: '+str(other_id))
            self.whom = Voter(other_id)
            self.which_whom = None
            logging.debug(self.whom.name_identification_string())
        return self.whom

    ## If the SoS voter registration doesn't yet know of this phone number:
    ### '''
    ### As of now, according to the Iowa secretary of self.state, your phone number <phone number> doesn't belong to a registered voter.
    ### '''
    ## Elif the this phone number appears in the SoS voter registration:
    ### '''
    ### The Iowa secretary of self.state associates your phone number with a registered voter.
    ###
    ### Your voting_actions on the delegate network will count in the public vote tallies and audits when you confirm your voter registration.
    # Elif there is input to process:
    ## all_inputs.append(input)
    ## "I heard you say: <input to process>"
    # gatherinput= False

    ## processthepromptforspeechinput()
    def find_possibilities(self,allpossibilities):
        poss = [x for x in allpossibilities if self.transcript.find(' '+x+' ')>-1] # search these first for proper name matches
        return poss
    def i_heard(self):
        logging.debug('I heard: '+str(self.transcript))
        self.say('I heard: ',self.transcript)
#        call.speak(payload = 'I heard '+self.transcript ,
#             language="en-US", voice="male")
    def process_transcript(self,narrowed_df): #this (narrowed) voters.voters_df locally overrides the global voters.voters_df
        transcript = self.transcript
        logging.debug('before: '+str(transcript))
        def strip_fields(string,x,fields):
            return re.sub(
                        '\\b'
                    +
                        (
                            '\\b|\\b'.join(
                                x[x.index.isin(fields)]
                            )
                        ).lower()
                    +
                        '\\b'
                    ,''
                    ,string
                    ,count=len(fields)
                )
        df = narrowed_df
        phonemedists_df = pd.Series(dtype='float64',name='REGN_NUM')
        spoken_first_name = ''
        # whomcnt keeps track of how far down we're reaching for a match.
        # the first of the first names is favored as it was ACTUALLY SPOKEN
        # the rest of the "spoken_first_name" bindings are to nickname variants
        # (ie: that variable name should be changed to not be so misleading)
        whomcnt = 0 # keep track of how far down we're reaching for a match (first is favored as it's what was actually spoken)
        for whom_query in self.whom_queries:
            whomcnt += 1
            if not('FIRST_NAME' in whom_query):
                # must be at least 2 names provided or it doesn't get this far
                continue# TODO middle last only 
            else: # FIRST_NAME is provided and for now we'll assume the other name provided is LAST_NAME
                if spoken_first_name != whom_query['FIRST_NAME']:
                    spoken_first_name = whom_query['FIRST_NAME']
                    spoken_first_name_phonemes = my_phonemize(spoken_first_name)
                logging.debug(whom_query)
                # get the phoneme distances between first names and the transcript's first name as parsed
                stripped_input = transcript
                logging.debug(stripped_input)
                thename = whom_query['LAST_NAME']
                logging.debug('LN '+thename)
                thequery = f"LAST_NAME=='{thename}'"
                logging.debug('thequery '+str(thequery))
                name_df = voters.voters_df.loc[df.query(thequery).REGN_NUM]
#                logging.debug(name_df)
                logging.debug(len(name_df)) #thomas m stein
                # thomas james senn
                stripped_again = whom_query['FIRST_NAME']
                stripped_again_phonemes = my_phonemize_cached(stripped_again, 'first')
                fnphdists_df = name_df.apply(lambda x: 
                    my_phonemes_distance_cached(
                        stripped_again_phonemes
                        ,x.loc['FIRST_PHONEMES']
                        ,stripped_again
                        ,x.FIRST_NAME
                    )
                    ,axis=1
                )
                # TODO the following should be made consistent with the LAST_NAME query above
                name = whom_query['FIRST_NAME']
                logging.debug('FN '+name)
                name_df = select_indirect(voters.voters_df, df, {'FIRST_NAME':name})
                if len(name_df)==0:
                    continue    #have first name
                logging.debug(len(name_df))
                stripped_again = whom_query['LAST_NAME']
                stripped_again_phonemes = my_phonemize_cached(stripped_again, 'last')
                lnphdists_df = name_df.apply(lambda x: 
                    my_phonemes_distance_cached(
                        stripped_again_phonemes
                        ,x.loc['LAST_PHONEMES']
                        ,stripped_again
                        ,x.LAST_NAME
                    )
                    ,axis=1
                )
                if len(fnphdists_df)==0:
                    fnphdists_df = pd.Series([], dtype='float64')
                if whomcnt==1: # if this "spoken_first_name" was _actually_ the one spoken:
                    logging.debug('applying discount for spoken first name: '+str(name))
                    lnphdists_df = lnphdists_df - 1.0 # favor the actually spoken first name by decreasing its distance
                flphdists_df = pd.DataFrame([fnphdists_df,lnphdists_df]).transpose().fillna(0)
                vdf = voters.voters_df
                flphdists_df = flphdists_df.apply(lambda x,vdf,spoken_first_name_phonemes: x[0]+x[1]+my_phonemes_distance_cached(vdf.loc[x.name].FIRST_PHONEMES,spoken_first_name_phonemes),vdf=vdf,spoken_first_name_phonemes=spoken_first_name_phonemes,axis=1)

                if len(flphdists_df):
                    phonemedists_df = phonemedists_df.append(flphdists_df)
                    logging.debug(str(pd.DataFrame(phonemedists_df.sort_values(ascending=True)).join(voters.voters_df[['FIRST_NAME','MIDDLE_NAME','LAST_NAME']])))
                    if phonemedists_df.mean()-phonemedists_df.min() >2*phonemedists_df.std():
                        # Return the closest match as soon as a name is 2 standard deviations better than the mean
                        logging.debug('Returning early with 2 standard deviation winner.')
                        other_id = phonemedists_df.idxmin()
                        return other_id
        if len(phonemedists_df):
            other_id = phonemedists_df.idxmin()
            logging.debug(str(pd.DataFrame(phonemedists_df.sort_values(ascending=True)).join(voters.voters_df[['FIRST_NAME','MIDDLE_NAME','LAST_NAME']])))
        else:
            other_id = None
        return other_id


###
##
#
    # If call a human:
    ## forward the call to customer support
#
##
###
    def say_random_sentence(self):
        # accumulate all words to speak by concatenating to this string. 
        # then invoke call.speak to prompt just before accepting more input
        self.speech_prompt = ''   
        def rc(distdict):
            return random.sample(distdict.keys(),1,counts=distdict.values())[0]
        voting_action_phrases = ['{voting_action}']
        person_phrases = ['{firstlast}']
        city_phrases = ['{city}']
        def generate_random_sentence():
            voting_action = random.choice(Call_Session.voting_actions)
            say_other_id_firstlast = ''
            say_other_id_city = ''
#            say_bill_id = ''
            person_phrase =''
            city_phrase = ''
            voting_action_phrase = random.choice(['','please', 'i want to','is my','my','make my'])+' '+random.choice(voting_action_phrases)
            if voting_action in {'delegate','audit','recall'}:
                say_other_id = random.choice(voters.voters_df.index)
                say_other_id_firstlast = voters.voters_df.iloc[say_other_id].FIRST_NAME+' '+voters_df.iloc[say_other_id].LAST_NAME
                person_phrase = random.choice(person_phrases)
                say_other_id_city = voters.voters_df.iloc[say_other_id].CITY
                city_phrase = rc({'':4,'of ':4,'in ':2})+rc({'':7,'the city of ':1})+random.choice(city_phrases)
    #            logging.debug(say_other_id,voters.voters_df.loc[say_other_id][['PHONENO','FIRST_NAME','MIDDLE_NAME','LAST_NAME','COUNTY','PRECINCT','CITY','STREET_NAME','STREET_TYPE','ZIP_CODE','HOUSE_NUM','GENDER'+str('PARTY']]))
            bill_phrase = random.choice(['for ','on '])+random.choice(['house bill ','house resolution ', 'hr','bill'])+' '+('' if random.randint(0,4) >0 else ' ').join(str(random.randint(1,300)))+' '
            if voting_action!='vote':
                bill_phrase = '' if random.randint(0,4)>0 else bill_phrase # only occasionally specify a bill
            else:
                bill_phrase += random.choice(['make my', 'my','I',''])+ ' ' +'vote'+ ' '+ random.choice(['yes','no','yea','nay','abstain','absent'])
                voting_action = ''

            phrases = [person_phrase+' '+city_phrase,voting_action_phrase,bill_phrase]
            random.shuffle(phrases)
            sentence = ' '.join(phrases)
            sentence = re.sub('{firstlast}',say_other_id_firstlast,sentence)
            sentence = re.sub('{city}',say_other_id_city,sentence)
            sentence = re.sub('{voting_action}',voting_action,sentence)
            return sentence
        random_sentence = generate_random_sentence()
        self.say(random_sentence)



def perform_audit(sess, bill_id_in, voter_in=None):
    def showVote():
        nonlocal voter,bill_id,prior_voter_ids,vote
        if len(prior_voter_ids)==0:
            vote = None
        prior_voter_ids.append(voter.id)
        bill_vote = voter.votes.get(bill_id)
        if bill_vote:
            if type(bill_vote) == dict:
                bill_delegates = bill_vote.get('delegates')
                if bill_delegates:
                    nth=0;
                    for bill_delegate in bill_delegates:
                        nth+=1
                        sess.say("{voter.first_middle_last_of_city_string()}'s {nth} bill delegate is {bill_delegate.first_middle_last_of_city_string()}. ",end='')
                        if bill_delegate in prior_voter_ids:
                            sess.say(" This is a vicious cycle, hence that bill delegate is absent.  ",end='')
                            continue
                        else:
                            saved_voter = voter
                            voter=bill_delegate
                            showVote()
                            voter = saved_voter
                        if vote!=None:
                            break
                    logging.debug("")
                else:
                    if voter.id==1e9+1:
                        sess.say(f"{voter.first_middle_last_of_city_string()} is absent.")
            else:
                vote=bill_vote
                sess.say(f"{voter.first_middle_last_of_city_string()} votes ",end='')
                sess.say(vote, end='')
                logging.debug("")
        else:
            delegates=voter.delegates
            if delegates:
                nth=0;
                for delegate in delegates:
                    nth+=1
                    sess.say(f"{voter.first_middle_last_of_city_string()}'s {nth} delegate is {delegate.first_middle_last_of_city_string()}. ",end='')
                    if delegate in prior_voter_ids:
                        sess.say(" This is a vicious cycle, hence that delegate is absent.  ",end='')
                        continue
                    else:
                        saved_voter = voter
                        voter=delegate
                        showVote()
                        voter = saved_voter
                    if vote!=None:
                        break
                logging.debug("")
            else:
                if voter.id==1e9+1:
                    sess.say(f"{voter.first_middle_last_of_city_string()} is absent.")
        prior_voter_ids.pop()
#        return vote
        return

#    if voter_in.__class__ != Voter:
#        sess.say('converting voter from id to class: ',voter_in)
    bill_id = bill_id_in
    if bill_id_in:
        logging.debug(f'bill_id_in:{bill_id_in}')
        yeas=nays=abstains=absents=0;
        prior_voter_ids = []
        voter = voters.voters_df.iloc[0][0]
        for voterid in Voter.all() if voter_in == None else [voter_in]:
            voter = Voter(voterid)
            vote = showVote();
            if vote=='yes':
                yeas+=1
            elif vote == None:
                absents+=1
            elif vote=='no':
                nays+=1
            elif vote=='abstain':
                abstains+=1
        if voter_in == None:
            sess.say(f"Yes {yeas}, No {nays}, Abstain {abstains}, Absent {absents}")
    else:
        bills_audited = []
        delegates_audited = []
        if voter_in == None:
            logging.debug("must specify a voter to audit if no bill specified")
            return
        elif voter_in.__class__ != Voter:
            voter = Voter(voter_in)
        else:
            voter = voter_in
        logging.debug(voter.id)
        while voter:
            sess.say(f'{voter.first_middle_last_of_city_string()}')
            if voter.id in delegates_audited:
                sess.say('but this is a vicious cycle of delegation.')
                break
            sess.say('who')
            for bill_id, vote in voter.votes.items():
                if bill_id in bills_audited:
                    continue
                sess.say(f'on bill {bill_id} votes {vote}')
                bills_audited.append(bill_id)
            sess.say('delegates to ', end ='')
            delegates_audited.append(voter.id)
            voter = voter.default_delegate
        sess.say('no one.')
#if __name__ == "__main__":
#    app = Flask(__name__)
#
#    app.run()
#if __name__ == "__main__":
#    load_dotenv(override=True)
#    telnyx.api_key = os.getenv("TELNYX_API_KEY")
#    telnyx.public_key = os.getenv("TELNYX_PUBLIC_KEY")
#    TELNYX_APP_PORT = os.getenv("PORT")
#    debug_level = os.getenv("DEBUG_LEVEL")
#    app.run(port=TELNYX_APP_PORT)
