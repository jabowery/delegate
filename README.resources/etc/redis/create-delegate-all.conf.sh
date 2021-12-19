#!/bin/bash -x
./create-delegate-private.conf.sh
./create-delegate-transactions.conf.sh
./create-delegate-public.conf.sh $1
