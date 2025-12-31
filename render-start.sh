#!/bin/bash

# Start the worker in the background
echo "Starting background worker..."
python -m worker.worker &
WORKER_PID=$!
echo "Worker started with PID: $WORKER_PID"

# Function to restart worker if it dies
monitor_worker() {
    while true; do
        if ! kill -0 $WORKER_PID 2>/dev/null; then
            echo "Worker died, restarting..."
            python -m worker.worker &
            WORKER_PID=$!
            echo "Worker restarted with PID: $WORKER_PID"
        fi
        sleep 30
    done
}

# Start worker monitor in background
monitor_worker &

# Start the API in the foreground
echo "Starting FastAPI API..."
cd apps/api && uvicorn app.main:app --host 0.0.0.0 --port $PORT
