#!/bin/bash

environ=$LAIN_DOMAIN

# specify the client id here
source /lain/app/config

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

default_server=$console_api_scheme"://console."$environ
api_server=${console_api_server:-$default_server}
# for we can not set empty "" in the previous line, set console_api_server="/" in config instead
if [ "$api_server" == "/" ];
	then api_server=""
fi


exec ./archon-0.1.linux.amd64 -sso-client-id=$client_id -api-server=$api_server -sso-server=$sso_server -entry-server=$ws_scheme"://entry."$environ -mode=frontend
