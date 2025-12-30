#!/bin/bash

# Start the worker in the background
echo "Starting background worker..."
cd worker && python worker.py &

# Start the API in the foreground
echo "Starting FastAPI API..."
cd ../apps/api && uvicorn app.main:app --host 0.0.0.0 --port $PORT
