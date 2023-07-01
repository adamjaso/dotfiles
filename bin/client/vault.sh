#!/bin/bash

usage() {
    [ -z "$1" ] || echo "$1"
    cat <<EOF
usage: $(basename $0) FLAGS list|get|set SUBPATH

This is a minimal requirement Vault client. Its only dependencies are curl and jq.

ACTIONS
    list - displays the paths in the current vault secret
    get  - retrieves the contents of a path
    set  - sends STDIN as an HTTP PUT request body to update a vault path
    del  - deletes the path in the current vault secret

FLAGS
   -v|--verbose                  (optional) Verbose output
   -k|--insecure-skip-tls-verify (optional) Don't verify TLS certificates
   -q|--quiet                    (optional) Suppress all output
   --token-only                  (optional) Only print the Vault auth token
   --show-env                    (optional) Only print the current environment variables
   -h|--help                     (optional) Show this help message

ENVIRONMENT
    VAULT_URL (required)
    VAULT_PATH (required)
    VAULT_ROLE_ID and VAULT_SECRET_ID or
    VAULT_USERNAME and VAULT_PASSWORD (required)

EOF
    exit 1
}

VERBOSE=
QUIET=
CURL='curl -sS -A vault.sh'
TOKEN_ONLY=
SHOW_ENV=
ACTION=LIST
while [ $# -gt 0 ] ; do
    case "$1" in
        -v|--verbose)
            VERBOSE=y
            CURL="$CURL -v"
            ;;
        -k|--insecure-skip-tls-verify)
            CURL="$CURL -k"
            ;;
        -q|--quiet)
            QUIET=y
            ;;
        --token-only)
            TOKEN_ONLY=y
            break
            ;;
        --show-env)
            SHOW_ENV=y
            break
            ;;
        -h|--help)
            usage
            ;;
        list)
            ACTION=LIST
            SUBPATH=$2
            break
            ;;
        get)
            ACTION=GET
            SUBPATH=$2
            break
            ;;
        set)
            ACTION=PUT
            SUBPATH=$2
            break
            ;;
        del)
            ACTION=DELETE
            SUBPATH=$2
            break
            ;;
        *)
            usage "unknown argument '$1'"
            ;;
    esac
    shift
done

# verify requirements
[ -z "$SUBPATH" ] || SUBPATH="/$SUBPATH"
[ -n "$VAULT_URL" ] || usage 'VAULT_URL is required'
[ -n "$VAULT_PATH" ] || usage 'VAULT_PATH is required'
[[ "$VAULT_URL" != *"/" ]] || VAULT_URL=${VAULT_URL%/}
[[ "$VAULT_PATH" != "/"* ]] || VAULT_PATH=${VAULT_PATH#/}

# build authentication
if [ -z "$VAULT_TOKEN" ] ; then
    if [ -n "$VAULT_USERNAME" ] && [ -n "$VAULT_PASSWORD" ] ; then
        AUTH_PATH="v1/auth/ldap/login/$VAULT_USERNAME"
        AUTH_JSON=$(jq -crn --arg pw "$VAULT_PASSWORD" '{password:$pw}')
    elif [ -n "$VAULT_ROLE_ID" ] && [ -n "$VAULT_SECRET_ID" ] ; then
        AUTH_PATH=v1/auth/approle/login
        AUTH_JSON=$(jq -crn --arg rid "$VAULT_ROLE_ID" --arg sid "$VAULT_SECRET_ID" -r '{role_id:$rid,secret_id:$sid}')
    else
        usage 'Either VAULT_USERNAME and VAULT_PASSWORD or VAULT_ROLE_ID and VAULT_SECRET_ID is required.'
    fi

    [ -z "$SHOW_ENV" ] || {
        echo -e "VAULT_URL:\t$VAULT_URL\nVAULT_PATH:\t$VAULT_PATH"
        [ -z "$VAULT_ROLE_ID" ] || [ -z "$VAULT_SECRET_ID" ] || \
            echo -e "VAULT_ROLE_ID\nVAULT_SECRET_ID"
        [ -z "$VAULT_USERNAME" ] || [ -z "$VAULT_PASSWORD" ] || \
            echo -e "VAULT_USERNAME\nVAULT_PASSWORD"
        exit 0
    }

    # set debug logging
    set -e
    [ -z "$VERBOSE" ] || set -x

    # get vault auth token
    VAULT_TOKEN=$($CURL -XPOST -H"content-type:application/json" -d "$AUTH_JSON" \
        "$VAULT_URL/$AUTH_PATH" | jq -r .auth.client_token)
else
    [ -z "$SHOW_ENV" ] || {
        echo -e "VAULT_TOKEN"
        exit 0
    }
    # set debug logging
    set -e
    [ -z "$VERBOSE" ] || set -x
fi
[ -z "$TOKEN_ONLY" ] || { echo "$VAULT_TOKEN" ; exit 0 ; }
# request vault
[ -n "$QUIET" ] || echo "$ACTION $VAULT_URL/$VAULT_PATH$SUBPATH" >&2
[ "$ACTION" != "PUT" ] || CURL="$CURL -Hcontent-type:application/json -d @-"
$CURL -X$ACTION -H"X-Vault-Token: $VAULT_TOKEN" $VAULT_URL/$VAULT_PATH$SUBPATH | jq .
