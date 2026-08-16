#!/bin/bash

# Quick Frontend Service Refresh - Forces new deployment
# Usage: ./quick-refresh-frontend.sh [environment]

set -e

ENVIRONMENT=${1:-dev}
CLUSTER_NAME=runmypool-cluster-${ENVIRONMENT}
SERVICE_NAME=runmypool-frontend-service-${ENVIRONMENT}
AWS_REGION=${AWS_REGION:-us-east-1}

echo "🔄 Quick refresh of frontend service..."
echo "Environment: $ENVIRONMENT"
echo "Service: $SERVICE_NAME"

# Force new deployment
aws ecs update-service \
    --cluster $CLUSTER_NAME \
    --service $SERVICE_NAME \
    --force-new-deployment \
    --region $AWS_REGION \
    --no-cli-pager

echo "✅ Frontend service refresh initiated!"
echo "Monitor progress with:"
echo "aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $AWS_REGION"
