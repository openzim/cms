#!/bin/bash

# Call it once to create a zimfarm `test-worker`:
# - retrieve an admin token
# - create the `test-worker`` user
# - create the associated worker object
# - upload a test public key.
#
# To be used to have a "real" test worker for local development, typically to start
# a worker manager or a task manager or simply assign tasks to a worker in the UI/API

set -e

die() {
    echo "ERROR: $1" >&2
    exit 1
}

check_non_empty() {
    local arg="$1"
    local message="$2"
    if [ -z "$arg" ]; then
	die "${message}"
    fi
}

check_http_code() {
    local http_code="$1"
    local response="$2"

    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
	:
    else
	error_msg=$(echo "$response" | jq -r '.errors // .message // .detail // "Unknown error"' 2>/dev/null || echo "HTTP $http_code")
	die "Could not checkin worker: ${error_msg}"
    fi
}

echo "Retrieving admin access token"

ZF_ADMIN_TOKEN="$(curl -s -X 'POST' \
    'http://localhost:37608/v2/auth/authorize' \
    -H 'accept: application/json' \
    -H 'Content-Type: application/json' \
    -d '{"username": "admin", "password": "admin_pass"}' \
    | jq -r '.access_token')"

if [ -z "$ZF_ADMIN_TOKEN" ] || [ "$ZF_ADMIN_TOKEN" = "null" ]; then
    die "Failed to retrieve admin access token"
fi


echo "Generating SSH key pair (Ed25519)"
ssh-keygen -t ed25519 -f id_ed25519 -N ""
payload="$(jq -n --arg name "test-worker" --arg key "$(< id_ed25519.pub)" \
    '{name: $name, ssh_key: {key: $key}}')"

echo "Create test-worker account with SSH keys"
response=$(curl -s -w "\n%{http_code}" -X POST http://localhost:37608/v2/workers \
  -H 'accept: */*' \
  -H "Authorization: Bearer $ZF_ADMIN_TOKEN" \
  -H 'Content-Type: application/json; charset=utf-8' \
  -d "$payload")

http_code=$(echo "$response" | tail -n1)
response=$(echo "$response" | head -n -1)

check_http_code "$http_code" "$response"

echo "DONE"
