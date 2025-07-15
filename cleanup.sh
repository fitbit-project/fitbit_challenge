#!/bin/bash

# This script will stop containers, remove named volumes,
# and then delete the local state directory.

echo "Running docker-compose down..."
docker-compose down -v

echo "Deleting local state directory..."
rm -rf ./ingestion/state

echo "Cleanup complete."