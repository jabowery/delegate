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
from global_utils import dd_path
import logging
from shelves import transactions_shelve as shelve
from properties import Property
import time
from pathlib import Path
import os
from dotenv import load_dotenv
load_dotenv(override=True)
audit_log_filepath = os.getenv('AUDIT_LOG') or f'{dd_path}/audit_log.txt'
audit_log_filepath = Path(audit_log_filepath)
if not(audit_log_filepath.exists()):
    audit_log_filepath.parent.mkdir(parents=True,exist_ok=True)
    audit_log_filepath.touch()

def prepend(subject, predicate, amount, object_of):
    line = ' '.join(
        [
        'At',
        time.asctime(),
        subject.name_identification_string() if not(type(subject) == str) else subject,
        predicate,
        amount,
        object_of.name_identification_string() if not(type(object_of) == str) else object_of,
        "\n"
        ]
    )
    with open(audit_log_filepath, 'r+') as audit_log_file:
        content = audit_log_file.read()
        audit_log_file.seek(0)
        audit_log_file.write(line + content)

class Transaction():
    def __init__(self,xaction):
        if type(xaction) == str:
            assert xaction in shelve # if initialized with a string it must be a transaction id
            self.id = xaction
            return
        # .id is an integer but must be convered to a string
        # An integer id is required to ensure redis provides sorted presentation.
        self.id = str(time.time_ns())
        if 'amount' in xaction:
            amt = round(float(xaction['amount']),2)
            str_amt = '${:,.2f}'.format(amt)
            xaction['amount'] = amt
        if 'payer' in xaction:
            payer = xaction['payer']
            payee = xaction['payee']
            ###
            ## critical section begin
            #
            shelve[self.id] = {'payer':payer.id, 'payee':payee.id, 'amount':amt}
            payer.wallet.add(0-amt)
            payee.wallet.add(amt)
            #
            ## critical section end
            ##
            prepend(payer,'pays',f'{str_amt} to',payee)
        elif 'bidder' in xaction:
            bidder = xaction['bidder']
            prop = xaction['property']
            ###
            ## critical section begin
            #
            shelve[self.id] = {'bidder':bidder.id, 'property':prop.id, 'amount':amt}
            prop.escrow_bid(bidder,amt)
            #
            ## critical section end
            ##
            prepend(bidder,'bids', f'{str_amt} for',prop)
        elif 'awardee' in xaction: # issue newly minted delegate dollars
            awardee = xaction['awardee']
            shelve[self.id] = {'awardee':awardee.id, 'amount':amt}
            awardee.wallet.add(amt)
            prepend('The Delegate Network for Iowa','awards',f'{str_amt} of the total $2B delegate money to founding registrant',awardee)
        elif 'delegatee' in xaction: 
            delegatee = xaction['delegatee']
            delegater = xaction['delegater']
            jurisdictionid = xaction['jurisdiction']
            assert jurisdictionid =='default'  #non-default jurisdictions are not yet supported
            delegater.default_delegate = delegatee
            shelve[self.id] = {'delegater':delegater.id, 'delegatee':delegatee.id, 'jurisdiction':jurisdictionid}
            prepend(delegater,'delegates','->',delegatee)
        elif 'voter' in xaction:
            voter = xaction['voter']
            bill = xaction['resolution']
            vote = xaction['vote']
            voter.vote_on_bill(bill, vote)
            shelve[self.id] = {'voter':voter.id, 'bill':bill, 'vote':vote}
            prepend(voter,'votes',f'{vote} on bill',bill)
    def escrow_bid(self,bidder,amt):
        bidder.wallet.debit(amt)
        bids = self.bids
        if not(bidder.id in bids):
            bids[bidder.id] = Property()
        bidchange = amt - bids[bidder.id] 
        bidder.wallet.add(-bidchange)
        bids[bidder.id].add(bidchange)

    def get(self,prop):
        return shelve[self.id][prop] if prop in shelve[self.id] else None

    def set(self,prop,val):
        pdict = shelve[self.id]
        pdict[prop] = val
        logging.debug(prop,val+str(pdict[prop]))
        shelve[self.id] = pdict
        shelve.sync()
