#!/bin/bash
# Docker entrypoint script for PhantomLink
# Handles dataset download if not present

set -e

DATA_FILE="/app/data/raw/mc_maze.nwb"
DATASET_URL="${DATASET_URL:-}"

echo "PhantomLink Docker Container Starting..."

# Check if dataset exists
if [ ! -f "$DATA_FILE" ]; then
    echo "Dataset not found at $DATA_FILE"
    
    if [ -n "$DATASET_URL" ]; then
        echo "Downloading dataset from $DATASET_URL..."
        mkdir -p /app/data/raw
        
        # Download with retry logic
        for i in {1..3}; do
            if curl -L -o "$DATA_FILE" "$DATASET_URL"; then
                echo "Dataset downloaded successfully"
                break
            else
                echo "Download attempt $i failed, retrying..."
                sleep 5
            fi
        done
        
        if [ ! -f "$DATA_FILE" ]; then
            echo "ERROR: Failed to download dataset after 3 attempts"
            echo "Please provide the dataset via volume mount or set DATASET_URL"
            exit 1
        fi
    else
        echo "WARNING: No dataset found and DATASET_URL not set"
        echo ""
        echo "Options to provide the dataset:"
        echo "  1. Mount volume: -v /path/to/data:/app/data"
        echo "  2. Set DATASET_URL: -e DATASET_URL=https://your-host/mc_maze.nwb"
        echo "  3. Use DANDI: dandi download DANDI:000140"
        echo ""
        echo "Exiting..."
        exit 1
    fi
else
    echo "Dataset found at $DATA_FILE"
    FILE_SIZE=$(du -h "$DATA_FILE" | cut -f1)
    echo "Dataset size: $FILE_SIZE"
fi

# Start the application
echo "Starting PhantomLink server..."
exec python main.py
