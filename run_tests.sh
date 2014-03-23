#!/bin/bash


trap 'kill -KILL $(jobs -p)' EXIT SIGINT

assertIn ()
# Assert $1 is included in $2
{
    [[ "$2" =~ "$1" ]] || return 1
}

port_number="8080"

# Start the server
./run.py 2>/dev/null &

# Wait for the server to fully start
sleep 1 
# Save PID
server_pid="$!"

# Test single connection using cURL
curl_output=$(curl -s -o /dev/null -w "%{http_code}" "127.0.0.1:$port_number")
assertIn "200" "$curl_output"
[ "$?" -ne 0 ] && exit 1

# Test persistent connection
for i in {1..10}
do
    ( curl -s -o /dev/null 127.0.0.1:$port_number & )
done

# Check number of threads
num_threads=$(grep -i 'thread' "/proc/$server_pid/status" | awk '{ print $2 }')
[ "$num_threads" -gt 1 ] || exit 1

