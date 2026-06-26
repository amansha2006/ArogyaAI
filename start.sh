#!/bin/bash

echo "Clearing GPU memory..."
pkill -9 -f python || true

# Start the application
echo "Starting ArogyaAI Server..."
uvicorn api:app --host 0.0.0.0 --port 8000
