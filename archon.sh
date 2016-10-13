#!/bin/bash

environ=$LAIN_DOMAIN

# specify the client id here
source ./config

cd /lain/app/archon-0.1/

exec ./archon-0.1.linux.amd64 -sso-client-id=$client_id -api-server="http://console."$environ -sso-server="http://sso."$environ -mode=frontend