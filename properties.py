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
from shelves import properties_shelve as shelve
from uuid import uuid4,UUID
class Property:
    def __init__(self,propid=None):
        propid = propid or str(uuid4())
        uuid = UUID(propid) # exception raised if not valid UUID
        propid = str(uuid)  # ensure its a string
        if not(propid in shelve): # if should allocate a new property
            shelve[propid]={'id':propid}
        assert shelve[propid]['id'] == propid
        self.id = propid

    def get(self,prop):
        rn = self.id
        return  shelve[rn][prop] if prop in shelve[rn] else None

    def set(self,prop,val):
        pdict = shelve[self.id] 
        pdict[prop] = val
        shelve[self.id] = pdict
        shelve.sync()

    @property
    def creator(self):
        from voters import Voter
        return Voter(self.get('creator_id'))
    @creator.setter
    def creator(self,creator):
        self.set('creator_id',creator.id)

    @property
    def session(self):
        from call_session import Call_Session
        return Call_Session(self.get('session_id'))
    @session.setter
    def session(self,session):
        self.set('session_id',session.id)

    
    @property
    def amount(self): #property money amount is also assessed demurrage
        return self.get('amount')

        if not('amount' in shelve[self.id]):
                self.amount = 0
        return shelve[self.id]['amount']
    @amount.setter
    def amount(self,addamount): # amount is floating point
        pdict = shelve[self.id]
        pdict['amount'] = round(addamount,2)
        shelve[self.id] = pdict

    def add(self,addamount):
        self.amount += float(addamount) # float in case addamount is str

#class Wallet:

