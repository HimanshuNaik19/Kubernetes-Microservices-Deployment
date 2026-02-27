#!/bin/bash
set -e

echo "Building Docker images..."

# Build frontend
echo "Building frontend..."
cd app/frontend
docker build -t task-frontend:latest .
cd ../..

# Build backend
echo "Building backend..."
cd app/backend
docker build -t task-backend:latest .
cd ../..

echo "Build completed successfully!"
echo "Images created:"
echo "  - task-frontend:latest"
echo "  - task-backend:latest"
