#!/bin/bash

environ=$LAIN_DOMAIN

cd /lain/app/archon-0.1/

exec ./archon-0.1.linux.amd64 -sso-client-id=3 -api-server="http://console."$environ -sso-server="http://sso."$environ -mode=frontend