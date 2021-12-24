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
# Input: voter_downloads/*.zip containing Voter registrations data downloaded from the Iowa Secretary of State in zip file format
# Output: all.csv which contains 
import logging
import os
import pandas as pd
import io
import csv
import zipfile
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(override=True)
from global_utils import vu_filepath, vu_path
#vu_path = Path('voter_downloads')
#vu_filename = 'all.csv'
#vu_filepath = vu_path/vu_filename # output file.
# Find candidate input file (latest download).
latest_vd_filepath = Path(sorted(map(lambda x: vu_path/x,filter(lambda xx: xx.find('.zip')>-1,os.listdir(vu_path))), key=os.path.getmtime)[-1])
if not(os.path.exists(vu_filepath)) or os.path.getmtime(latest_vd_filepath)>os.path.getmtime(vu_filepath):
    # A new update has arrived from the Iowa Secretary of state.  The current iowa_voters.csv is out of date.  Process it.
    outer_zf = zipfile.ZipFile(latest_vd_filepath)
    names = outer_zf.namelist()
    # If this is a zip within a zip, use the inner zip.
    zf = zipfile.ZipFile(outer_zf.open(names[0])) if len(names)==1 and names[0].find('.zip')>-1 else outer_zf
    vu_file = open(vu_filepath,'wb')
    csvwriter = csv.writer(io.TextIOWrapper(vu_file, encoding="utf-8"))
    rcnt = 0
    for name in zf.namelist():
#        allfp.write(zf.open(name).read())
        ###
        ## Reformat the output file to make it readable by pandas.read_csv
        ## Even though, in theory, the output file now exists, experience has shown
        ## the data arriving has varying numbers of fields in the rows, some of 
        ## which exceed the number of column headers in the first line of the csv.
        ## This makes pandas.read_csv throw an exception. As we use only  
        ## some of the first columns, these can be safely ignored by clipping
        ## their fields to eliminate the trailing columns.
        #
        this_rcnt = 0
        fieldcntrows = dict()
        csvreader = csv.reader(io.TextIOWrapper(zf.open(name), encoding="utf-8")) # TextIOWrapper necessary to kludge around brain damaged zipfile library
        for row in csvreader:
            rcnt += 1
            this_rcnt += 1
            if rcnt==1:
                expected_fields = row
            elif this_rcnt!=1:
                rowlen = len(row)
                if not(rowlen in fieldcntrows):
                    fieldcntrows[rowlen] = [expected_fields.copy()]
                fieldcntrows[rowlen].append(row)
                if len(expected_fields) < rowlen:
                    logging.debug(f'{rcnt}: {row[0]}...{row[len(expected_fields):]}')
                    row = row[:len(expected_fields)]
            else:
                continue
            csvwriter.writerow(row)
        logging.debug({rowlen:len(fieldcntrows[rowlen]) for rowlen in fieldcntrows.keys()})
    zf.close()
    outer_zf.close()
    ###
    ## Write out separate files for each different field number encounterd.
    ## This is for diagnostic purposes.
    ##
    for fieldcnt in fieldcntrows.keys():
        csvfilepath = vu_path/f'fieldcnt{fieldcnt}{name}'
        csvfilepath.parent.mkdir(parents=True,exist_ok=True)
        with open(csvfilepath, 'w') as csvfile:
            csvwriter2 = csv.writer(csvfile)
            for row in fieldcntrows[fieldcnt]:
                csvwriter2.writerow(row)
    #
    ## Wrote out separate files for each different field number encounterd.
    ###
    ###
    ## Deal with duplicate REGN_NUM rows coming in from the SoS office.
    #
    vu_file.close()
    voters_df = pd.read_csv(vu_filepath,index_col=['REGN_NUM'],dtype=str,skipinitialspace=True,parse_dates=['LAST_UPDATED_DATE'],infer_datetime_format=True).fillna(value='')
#    voters_df = pd.read_csv(vu_filepath,index_col=['REGN_NUM'],dtype=str,skipinitialspace=True).fillna(value='')
    dup_entries = voters_df.index.duplicated(keep=False)
    dup_df = voters_df.loc[dup_entries]
    if len(dup_df):
        # There were duplicates.
        dup_df.to_csv(vu_path/'duplicate_REGN_NUMs.csv') # Write out a file to notify the SoS of which rows were duplicate REGN_NUMs
        voters_df = voters_df.sort_values('LAST_UPDATED_DATE')
        voters_df = voters_df[~voters_df.index.duplicated(keep='last')]
        voters_df.sort_index()
        voters_df.to_csv(vu_filepath)
    #
    ## Dealt with duplicate REGN_NUM rows coming in from the SoS office.
    ###
    # 
    ## Reformated the output file to make it readable by pandas.read_csv
    ###
