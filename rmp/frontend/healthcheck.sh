#!/bin/sh

# ECS Health Check Script for Next.js
# Waits for Next.js to be ready before checking health

MAX_WAIT=30
WAIT_TIME=0

echo "Starting health check..."

# Wait for Next.js to be ready
while [ $WAIT_TIME -lt $MAX_WAIT ]; do
    if wget --no-verbose --tries=1 --spider http://localhost:3000/ 2>/dev/null; then
        echo "✅ Next.js is ready and responding"
        exit 0
    fi
    echo "⏳ Waiting for Next.js... (${WAIT_TIME}s/${MAX_WAIT}s)"
    sleep 2
    WAIT_TIME=$((WAIT_TIME + 2))
done

echo "❌ Next.js failed to respond within ${MAX_WAIT} seconds"
exit 1
