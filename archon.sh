#!/bin/bash

environ=$LAIN_DOMAIN

# specify the client id here
source ./config

if [ $console_api_scheme == "https" ]; then
	ws_scheme="wss";
elif [ $console_api_scheme == "http" ]; then
	ws_scheme="ws";
else
	echo "console_api_scheme is not defined"
	exit 1
fi

sso_server=${sso_server:-"http://sso."$environ}

cd /lain/app/archon-0.1/

exec ./archon-0.1.linux.amd64 -sso-client-id=$client_id -api-server=$console_api_scheme"://console."$environ -sso-server=$sso_server -entry-server=$ws_scheme"://entry."$environ -mode=frontend
