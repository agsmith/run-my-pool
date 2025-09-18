#!/bin/bash

# RunMyPool Backend Docker Build and Push Script for ECS
# Usage: ./build-and-push-backend.sh [environment]
# Environment: dev, staging, prod (default: dev)

set -e

# Configuration
ENVIRONMENT=${1:-dev}
AWS_REGION=${AWS_REGION:-us-east-1}
AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID}
ECR_REGISTRY=${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Check if AWS_ACCOUNT_ID is set
if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo "Error: AWS_ACCOUNT_ID environment variable is not set"
    echo "Please set it with: export AWS_ACCOUNT_ID=your-account-id"
    exit 1
fi

# Repository name
BACKEND_REPO=runmypool-backend

# Tags
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKEND_TAG="${ENVIRONMENT}-${TIMESTAMP}"

echo "=========================================="
echo "Building and pushing BACKEND Docker image"
echo "=========================================="
echo "Environment: $ENVIRONMENT"
echo "AWS Account ID: $AWS_ACCOUNT_ID"
echo "AWS Region: $AWS_REGION"
echo "Timestamp: $TIMESTAMP"
echo "Backend Tag: $BACKEND_TAG"
echo ""

# Login to ECR
echo "Logging in to Amazon ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

# Create ECR repository if it doesn't exist
echo "Ensuring ECR repository exists..."
aws ecr describe-repositories --repository-names $BACKEND_REPO --region $AWS_REGION 2>/dev/null || \
    aws ecr create-repository --repository-name $BACKEND_REPO --region $AWS_REGION

# Check if backend directory exists
if [ ! -d "./backend" ]; then
    echo "Error: backend directory not found"
    echo "Please run this script from the root directory containing the backend folder"
    exit 1
fi

# Build backend Docker image
echo "Building backend Docker image..."
echo "Docker build context: ./backend"

# Check if Dockerfile exists
if [ ! -f "./backend/Dockerfile" ]; then
    echo "Error: Dockerfile not found in backend directory"
    echo "Please ensure ./backend/Dockerfile exists"
    exit 1
fi

docker build -t $BACKEND_REPO:latest ./backend

# Tag the image
echo "Tagging backend image..."
docker tag $BACKEND_REPO:latest $ECR_REGISTRY/$BACKEND_REPO:$BACKEND_TAG
docker tag $BACKEND_REPO:latest $ECR_REGISTRY/$BACKEND_REPO:latest

# Push to ECR
echo "Pushing backend image to ECR..."
docker push $ECR_REGISTRY/$BACKEND_REPO:$BACKEND_TAG
docker push $ECR_REGISTRY/$BACKEND_REPO:latest

echo ""
echo "=========================================="
echo "Backend build and push completed successfully!"
echo "=========================================="
echo "Backend image URI: $ECR_REGISTRY/$BACKEND_REPO:$BACKEND_TAG"
echo "Backend latest URI: $ECR_REGISTRY/$BACKEND_REPO:latest"
echo ""

# Update backend task definition
if [ -f "ecs-backend-task-definition.json" ]; then
    echo "Updating backend ECS task definition..."
    sed "s/YOUR_ACCOUNT_ID/$AWS_ACCOUNT_ID/g; s/YOUR_REGION/$AWS_REGION/g" ecs-backend-task-definition.json > ecs-backend-task-definition-${ENVIRONMENT}.json
    echo "Task definition file created: ecs-backend-task-definition-${ENVIRONMENT}.json"
    echo ""
    echo "To deploy backend to ECS, run:"
    echo "aws ecs register-task-definition --cli-input-json file://ecs-backend-task-definition-${ENVIRONMENT}.json"
    echo ""
else
    echo "Note: ecs-backend-task-definition.json not found - skipping task definition update"
fi

# Clean up local images (optional)
read -p "Do you want to clean up local Docker images? (y/N): " cleanup
if [[ $cleanup =~ ^[Yy]$ ]]; then
    echo "Cleaning up local backend images..."
    docker rmi $BACKEND_REPO:latest 2>/dev/null || true
    docker rmi $ECR_REGISTRY/$BACKEND_REPO:$BACKEND_TAG 2>/dev/null || true
    docker rmi $ECR_REGISTRY/$BACKEND_REPO:latest 2>/dev/null || true
    echo "Local images cleaned up"
fi

echo "Backend deployment script completed!"
