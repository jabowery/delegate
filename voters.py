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
from global_utils import select
import re
import pandas as pd
import numpy as np
from properties import Property
from voters_df import voters_df, voters_REGN_NUM_df, first_tentative_vid, root_pid 
from shelves import voters_shelve as shelve
from transactions import Transaction
import os
import signal
from dotenv import load_dotenv
load_dotenv(override=True)
NUMBER_OF_ACTIVATIONS_TO_REWARD = os.getenv("NUMBER_OF_ACTIVATIONS_TO_REWARD") 
NUMBER_OF_ACTIVATIONS_TO_REWARD = int(NUMBER_OF_ACTIVATIONS_TO_REWARD) if NUMBER_OF_ACTIVATIONS_TO_REWARD else 0

#for x in ['3481474', '3481473', '3481470', '3481471', '3481472']:
#    del shelve[x]

class Voter:
    def __init__(self, selector=None):
        logging.debug(f'selector {selector}')
        if selector==None:
            #allocate potential voter identity
            next_vid = shelve['last_vid'] + 1# increment allocated voter ids See 'def id' below 
            self.id = next_vid
            shelve['last_vid'] = next_vid
            ###
            ## See below os.kill(root_pid, signal.SIGHUP)
            #
            voters_df.loc[int(self.id)] = pd.Series(['']*len(voters_df.columns),index=voters_df.columns) # CRITICAL FOR DELEGATE_NETWORK = True! this does not yet work!
            #
            ## TODO 
            ###
            logging.debug('Voter NEW')
            logging.debug(self.id)
            shelve[str(self.id)] = {} #after this properties may be set
            return  
        if np.issubdtype(type(selector),np.integer):
            # permit integer selector as input but convert it to canonical type (str)
            selector = str(selector)
        if type(selector) == str:
            # String selector is either:
            if re.match(r'\d\d\d-\d\d\d-\d\d\d\d',selector):
                # A phone number, in which case it is either:
                if selector in shelve: # NOTE: the voters_shelve index contains both phone numbers as strings (mapping to integers as strings) and integers as strings.
                    # already registered, so return its id...
                    self.id = shelve[selector] # map phone number to id
                    return
                else:
                    # or else it is a new phone number, so create its id and register it.
                    new_voter = Voter()
                    shelve[selector] = new_voter.id # map phone number to id
                    self.id = new_voter.id
                    self.PHONENO = selector
                    os.kill(root_pid, signal.SIGHUP) # signal parent to incorporate PHONENO into shared voters_df row for this tentative voter
                    return
            else:
                # it is, itself, the id
#                assert selector in shelve or selector in voters_df.index
                self.id = selector
                return
        # must now satisfy selector.__class__ in [dict or pd.core.series.Series]:
        logging.debug('select Voter from '+str(selector))
        self.voters = Voter.select(selector)
        logging.debug(self.voters)
        if len(self.voters)==0: # 
            # no voters fit the selector criterion so
            if selector['PHONENO']:
                # if there was a phone number register this as a new voters
                voter = Voter(selector['PHONENO'])
                self.id = voter.id
                return
            else:
                # otherwise, not even a tentantive id may be returned
                self.id = None
        else:
            self.id = self.voters[0].id # if more than one voter returned by the query, arbitrarily return the first one 
    """
    # This is being replaced by network effect rewards for authenticated phone numbers declaring a delegate.
    @classmethod
    def process_newly_authorized(cls):
        if not 'NEWLY_AUTHORIZED' in shelve:
            return
        navdict = shelve['NEWLY_AUTHORIZED'] #maps phone to REGN_NUM (integer voter id)
        for navph in navdict:
            nav = Voter(navdict[navph])
            nav.mint(DELEGATE_MONEY_SUPPLY_PER_VOTER)
        del shelve['NEWLY_AUTHORIZED']
    """        
    @classmethod 
    def select(cls,selector):
        voters = [Voter(int(x)) for x in select(voters_REGN_NUM_df,selector).REGN_NUM]
#        desired_df = df.query(series_to_query(selector_series))
        logging.debug('returning voters: '+str([x.id for x in voters]))
        return voters

    @classmethod
    def indexed_ids(cls):
        return voters_REGN_NUM_df

    @classmethod
    def all(cls):   # TODO delete this method if not used anywhere?
        return list(voters_df.index)

    @property
    def id(self):
        return str(self.REGN_NUM) # for now, keep using the Iowa SoS voter registration number column name internally
    @id.setter
    def id(self,REGN_NUM):
        self.REGN_NUM = int(REGN_NUM) if REGN_NUM else REGN_NUM

    @property 
    def registration(self):# TODO delete this method if not used anywhere?
        return voters_df.loc[int(self.id)]

    def name_identification_string(self):
        if self.is_registered():
            first, middle, last, city = self.registration.loc[['FIRST_NAME','MIDDLE_NAME',"LAST_NAME",'CITY']]
            return f'{first} {middle} {last} of {city}'
        else:
            phone = self.PHONENO
            phone = re.sub(r'\d\d\d\d','XXXX',phone)
            return f'{phone} unregistered with the Iowa SoS'

    ###
    ## TODO the voters_df must be made shared memory between processes/threads with appropriate safeguards 
    #
    def get(self,prop):
        rn = self.id # use only for retrieving data not to be supplied by the Secretary of State 
        if not(rn in shelve):
            shelve[rn] = {} # can't rely on the shelve always having been initializd prior to access
        return voters_df.loc[int(self.id)][prop] if prop in voters_df.columns else shelve[rn][prop] if prop in shelve[rn] else None

    def set(self,prop,val):
        if prop in voters_df.columns:
            voters_df.loc[int(self.id)][prop] = val # must reconcile tentative data with secretary of state voter registration database
        pdict = shelve[self.id] # must keep tentative data consistent with voters data
        pdict[prop] = val
        shelve[self.id] = pdict
        shelve.sync()
    #
    ## TODO 
    ###

    def recall(self):
        self.default_delegate = None

    def is_registered(self):
#        logging.debug(f'{self.id} < {first_tentative_vid}')
        return int(self.id) < first_tentative_vid

    @property
    def delegates(self):
        # for now just one delegate per voter 
        delegdict = self.get('delegates')
        return {jurisdictionid:Voter(delegid) for (jurisdictionid,delegid) in delegdict.items()} if delegdict != None else {}
    @delegates.setter
    def delegates(self,delegatevotersdict):
        self.set('delegates',{jurisdictionid:voter.id for (jurisdictionid,voter) in delegatevotersdict.items()}) 
   
    @property
    def delegate_serial_number(self):
        dsn = self.get('delegate_serial_number')
        return dsn if dsn else 0
    @delegate_serial_number.setter
    def delegate_serial_number(self,dsn):
        self.set('delegate_serial_number',dsn)

    @property
    def default_delegate(self):
        # for now just one delegate per voter 
        delegdict = self.delegates
        return delegdict['default'] if len(delegdict)>0 else None
    @default_delegate.setter
    def default_delegate(self,delegatevoter):
        if delegatevoter != None and int(self.id)<first_tentative_vid and not(self.delegate_serial_number):
            # This is the first time this voter has specified a delegate while their phone number is in the Secretary of State's voter registrations
            # Assign a delegate_serial_number
            self.number_of_active_delegates += 1
            self.delegate_serial_number = self.number_of_active_delegates
            logging.info(f'Issuing delegate_serial_number: {self.delegate_serial_number}')
            activation_reward = NUMBER_OF_ACTIVATIONS_TO_REWARD - self.delegate_serial_number
            if activation_reward > 0:
                # mint delegate money accordingly.
                self.mint(activation_reward)
                logging.info(f'Issuing activation reward: {activation_reward}')
        delegdict = self.delegates 
        if delegatevoter:
            delegdict['default'] = delegatevoter
        elif 'default' in delegdict:
            del delegdict['default']
        self.delegates = delegdict

    @property
    def number_of_active_delegates(self):
        return shelve['number_of_active_delegates'] if 'number_of_active_delegates' in shelve else 0
    @number_of_active_delegates.setter
    def number_of_active_delegates(self,nad):
        shelve['number_of_active_delegates']=nad
        
    @property
    def votes(self):
        vtmp = self.get('votes')
        return vtmp if vtmp!= None else dict()
    @votes.setter
    def votes(self,votesdict):
        self.set('votes',votesdict)

#    @property
#    def voters(self):
#        vtmp = self.get('voters')
#        return vtmp if vtmp!= None else []
#    @voters.setter
#    def voters(self,voterslist):
#        self.set('voters',voterslist)

    def vote_on_bill(self,bill,cast):
        # for now, no per bill delegates
        myvotes = self.votes
        if myvotes == None:
            myvotes = dict()
        if cast=='absent':
            if bill in myvotes:
                del myvotes[bill]
        else:
            myvotes[bill]=cast
        self.votes = myvotes

    def vote(self,bill,cast):
        Transaction({'voter':self, 'resolution':bill, 'vote':cast})

    def pay(self,whom,amount):
        Transaction({'payer':self, 'amount':amount, 'payee':whom})

    def delegate(self,delegate, jurisdiction='default'):
        Transaction({'delegater':self, 'delegatee':delegate, 'jurisdiction':jurisdiction})

    def mint(self,amount):
        Transaction({'amount':amount, 'awardee':self})

    def escrow_bid(self,prop, amount): #  demurrage assessment is the high bid in escrow
        # all other bids are also assessed demurrage
        Transaction({'bidder':self, 'amount':amount, 'property':prop})
#    @property
#    def properties(self):
        
    def create_property(self, prop_description):
        prop = Property()
        prop.creator = self
        prop.description = prop_description
        return prop

    @property
    def wallet(self): #property money wallet is also assessed demurrage
        wallet_id = self.get('wallet_id') # this is a property id (str(uuid4()))
        if not(wallet_id):  # If need to create a wallet for this voter
            wallet = Property()
            self.wallet = wallet #this also records the id so self.balance setter works
            wallet_id = self.wallet.id
            self.balance = 0  #initialize the wallet's amount
            self.wallet_id = wallet_id
        return Property(wallet_id) 
    @wallet.setter
    def wallet(self,prop): # amount is floating point
        self.set('wallet_id',prop.id)

    @property
    def balance(self): #property money balance is also assessed demurrage
        return self.wallet.amount
    @balance.setter
    def balance(self,amount): # amount is floating point
        self.wallet.amount = amount

    def first_middle_last_of_city_string(self):
        return f'{" ".join([self.FIRST_NAME,self.MIDDLE_NAME,self.LAST_NAME])} of {self.CITY}' if self.is_registered() else f'The person at caller id {self.PHONENO}'

    @property
    def is_active(self):
            return self.default_delegate != None # don't consider a voter active until his delegate is specified


# generate property methods for columns        
voter_property_names = voters_df.columns.values 
for voter_property_name in voter_property_names:
    if not(re.match(r'[a-zA-Z][a-zA-Z0-9_]*$',voter_property_name)):
        continue    # skip names that can't be legal property names
    execstr = f'Voter.{voter_property_name} = property(lambda self: self.get("{voter_property_name}"), lambda self,x:self.set("{voter_property_name}",x))'
#    logging.debug(execstr)
    exec(execstr)
