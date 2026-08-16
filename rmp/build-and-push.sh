#!/bin/bash

# RunMyPool Docker Build and Push Script for ECS
# Usage: ./build-and-push.sh [environment]
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

# Repository names
BACKEND_REPO=runmypool-backend
FRONTEND_REPO=runmypool-frontend

# Tags
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKEND_TAG="${ENVIRONMENT}-${TIMESTAMP}"
FRONTEND_TAG="${ENVIRONMENT}-${TIMESTAMP}"

echo "Building and pushing Docker images for environment: $ENVIRONMENT"
echo "AWS Account ID: $AWS_ACCOUNT_ID"
echo "AWS Region: $AWS_REGION"
echo "Timestamp: $TIMESTAMP"

# Login to ECR
echo "Logging in to Amazon ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

# Create ECR repositories if they don't exist
echo "Ensuring ECR repositories exist..."
aws ecr describe-repositories --repository-names $BACKEND_REPO --region $AWS_REGION 2>/dev/null || \
    aws ecr create-repository --repository-name $BACKEND_REPO --region $AWS_REGION

aws ecr describe-repositories --repository-names $FRONTEND_REPO --region $AWS_REGION 2>/dev/null || \
    aws ecr create-repository --repository-name $FRONTEND_REPO --region $AWS_REGION

# Build and push backend
echo "Building backend Docker image..."
docker build -t $BACKEND_REPO:latest ./backend
docker tag $BACKEND_REPO:latest $ECR_REGISTRY/$BACKEND_REPO:$BACKEND_TAG
docker tag $BACKEND_REPO:latest $ECR_REGISTRY/$BACKEND_REPO:latest

echo "Pushing backend image to ECR..."
docker push $ECR_REGISTRY/$BACKEND_REPO:$BACKEND_TAG
docker push $ECR_REGISTRY/$BACKEND_REPO:latest

# Build and push frontend
echo "Building frontend Docker image..."
docker build -t $FRONTEND_REPO:latest ./frontend
docker tag $FRONTEND_REPO:latest $ECR_REGISTRY/$FRONTEND_REPO:$FRONTEND_TAG
docker tag $FRONTEND_REPO:latest $ECR_REGISTRY/$FRONTEND_REPO:latest

echo "Pushing frontend image to ECR..."
docker push $ECR_REGISTRY/$FRONTEND_REPO:$FRONTEND_TAG
docker push $ECR_REGISTRY/$FRONTEND_REPO:latest

echo "Build and push completed successfully!"
echo "Backend image: $ECR_REGISTRY/$BACKEND_REPO:$BACKEND_TAG"
echo "Frontend image: $ECR_REGISTRY/$FRONTEND_REPO:$FRONTEND_TAG"

# Update task definitions with new image URIs
echo "Updating ECS task definitions..."

# Update backend task definition
sed "s/YOUR_ACCOUNT_ID/$AWS_ACCOUNT_ID/g; s/YOUR_REGION/$AWS_REGION/g" ecs-backend-task-definition.json > ecs-backend-task-definition-${ENVIRONMENT}.json

# Update frontend task definition
sed "s/YOUR_ACCOUNT_ID/$AWS_ACCOUNT_ID/g; s/YOUR_REGION/$AWS_REGION/g" ecs-frontend-task-definition.json > ecs-frontend-task-definition-${ENVIRONMENT}.json

echo "Task definition files created:"
echo "- ecs-backend-task-definition-${ENVIRONMENT}.json"
echo "- ecs-frontend-task-definition-${ENVIRONMENT}.json"

echo "To deploy to ECS, run:"
echo "aws ecs register-task-definition --cli-input-json file://ecs-backend-task-definition-${ENVIRONMENT}.json"
echo "aws ecs register-task-definition --cli-input-json file://ecs-frontend-task-definition-${ENVIRONMENT}.json"
