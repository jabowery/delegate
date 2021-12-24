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
import pandas as pd
import re
import json
import base64
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(override=True)
VOTING_DISTRICT = os.getenv("VOTING_DISTRICT")
STATE_OR_PROVINCE = os.getenv("STATE_OR_PROVINCE")

dd_path = Path('dynamic_data')
vu_path = Path('voter_downloads')
vu_filename = Path('all.csv')
vu_filepath = vu_path/vu_filename
v_filepath = dd_path/(f'{STATE_OR_PROVINCE}'+('_district{VOTING_DISTRICT}' if VOTING_DISTRICT else '')+'_voters.csv')
first_tentative_vid = int(1e10) # well beyond anything the Iowa SoS has allocated in its records

def bp(): 
    # breakpoint within server creating file blocking additional thread spawns
    # the file must be deleted to enable the server to continue spawning
    # e.g. see 'def respond'
    with open('nowdebugging','w') as f:
        print(' ',file=f)
    breakpoint()

def show_val(valname,val):
    logging.debug(f'{valname}.__class__: {val.__class__}')
    logging.debug(f'{valname}: {val}')

def phonemes_idx_sigma_match(phdists,sigma=1):
    midx = phdists.idxmin()
    minpd = phdists.min()
    meanpd = phdists.mean()
    stdpd = phdists.std()
    logging.debug(f'min {minpd} mean {meanpd} std {str(stdpd)}')
    return midx if stdpd/meanpd > (1/4) or sigma==0 else False

def not_None(isnoneq):
    return isnoneq.__class__ != None.__class__


def series_to_query(ser):
    query = ' and '.join([str(index)+'=='+'"'+str(value)+'"' for index,value in ser.items()])
    logging.debug(query)
    return query

def select(df,selector):
    if selector.__class__ == dict:
        selector = pd.Series(selector)
    desired_df = df.query(series_to_query(selector))
#    desired_df = df[pd.DataFrame([df[x]==selector_series[x] for x in selector_series.index.intersection(df.columns)]).all()]
    return desired_df

def select_indirect(full_df, indseries, selector):
    ###
    ## Select rows in a full_df via a highly indexed (multiindexed) intermediate that yields a simple index for df
    ## This is useful for situations in which it is desirable to populate the multiidex with data for fast lookup
    ## while retaining the ability to access that data with ordinary DataFrame syntax such as 'full_df[full_df.FIRST_NAME==name]'
    ##
    ## full_df: selecting from this DataFrame 
    ## indseries: A series possessing the queryable (multi)index yielding the index of full_df
    if indseries.__class__ == dict:
        indseries = pd.Series(indseries)
    narrowed_indseries_as_df = select(pd.DataFrame(indseries), selector)
    desired_df = full_df.loc[narrowed_indseries_as_df.iloc[:,0]] # There is only one data column (possessing the labels for full_df)
    return desired_df

def encode_client_state(client_obj):
    return base64.urlsafe_b64encode(json.dumps(client_obj).encode()).decode()

def decode_client_state(client_data):
#    logging.debug(type(client_data))
    return json.loads(base64.urlsafe_b64decode(client_data.encode()).decode())

def just_numbers(not_just_numbers):
    return re.sub(r'[^0-9]','',not_just_numbers)

import collections
class PhoneNumber(collections.UserString):
    # The main utility of this class is in touch tone UI where
    # entry of, say, 2352 can be imputed to have an area code and exchange
    # identical to that of the caller so that it is easier to identify
    # the person intended as, say, a delegate or, in the ultimate
    # system where a local currency is involved, the recipient of
    # payment.
    def default(self, obj):
        return json.dumps(self.e123)
    def normalize_phonenum(phonenum):
       return phonenum
    def __init__(self, USpn):
        super().__init__(USpn)
        USpn = self.data
        pn = re.sub(r'[^0-9]','',USpn)
        if len(pn)==11 and pn[0]=='1':
            pn = pn[1:]
        if len(pn)!=10:
            self.data = ''
            return
        self.area = pn[0:3]
        self.exchange = pn[3:6]
        self.station = pn[6:10]
        self.country = '1'
        self.e123 = '+'+self.country+self.area+self.exchange+self.station # E.123 standard format
        self.ten_digit = self.e123[2:]
        self.ten_digit_hyphenated = self.area+'-'+self.exchange+'-'+self.station
        self.data = self.ten_digit_hyphenated
#        if not(re.match(r'^\d\d\d-\d\d\d-\d\d\d\d$',str(self))):
#            raise ValueError(USpn,'is not a US complete phone number')
        
    def _asdict(self):
        return self.__dict__



