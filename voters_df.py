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
import Levenshtein as lev
import panphon.distance
#from espeakng import ESpeakNG
import os
import re
import pandas as pd
import numpy as np
from nicknames import NameDenormalizer
from multiprocess import Pool
#import zipfile
#import subprocess
#from shelves import sessions_shelve
from shelves import voters_shelve
from global_utils import vu_filepath, v_filepath, first_tentative_vid
#from shelves import properties_shelve
from dotenv import load_dotenv
load_dotenv(override=True)

VOTING_DISTRICT = os.getenv("VOTING_DISTRICT")

#third_congressional_district_counties = ['guthrie','dallas','polk','warren','madison','adair','cass','pottawattamie','mills','montgomery','adams','union','fremont','page','taylor','ringgold']
#third_congressional_district_county_REP_chairs =['therese davis','ronald forsell','gloria mazza','mark snell']
logging.debug('executing voters_df.py')
all_possibilities = dict()
all_words = set()
var_to_words = dict()
phonemes_cache = pd.Series(dict(),dtype=object) # make it an empty series of the right dtype
def populate_all_possibilities():
    global phonemes_cache, all_words, var_to_words, all_possibilities
    # Prepopulate word dictionaries including phoneme cache.  (Phoneme generation is resource intensive.)
    for varname in ['county','city','last','first','middle']:
        logging.debug(varname)
        try:
            all_possibilities[varname] = pd.read_csv(f'dynamic_data/{varname}2phonemes.csv',index_col=0,dtype=str, squeeze=True, na_filter=False,skipinitialspace=True)
        except:
            all_possibilities[varname] = pd.Series(dict(),dtype=object) # make it an empty series of the right dtype
            # If a phoneme file doesn't exist, it will exist the next time a voter update arrives.
            # See the if conditioned block below processing updates.
        phonemes_cache = pd.Series(phonemes_cache.to_dict() | all_possibilities[varname].to_dict())
#        # TODO replace this loop with the appropriate |= operation
#        for word in all_possibilities[varname].keys():
#            phonemes_cache[word] = all_possibilities[varname][word]
        var_to_words[varname] = all_possibilities[varname].keys() # is this really necessary?
    all_words = set(phonemes_cache.keys()) # is this really necessary?
#    phser = pd.Series(phonemes_cache)
#esng = ESpeakNG(voice='en-us') #for phonemeization of text  See my_phonemize
#def my_phonemize(txt):
#    ipa = esng.g2p(txt, ipa=2) if len(txt) else ''
##    logging.debug('phonemizing '+str(txt))
#    return ipa
def my_phonemize(word):
    import subprocess
    # this is the comand produced by the above commented out my_phonemize
    # to verify, import logging and then set level to DEBUG to see the command produced by the call to g2p
    if word in phonemes_cache:
        return phonemes_cache[word]
    cmd = ['espeak-ng', '-a', '100', '-k', '0', '-l', '0', '-p', '50', '-s', '175', '-v', 'en-us', '-b', '1', '-q', '--ipa=2']
#    pairs = []
    phs = subprocess.run(cmd+[word], capture_output=True,encoding='UTF-8').stdout
    phonemes_cache[word] = phs
    return (phs)
def my_phonemize_cached(txt,field_name):
#    if not(txt in all_possibilities[field_name]):
#            logging.debug(txt+str(field_name))
#    txtph = all_possibilities[field_name][txt] if txt in all_possibilities[field_name] else my_phonemize(txt)
    txtph = my_phonemize(txt) # caching now backed by my_phonemize itself
    all_possibilities[field_name][txt] = txtph #ensure it's cached for this field's values
    return txtph

nicknames = NameDenormalizer()

def my_first_name_homonyms(first_name):
    fnp = my_phonemize_cached(first_name,'first')
    aps = pd.Series(all_possibilities['first'])
    return set(aps[aps==fnp].index) # return the set of names that sound the same as first_name
def nicknames_of_homonyms(first_name):
    nicks = set()
    for homonym in my_first_name_homonyms(first_name):
        nicks |= set(nicknames.get(homonym)).copy()
    return nicks


dst = panphon.distance.Distance()
def my_phonemes_distance(ps1,ps2,str1=None,str2=None):
#        str12 = ' '.join([str1.lower(),str2.lower()])
#        if str12.find('hoppmann')>-1 or str12.find('hoskins')>-1:
#            with open('nowdebugging','w') as f:
#                logging.debug(' '+str(file=f))
        pd1 = dst.dogol_prime_distance(ps1,ps2)

        pd2 = ((ps1[0]!=ps2[0])+(ps1[-1]!=ps2[-1]) if len(ps1)*len(ps2) else 2) # bias in favor of first+last phoneme match
        if str1==None:
            pd3 = 0
            pd4 = 0
            pd5 = 0
        elif len(str1)*len(str2):
            pd3 = ((str1[0]!=str2[0])+(str1[-1]!=str2[-1]))/2 # bias in favor of first+last character match
            pd4 = 4*abs(len(str1)-len(str2))/((len(str1)+len(str2))/2) # more severly punish length differences
            pd5 = lev.distance(str1,str2)/2 # bias in favor of near spellings
        else: # one of the strings is null
            pd3 = 2/2
            pd4 = 4/2
            pd5 = abs(len(str1)-len(str2))/2
        td = pd1+pd2+pd3+pd4+pd5
#        logging.debug(td,pd1,pd2,pd3,pd4,pd5,ps1,ps2,str1+str(str2))
        return td
my_phonemes_distance_cache =  pd.Series([0.0],index=pd.MultiIndex(levels=[[''],[''],[''],['']],codes=[[0],[0],[0],[0]],names=['ps1','ps2','str1','str2']))
def my_phonemes_distance_cached(ps1,ps2,str1='',str2=''):
    if not((ps1,ps2,str1,str2) in my_phonemes_distance_cache):
            my_phonemes_distance_cache.loc[ps1,ps2,str1,str2] = my_phonemes_distance(ps1,ps2,str1,str2)
    return my_phonemes_distance_cache.loc[ps1,ps2,str1,str2]


var_to_column_name = {'city':'CITY', 'county':'COUNTY', 'zip_code':'ZIP_CODE', 'last':'LAST_NAME', 'first':'FIRST_NAME', 'middle':'MIDDLE_NAME', 'street_name':'STREET_NAME', 'phone':'PHONENO'}  # the order of this dict is no longer important (see 'select_indirect')
keep_data_columns = ['PRECINCT','TOWNSHIP','GENDER','NAME_SUFFIX','EFF_REGN_DATE', 'LAST_UPDATED_DATE', 'HOUSE_NUM','HOUSE_SUFFIX','STREET_TYPE','BIRTHDATE','PARTY','CONGRESSIONAL','UNIT_TYPE','UNIT_NUM','VOTERSTATUS', 'MAILING_ADDRESS', 'CITY.1','STATE.1', 'ZIP_CODE.1','ZIP_PLUS.1','PRE_DIR','POST_DIR']
def lower_all_but_phonemes(df): # normalize dataframe to lower case except for phonemes
    df = df.fillna(value='')
    for colname in df.columns:
        if colname.find('PHONEME') > -1:
            next
        df[colname] = df[colname].apply(lambda x: x.lower())
    return df
def fnph(df):
    if df.__class__ == str:
        return my_phonemize_cached(df,'first')
    else:
        return pd.Series({x: my_phonemize_cached(x,'first') for x in df})
def mnph(df):
    return my_phonemize_cached(df,'middle')
def lnph(df):
    return my_phonemize_cached(df,'last')
def ciph(df):
    return my_phonemize_cached(df,'city')
def coph(df):
    return my_phonemize_cached(df,'county')

v_exists = os.path.exists(v_filepath)
vu_exists = os.path.exists(vu_filepath ) 
if     (v_exists and vu_exists and os.path.getmtime(vu_filepath) > os.path.getmtime(v_filepath)
    or
        not(v_exists) and vu_exists):
    # A new update has arrived from the Iowa Secretary of state.  The current iowa_3rd_district_voters.csv is out of date.  Recompile it.
    # At present it is necessary to execute this file on its own (python voters_df.py) -- not from within a threading server.
    # TODO make the following data import's use of from multiprocessing import Pool work even if invoked within a threading WSGI server.
    # 
    populate_all_possibilities() # prepopulate the phoneme cache so this doesn't take so long
#   phonemes_cache = pd.read_csv('phonemes_cache.csv').to_dict()
    voters_df = pd.read_csv(vu_filepath,index_col=['REGN_NUM'],dtype=str,skipinitialspace=True).fillna(value='')
    if VOTING_DISTRICT:
        voters_df = voters_df[voters_df.CONGRESSIONAL == VOTING_DISTRICT] 
    else:
        logging.debug('WARNING:  No VOTING_DISTRICT was configured.  Importing everything.')
    voters_df = lower_all_but_phonemes(voters_df)   # normalize to lower case rather than upper

    voters_df = voters_df[list(var_to_column_name.values())+keep_data_columns] # keep only essential columns

    ###
    ## Convert direction abbreviations to full words in city names.
    #
    dhash = {'w':'west','n':'north','e':'east','s':'south'}
    def subdirection(nsew): #e.g. convert 'w des moines' to 'west des moines'
        return dhash[nsew.group(1)]+(dhash[nsew.group(2)] if nsew.group(2) else '')+' '
    logging.debug(voters_df.CITY)
    voters_df.CITY = voters_df.CITY.apply(lambda x: re.sub(r'^([nsew])([nesw])?\.? ',subdirection, x))
    #
    ## Converted direction abbreviations to full words in city names.
    ###

    ###
    ## Add phoneme columns to voters_df
    #
    ###
    ## Encache phonemes of newly encountered words
    #
    ###
    ## Include nicknames (possibly not already in possible first names)
    #
    nickset = set()
    for nick in nicknames.lookup: # put all nicknames into nickset
        for subnick in nicknames.lookup[nick]:
            nickset |= subnick
    var_to_words['first'] = var_to_words['first'].union(nickset)
    all_words |= nickset
    #
    ## Included nicknames (possibly not in possible first names)
    ###
    ###
    ## Include all values from the relevant columns.
    #
    for varname in ['county','city','last','first','middle']:
        var_to_words[varname] = var_to_words[varname].union(set(voters_df[var_to_column_name[varname]].unique()))
        all_words |= set(var_to_words[varname])
    #
    ## Included all values from the relevant columns.
    ###
    ###
    ## Phonemize, in parallel all the new words.
    #
    new_words = all_words - set(phonemes_cache.keys()) # phonemize only the new words
    logging.debug('multiprocessing start')
    with Pool(45) as pool:
        new_phonemes_cache = pool.map(my_phonemize,new_words) #my_phonemize doesn't internally cach within a multiprocess pool instance
        new_phonemes_cache = dict(zip(new_words,new_phonemes_cache)) # that's why it has to be cached here, prior to my_phonemize_df below
        phonemes_cache = pd.Series(phonemes_cache.to_dict() | new_phonemes_cache)
    logging.debug('multiprocessing end')
    #
    ## Phonemized, in parallel all the new words.
    ###
    ###
    ## Update field specific phoneme caches.
    #
    for varname in ['county','city','last','first','middle']:
        all_possibilities[varname] = pd.Series({word:phonemes_cache[word] for word in var_to_words[varname]})
    #
    ## Updated field specific phoneme caches.
    ###
    #
    ## Encached phonemes of newly encountered words
    ###

    def my_phonemize_df(df): # This relies on the caches being prepared as above for speed
        df['FIRST_PHONEMES']=voters_df['FIRST_NAME'].apply(fnph)
        df['MIDDLE_PHONEMES']=voters_df['MIDDLE_NAME'].apply(mnph)
        df['LAST_PHONEMES']=voters_df['LAST_NAME'].apply(lnph)
        df['CITY_PHONEMES']=voters_df['CITY'].apply(ciph)
        df['COUNTY_PHONEMES']=voters_df['COUNTY'].apply(coph)
        return df

#    voters_df =  my_phonemize_df(voters_df)
    logging.debug('df multiprocessing start')
    with Pool(45) as pool:
        voters_df['FIRST_PHONEMES']=pool.map(fnph,voters_df.FIRST_NAME)
        voters_df['MIDDLE_PHONEMES']=pool.map(mnph,voters_df.MIDDLE_NAME)
        voters_df['LAST_PHONEMES']=pool.map(lnph,voters_df.LAST_NAME)
        voters_df['CITY_PHONEMES']=pool.map(ciph,voters_df.CITY)
        voters_df['COUNTY_PHONEMES']=pool.map(coph,voters_df.COUNTY)
#        new_voters_voters_df[= pool.map(my_phonemize_df,voters_df) 
#        new_phonemes_cache = dict(zip(new_words,new_phonemes_cache)) # that's why it has to be cached here, prior to my_phonemize_df below
#        phonemes_cache = pd.Series(phonemes_cache.to_dict() | new_phonemes_cache)
    logging.debug('df multiprocessing end')
    #
    ## Added phoneme columns to voters_df
    ###

    ###
    ## Normalize to 10 digit hyphenated
    #
    voters_df.loc[np.logical_not(voters_df.PHONENO.notna()),'PHONENO']=''
    voters_df['PHONENO'] = [re.sub(r'(\d\d\d)(\d\d\d)(\d\d\d\d)',r'\1-\2-\3',re.sub(r'^1','',re.sub(r'[^0-9]','',x))) for x in voters_df.PHONENO]
    voters_df['PHONENO'] = [x if len(x)==12 else '' for x in voters_df.PHONENO]
    #
    ## Normalized to 10 digit hyphenated
    ###

    voters_df.to_csv(v_filepath)
    logging.debug('phonemized voters_df written out')
    for varname in ['county','city','last','first','middle']:
        logging.debug(varname+str(len(all_possibilities[varname])))
        all_possibilities[varname].to_csv('dynamic_data/'+varname+'2phonemes.csv')
    logging.debug('per-field phonemes written out')

###
## Read everything in as though the prior condition failed to update from the SoS's voter registration database
#
#voters_df                   = pd.read_csv('dynamic_data/voters_df.csv',index_col='REGN_NUM',dtype=str, na_filter=False, skipinitialspace=True)
voters_df                   = pd.read_csv('dynamic_data/voters_df.csv',dtype=str, na_filter=False, skipinitialspace=True)
voters_df.REGN_NUM = [int(x) for x in voters_df.REGN_NUM]
voters_df = voters_df.set_index('REGN_NUM')
voter_cols = voters_df.columns
populate_all_possibilities()

debugging_voters_filepath = 'debug_data/debugging_voters.csv'
if os.path.exists(debugging_voters_filepath):
    ###
    ## Append debugging voters.
    ## These must be assigned REGN_NUM values just below first_tentative_vid so as not to interfere.
    ## Interference would involve:
    ##  Occupying vids within the registered voters.
    ##  Occupyong vids within the tentative voters.
    ##  Altering the maximum vid (telling where additional tenativ vids are to be allocated).
    #
    debugging_voters_df = pd.read_csv(debugging_voters_filepath, index_col=['REGN_NUM'], dtype=str,skipinitialspace=True).fillna(value='')
    debugging_voters_df = lower_all_but_phonemes(debugging_voters_df) #normalize debugging data to lower as with voters_df

    for REGN_NUM in debugging_voters_df.index:
        row = debugging_voters_df.loc[REGN_NUM]
        for varname in ['county','city','last','first','middle']: # debugging rows must define all of the corresponding columns
#            vnap = all_possibilities[varname]
#            row.loc[(varname+'_PHONEMES').upper()] = vnap[row.loc[var_to_column_name[varname]]] 
            row.loc[(varname+'_PHONEMES').upper()] = my_phonemize_cached(row.loc[var_to_column_name[varname]],varname)
        voters_df.loc[REGN_NUM] = row
    #
    ## Appended debugging voters.
    ###

def add_tentative_voters(signum, frame):
    global voters_df, voters_REGN_NUM_df
    if not('last_vid' in voters_shelve):
        # initialize last voter id to be allocated
        voters_shelve['last_vid'] = first_tentative_vid-1    # to be the one just before the first to be allocatd
    last_vid = voters_shelve['last_vid'] 
    serlist = []
    logging.debug('last_vid '+str(last_vid))
    ###
    ## Add tentative voters to the voters DataFrame
    #
    for vid in range(first_tentative_vid,last_vid+1):
        if not(str(vid) in voters_shelve): 
            # this tentative registration slot has been vacated
            # skip this
            # TODO during the voter registration import it may be discovered this voter has been validated by the SoS
            #  in which case the data here should PREVIOUSLY (see below) have been moved to the validated range of REGN_NUMs
            continue
        if vid in voters_df.index:
            continue
        vdict = voters_shelve[str(vid)]
        logging.debug(vdict)
        if vdict['PHONENO'] in voters_df.PHONENO.values: # is it now among the registered voters?
            ###
            ## Migrate this voter to their validated REGN_NUM
            #
            this_voter_REGN_NUM = voters_df[voters_df.PHONENO == vdict['PHONENO']].iloc[0].name #TODO: handle case where more than one voter share a phone (note: '[0]' is arbitrary in this case)
            logging.debug(f'Delegate newly authorized with tentative vid: {vid}, changing to Secretary of State authorized vid: {this_voter_REGN_NUM}')
            #TODO reward recruiter of this delegate with delegate money by asking this delegate who recruited them and making that person this voter's default delegate
#            vdict['NEWLY_AUTHORIZED'] = True # flag this delegate as newly authorized so that the next time they phone in they're appropriately queried about who recruited them
            voters_shelve[str(this_voter_REGN_NUM)] = vdict
            voters_shelve[vdict['PHONENO']] = this_voter_REGN_NUM
            del voters_shelve[str(vid)]  # copy shelved data to registered voter id #TODO: what about overlapping fields as in the intersection below?
#            nadict = voters_shelve['NEWLY_AUTHORIZED'] 
#            nadict[vdict['PHONENO']] = this_voter_REGN_NUM
#            voters_shelve['NEWLY_AUTHORIZED'] = nadict  #queue up work to be done for the newly authorized phone numbers.  See delegate.py where it ('needlessly' imports call_sessions so as to indirectly import this module and only then import voters.Voter)
            continue
        mycols = voter_cols.intersection(vdict.keys()) #TODO: Is the only overlapping field PHONENO when a phone doesn't appear in the SoS registered voters?
        vdict = {x:vdict[x] for x in mycols}
        row = pd.Series(vdict,index = voter_cols,name=vid)

        if vid in voters_df.index:
            voters_df.loc[vid][row.index] = row.values
        else:
            serlist.append(row)
    ###
    ## Work around for bug 
    voters_df_index_name = voters_df.index.name
    voters_df = voters_df.append(serlist)
    voters_df.index.name = voters_df_index_name
    #
    ## Added tentative voters to the voters DataFrame
    ###
    voters_REGN_NUM_df = pd.DataFrame(voters_df.index.values,index=pd.MultiIndex.from_frame(voters_df[var_to_column_name.values()]),columns=['REGN_NUM'])

    logging.debug('tables read in')
add_tentative_voters(None,None)
#
## Read everything in as though the prior condition failed to update from the SoS's voter registration database
###

import signal
signal.signal(signal.SIGHUP,add_tentative_voters) # permit child processes to add tentaive voters to their local voters_df and signal the shared voters_df be updated
root_pid = os.getpid() # can now os.kill(root_pid, signal.SIGHUP) whenever voters_shelve has a new tentative voter to be updated in the shared voters_df

