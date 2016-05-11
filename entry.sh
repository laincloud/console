#!/bin/bash

environ=$LAIN_DOMAIN
clientid=3
clientsec="secret"
console_api_scheme="https"

# specify the client id, client secret and sso server here
if [ "$environ" = "lain.local" ]; then
    clientid=3
    clientsec="secret_in_local"
    redirecturi="https://example.com"
    console_api_scheme="http"
fi

export SSO_CLIENT_ID=$clientid
export SSO_CLIENT_SECRET=$clientsec
export SSO_REDIRECT_URI=$redirecturi
export CONSOLE_API_SCHEME=$console_api_scheme
export CONSOLE_LOG_LEVEL="INFO"
export CONSOLE_APISERVER="http://deployd.lain:9003"

exec gunicorn -w 3 -b 0.0.0.0:8000 --max-requests=100 --preload --error-logfile logs/error.log --access-logfile logs/access.log console.wsgi 
