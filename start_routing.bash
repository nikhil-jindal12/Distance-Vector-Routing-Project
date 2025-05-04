#!/bin/bash

# Distance Vector Routing Initialization Script

# Function to cleanup on exit
cleanup() {
    echo "Cleaning up processes..."
    kill $(jobs -p) 2>/dev/null
    wait
    echo "All processes terminated."
}

# Set trap to cleanup on script exit
trap cleanup EXIT

# Check if configuration file exists
if [ ! -f "config.txt" ]; then
    echo "Error: config.txt not found!"
    exit 1
fi

# Check if all required files exist
for file in server.py client.py; do
    if [ ! -f "$file" ]; then
        echo "Error: $file not found!"
        exit 1
    fi
done

# Make scripts executable
chmod +x server.py client.py

# Start the server
echo "Starting server on port 5555..."
python3 server.py 5555 config.txt &
SERVER_PID=$!
echo "Server started with PID: $SERVER_PID"

# Wait for server to start
sleep 2

# Start all routers simultaneously
declare -a routers=("u" "x" "w" "v" "y" "z")

echo "Starting routers simultaneously..."
for router in "${routers[@]}"; do
    echo "Starting router $router..."
    python3 client.py "$router" localhost 5555 &
    echo "Router $router started with PID: $!"
done

echo "All routers started simultaneously. Press Ctrl+C to stop all processes."

# Keep script running
while true; do
    sleep 1
done