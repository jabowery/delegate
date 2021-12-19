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
import redisshelve
from redis import Redis
import os
from dotenv import load_dotenv
load_dotenv(override=True)

REDIS_SOCKET= os.getenv("REDIS_SOCKET")
def Redis_Connect(db=0):
#REDIS_SOCKET_URL=redis.from_url('unix://@/var/run/redis-myname/redis-server.sock')
#    return Redis(unix_socket_path=REDIS_SOCKET, db=db) if REDIS_SOCKET else Redis(db=db)
    return Redis(unix_socket_path=REDIS_SOCKET, db=db)
def Redis_Connect_Public_Audit(db=0):
#REDIS_SOCKET_URL=redis.from_url('unix://@/var/run/redis-myname/redis-server.sock')
    return Redis(db=db,port=6380)

transactions_shelve_db_number = os.getenv("REDIS_TRANSACTIONS_DB") or 0
transactions_redis = Redis_Connect_Public_Audit(db=transactions_shelve_db_number)
transactions_shelve = redisshelve.RedisShelf(redis=transactions_redis)

sessions_shelve_db_number = os.getenv("REDIS_SESSIONS_DB") or 1
sessions_redis = Redis_Connect(db=sessions_shelve_db_number)
sessions_shelve = redisshelve.RedisShelf(redis=sessions_redis)

voters_shelve_db_number = os.getenv("REDIS_VOTERS_DB") or 2
voters_redis = Redis_Connect(db=voters_shelve_db_number)
voters_shelve = redisshelve.RedisShelf(redis=voters_redis)

properties_shelve_db_number = os.getenv("REDIS_PROPERTIES_DB") or 4
properties_redis = Redis_Connect(db=properties_shelve_db_number)
properties_shelve = redisshelve.RedisShelf(redis=properties_redis)

def purge_all():
# to purge all shelves, in ipython execute:
#from shelves import *
    for x in ['properties','voters','transactions','sessions']:
        logging.debug(x)
        purge(x)
def purge(x):
    shelve = eval(x+'_shelve')
    for k in shelve:
#        print(f'deleting {k}: {shelve[k]}')
        print(f'deleting {k}')
        del shelve[k]
        shelve.sync()

def show(sn):
    shelve = eval(sn+'_shelve')
    for k in shelve:
        print(f'{k}:')
        print(f'{shelve[k]}')

