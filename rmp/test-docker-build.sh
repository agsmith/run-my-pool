#!/bin/bash

# Test Docker builds locally
# Usage: ./test-docker-build.sh

set -e

echo "Testing Docker builds locally..."

# Build backend
echo "Building backend Docker image..."
cd backend
docker build -t runmypool-backend-test .
echo "✅ Backend build successful"

# Build frontend
echo "Building frontend Docker image..."
cd ../frontend
docker build -t runmypool-frontend-test .
echo "✅ Frontend build successful"

# Test with docker-compose
echo "Testing with docker-compose..."
cd ..
docker-compose -f docker-compose.yml build
echo "✅ Docker Compose build successful"

echo "🎉 All Docker builds completed successfully!"
echo ""
echo "To test the full stack locally:"
echo "  docker-compose up"
echo ""
echo "To clean up test images:"
echo "  docker rmi runmypool-backend-test runmypool-frontend-test"
