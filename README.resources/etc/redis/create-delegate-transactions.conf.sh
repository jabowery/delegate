#!/bin/bash -x
## Templated service file for redis-server(1)
# 
# Each instance of redis-server requires its own configuration file:
#
cp bak/redis.conf redis-delegate-transactions.conf
chown redis:redis redis-delegate-transactions.conf
#
# Ensure each instance is using their own database:
#
sed -i -e 's@^dbfilename .*@dbfilename dump-delegate-transactions.rdb@' redis-delegate-transactions.conf
#
# ... and ensure we are logging, etc. in a unique location:
#
sed -i -e 's@^logfile .*@logfile /var/log/redis/redis-server-delegate-transactions.log@' redis-delegate-transactions.conf

#
# provide private localhost replication service on localhost port 6380 (rather than 6379 which is used for public IP's repliation service)
#
sed -i -e 's@^port 6379@port 6380@' redis-delegate-transactions.conf

#
# 
sed -i -e 's@^daemonize yes@daemonize no@' redis-delegate-transactions.conf
sed -i -e 's@^supervised no@supervised auto@' redis-delegate-transactions.conf
sed -i -e 's@^pidfile@#pidfile@' redis-delegate-transactions.conf
sed -i -e 's@^appendfilename "appendonly.aof@appendfilename "appendonly-delegate-transactions.aof@' redis-delegate-transactions.conf

#
# We can then start the service as follows, validating we are using our own
# configuration:
#
systemctl stop redis-server@delegate-transactions.service
systemctl enable redis-server@delegate-transactions.service
systemctl start redis-server@delegate-transactions.service
redis-cli -h 127.0.0.1 -p 6380 info | grep config_file
