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
# INPUT voters_df (symbolic linked to the unscrambled iowa_3rd_district_voters.csv)
# OUTPUT iowa_3rd_district_voters_scrambled.csv
# anonomize the iowa voters database for publication in open source work

from voters_df import voters_df, v_filepath

import random
import re
import os
from dotenv import load_dotenv
load_dotenv(override=True)

#VOTING_DISTRICT = os.getenv("VOTING_DISTRICT")
#STATE_OR_PROVINCE = os.getenv("STATE_OR_PROVINCE")

voters_df = voters_df
vnum = len(voters_df)
vscr = voters_df.copy()
male_df = voters_df[voters_df.GENDER=='male']
female_df = voters_df[voters_df.GENDER=='female']

def pick_row(df):
    return random.randint(0,len(df)-1)

def valscr(row, colname):
    nv = voters_df.iloc[pick_row(voters_df)][colname]
    row.loc[colname] = nv
    return row

def namescr(column,ndf):
    phoneme_column = re.sub('_NAME','',column)+'_PHONEMES'
    return ndf.iloc[pick_row(ndf)][[column,phoneme_column]]

def dig():
    return '0123456789'[random.randint(0,9)]
voters_df.loc[:,'MAILING_ADDRESS'] = '' #wipe out difficult to scramble identifying field
for rowi in range(0,len(voters_df)):
    row = vscr.iloc[rowi]
    ndf = male_df if row.GENDER == 'male' else female_df
    nrow = row.copy()
    for namecol in ['FIRST_NAME','MIDDLE_NAME','LAST_NAME']:
        nname = namescr(namecol,ndf)
        nrow.loc[nname.index] = nname.values
    for valcol in ['STREET_NAME','BIRTHDATE','PARTY','UNIT_TYPE','UNIT_NUM']:
        nrow = valscr(nrow, valcol)
    nrow.PHONENO = nrow.PHONENO[:-4]+dig()+dig()+dig()+dig()
    vscr.loc[row.name] = nrow
v_filepath_scrambled = re.sub(r'\.csv','_scrambled.csv',str(v_filepath))
vscr.to_csv(v_filepath_scrambled)
    
