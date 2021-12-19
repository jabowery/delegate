#!/bin/bash -x
## Templated service file for redis-server(1)
# 
# Each instance of redis-server requires its own configuration file:
#
cp bak/redis.conf redis-delegate-private.conf
chown redis:redis redis-delegate-private.conf
#
# Ensure each instance is using their own database:
#
sed -i -e 's@^dbfilename .*@dbfilename dump-delegate-private.rdb@' redis-delegate-private.conf
#
# We then listen exlusively on UNIX sockets to avoid TCP port collisions:
#
sed -i -e 's@^port .*@port 0@' redis-delegate-private.conf
sed -i -e 's@^\(# \)\{0,1\}unixsocket .*@unixsocket /var/run/redis-delegate-private/redis-server.sock@' redis-delegate-private.conf
#
# ... and ensure we are logging, etc. in a unique location:
#
sed -i -e 's@^logfile .*@logfile /var/log/redis/redis-server-delegate-private.log@' redis-delegate-private.conf

sed -i -e 's@^daemonize yes@daemonize no@' redis-delegate-private.conf
sed -i -e 's@^supervised no@supervised auto@' redis-delegate-private.conf
sed -i -e 's@^pidfile@#pidfile@' redis-delegate-private.conf
sed -i -e 's@^appendfilename "appendonly.aof@appendfilename "appendonly-delegate-private.aof@' redis-delegate-private.conf

#
# We can then start the service as follows, validating we are using our own
# configuration:
#

systemctl stop redis-server@delegate-private.service
systemctl start redis-server@delegate-private.service
redis-cli -s /var/run/redis-delegate-private/redis-server.sock info | grep config_file
systemctl enable redis-server@delegate-private.service
#
