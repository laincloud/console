#!/bin/bash

environ=$LAIN_DOMAIN
ssoserver="https://sso.yxapp.in"
console_api_scheme="http"

if [ "$environ" = "yxapp.in" ]; then
    clientid=7
    clientsec="n-33rREkju-yTRs1dCmDxA"
    console_api_scheme="https"
elif [ "$environ" = "yxapp.xyz" ]; then
    clientid=23
    clientsec="7bnsvPR6keTMTyoUIQzOIA"
    console_api_scheme="https"
elif [ "$environ" = "lain.local" ]; then
    clientid=9
    clientsec="WGwJ4lc8dcDc8913wqd-pw=="
    ssoserver="http://sso.lain.bdp.cc"
fi

export SSO_CLIENT_ID=$clientid
export SSO_CLIENT_SECRET=$clientsec
export SSO_SERVER_NAME=$ssoserver
export CONSOLE_API_SCHEME=$console_api_scheme
export CONSOLE_LOG_LEVEL="INFO"
export CONSOLE_APISERVER="http://deployd.lain:9003"

exec gunicorn -w 3 -b 0.0.0.0:8000 --max-requests=100 --preload --error-logfile logs/error.log --access-logfile logs/access.log console.wsgi 
