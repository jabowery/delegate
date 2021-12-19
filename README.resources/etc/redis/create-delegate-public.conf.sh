#!/bin/bash -x
## Templated service file for redis-server(1)
# 
# Each instance of redis-server requires its own configuration file:
#
cp bak/redis.conf redis-delegate-public.conf
chown redis:redis redis-delegate-public.conf
#
# Ensure each instance is using their own database:
#
sed -i -e 's@^dbfilename .*@dbfilename dump-delegate-public.rdb@' redis-delegate-public.conf
#
# ... and ensure we are logging, etc. in a unique location:
#
sed -i -e 's@^logfile .*@logfile /var/log/redis/redis-server-delegate-public.log@' redis-delegate-public.conf

sed -i -e 's@^daemonize yes@daemonize no@' redis-delegate-public.conf
sed -i -e 's@^supervised no@supervised auto@' redis-delegate-public.conf
sed -i -e 's@^pidfile@#pidfile@' redis-delegate-public.conf
sed -i -e 's@^appendfilename "appendonly.aof@appendfilename "appendonly-delegate-public.aof@' redis-delegate-public.conf


#
# listen only on the public IP4 address
#
if [ -z "$1" ]
then
	MY_HOSTNAME=$(hostname)
	MY_IP=$(dig +short $MY_HOSTNAME)
	OCTTT=$(echo $MY_IP | cut -c1-3)
	if [[ $OCTTT == '127' ]]
	then
		echo "You will have to specify your public IP address."
		echo "$0 <public_IP_address>"
		exit 1 
	fi
else
	MY_IP=$1
fi
echo "MY_IP: $MY_IP"
sed -i -e "s@^bind.*@bind $MY_IP@" redis-delegate-public.conf

#
# replicate from localhost's private redis port (6380)
#
sed -i -e 's@^# replicaof <masterip> <masterport>@replicaof 127.0.0.1 6380@' redis-delegate-public.conf

sed -i '/^# Command renaming..*/a rename-command CONFIG ""\nrename-command DEBUG ""' redis-delegate-public.conf

#
# We can then start the service as follows, validating we are using our own
# configuration:
#
systemctl stop redis-server@delegate-public.service
systemctl enable redis-server@delegate-public.service
systemctl start redis-server@delegate-public.service
redis-cli -h $MY_IP info | grep config_file
