#!/bin/bash

# RunMyPool Frontend Docker Build and Push Script for ECS
# Usage: ./build-and-push-frontend.sh [environment]
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
FRONTEND_REPO=runmypool-frontend

# Tags
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
FRONTEND_TAG="${ENVIRONMENT}-${TIMESTAMP}"

echo "=========================================="
echo "Building and pushing FRONTEND Docker image"
echo "=========================================="
echo "Environment: $ENVIRONMENT"
echo "AWS Account ID: $AWS_ACCOUNT_ID"
echo "AWS Region: $AWS_REGION"
echo "Timestamp: $TIMESTAMP"
echo "Frontend Tag: $FRONTEND_TAG"
echo ""

# Login to ECR
echo "Logging in to Amazon ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

# Create ECR repository if it doesn't exist
echo "Ensuring ECR repository exists..."
aws ecr describe-repositories --repository-names $FRONTEND_REPO --region $AWS_REGION 2>/dev/null || \
    aws ecr create-repository --repository-name $FRONTEND_REPO --region $AWS_REGION

# Check if frontend directory exists
if [ ! -d "./frontend" ]; then
    echo "Error: frontend directory not found"
    echo "Please run this script from the root directory containing the frontend folder"
    exit 1
fi

# Build frontend Docker image
echo "Building frontend Docker image..."
echo "Docker build context: ./frontend"

# Check if Dockerfile exists
if [ ! -f "./frontend/Dockerfile" ]; then
    echo "Error: Dockerfile not found in frontend directory"
    echo "Please ensure ./frontend/Dockerfile exists"
    exit 1
fi

docker build -t $FRONTEND_REPO:latest ./frontend

# Tag the image
echo "Tagging frontend image..."
docker tag $FRONTEND_REPO:latest $ECR_REGISTRY/$FRONTEND_REPO:$FRONTEND_TAG
docker tag $FRONTEND_REPO:latest $ECR_REGISTRY/$FRONTEND_REPO:latest

# Push to ECR
echo "Pushing frontend image to ECR..."
docker push $ECR_REGISTRY/$FRONTEND_REPO:$FRONTEND_TAG
docker push $ECR_REGISTRY/$FRONTEND_REPO:latest

echo ""
echo "=========================================="
echo "Frontend build and push completed successfully!"
echo "=========================================="
echo "Frontend image URI: $ECR_REGISTRY/$FRONTEND_REPO:$FRONTEND_TAG"
echo "Frontend latest URI: $ECR_REGISTRY/$FRONTEND_REPO:latest"
echo ""

# Update frontend task definition
if [ -f "ecs-frontend-task-definition.json" ]; then
    echo "Updating frontend ECS task definition..."
    sed "s/YOUR_ACCOUNT_ID/$AWS_ACCOUNT_ID/g; s/YOUR_REGION/$AWS_REGION/g" ecs-frontend-task-definition.json > ecs-frontend-task-definition-${ENVIRONMENT}.json
    echo "Task definition file created: ecs-frontend-task-definition-${ENVIRONMENT}.json"
    echo ""
    echo "To deploy frontend to ECS, run:"
    echo "aws ecs register-task-definition --cli-input-json file://ecs-frontend-task-definition-${ENVIRONMENT}.json"
    echo ""
else
    echo "Note: ecs-frontend-task-definition.json not found - skipping task definition update"
fi

# Clean up local images (optional)
read -p "Do you want to clean up local Docker images? (y/N): " cleanup
if [[ $cleanup =~ ^[Yy]$ ]]; then
    echo "Cleaning up local frontend images..."
    docker rmi $FRONTEND_REPO:latest 2>/dev/null || true
    docker rmi $ECR_REGISTRY/$FRONTEND_REPO:$FRONTEND_TAG 2>/dev/null || true
    docker rmi $ECR_REGISTRY/$FRONTEND_REPO:latest 2>/dev/null || true
    echo "Local images cleaned up"
fi

echo "Frontend deployment script completed!"
