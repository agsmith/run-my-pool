#!/bin/bash

# RunMyPool Frontend ECS Service Refresh Script
# Usage: ./refresh-frontend-service.sh [environment] [cluster-name]
# Environment: dev, staging, prod (default: dev)

set -e

# Configuration
ENVIRONMENT=${1:-dev}
CLUSTER_NAME=${2:-runmypool-cluster-${ENVIRONMENT}}
AWS_REGION=${AWS_REGION:-us-east-1}
SERVICE_NAME=runmypool-frontend-service-${ENVIRONMENT}

echo "=========================================="
echo "Refreshing Frontend ECS Service"
echo "=========================================="
echo "Environment: $ENVIRONMENT"
echo "Cluster: $CLUSTER_NAME"
echo "Service: $SERVICE_NAME"
echo "AWS Region: $AWS_REGION"
echo ""

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &>/dev/null; then
    echo "Error: AWS CLI is not configured or credentials are invalid"
    echo "Please run: aws configure"
    exit 1
fi

# Check if cluster exists
echo "Checking if cluster exists..."
if ! aws ecs describe-clusters --clusters $CLUSTER_NAME --region $AWS_REGION --query 'clusters[0].status' --output text 2>/dev/null | grep -q "ACTIVE"; then
    echo "Error: Cluster '$CLUSTER_NAME' not found or not active"
    echo "Available clusters:"
    aws ecs list-clusters --region $AWS_REGION --query 'clusterArns[]' --output table
    exit 1
fi

# Check if service exists
echo "Checking if service exists..."
if ! aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $AWS_REGION --query 'services[0].status' --output text 2>/dev/null | grep -q "ACTIVE"; then
    echo "Error: Service '$SERVICE_NAME' not found or not active in cluster '$CLUSTER_NAME'"
    echo "Available services in cluster:"
    aws ecs list-services --cluster $CLUSTER_NAME --region $AWS_REGION --query 'serviceArns[]' --output table
    exit 1
fi

# Get current service status
echo "Getting current service status..."
CURRENT_STATUS=$(aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $AWS_REGION --query 'services[0].[status,runningCount,pendingCount,desiredCount]' --output table)
echo "$CURRENT_STATUS"

# Option 1: Force new deployment (recommended)
echo ""
echo "Option 1: Force New Deployment (Recommended)"
echo "This will:"
echo "- Use the existing task definition"
echo "- Force all tasks to restart with latest container images"
echo "- Maintain the same configuration"
echo ""

read -p "Force new deployment? (Y/n): " force_deploy
if [[ $force_deploy =~ ^[Nn]$ ]]; then
    echo "Skipping force deployment..."
else
    echo "Forcing new deployment..."
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service $SERVICE_NAME \
        --force-new-deployment \
        --region $AWS_REGION \
        --output table
    
    echo "Force deployment initiated successfully!"
fi

# Option 2: Update with latest task definition
echo ""
echo "Option 2: Update Task Definition"
echo "This will:"
echo "- Register the latest task definition"
echo "- Update the service to use the new task definition"
echo ""

# Check if task definition file exists
TASK_DEF_FILE="ecs-frontend-task-definition-${ENVIRONMENT}.json"
if [ -f "$TASK_DEF_FILE" ]; then
    read -p "Update service with latest task definition from $TASK_DEF_FILE? (y/N): " update_task_def
    if [[ $update_task_def =~ ^[Yy]$ ]]; then
        echo "Registering new task definition..."
        NEW_TASK_DEF_ARN=$(aws ecs register-task-definition --cli-input-json file://$TASK_DEF_FILE --region $AWS_REGION --query 'taskDefinition.taskDefinitionArn' --output text)
        echo "New task definition registered: $NEW_TASK_DEF_ARN"
        
        echo "Updating service with new task definition..."
        aws ecs update-service \
            --cluster $CLUSTER_NAME \
            --service $SERVICE_NAME \
            --task-definition $NEW_TASK_DEF_ARN \
            --region $AWS_REGION \
            --output table
        
        echo "Service updated with new task definition!"
    fi
else
    echo "Task definition file $TASK_DEF_FILE not found - skipping task definition update"
fi

# Monitor deployment
echo ""
echo "=========================================="
echo "Monitoring Deployment Progress"
echo "=========================================="
echo "Waiting for deployment to complete..."
echo "(This may take several minutes)"

# Wait for deployment to stabilize
aws ecs wait services-stable --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $AWS_REGION

echo ""
echo "Deployment completed! Getting final service status..."
FINAL_STATUS=$(aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $AWS_REGION --query 'services[0].[status,runningCount,pendingCount,desiredCount]' --output table)
echo "$FINAL_STATUS"

# Get service events (last 5)
echo ""
echo "Recent service events:"
aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $AWS_REGION --query 'services[0].events[:5].[createdAt,message]' --output table

# Get task health status
echo ""
echo "Current task health:"
TASK_ARNS=$(aws ecs list-tasks --cluster $CLUSTER_NAME --service-name $SERVICE_NAME --region $AWS_REGION --query 'taskArns[]' --output text)

if [ -n "$TASK_ARNS" ]; then
    aws ecs describe-tasks --cluster $CLUSTER_NAME --tasks $TASK_ARNS --region $AWS_REGION --query 'tasks[].[taskArn,lastStatus,healthStatus,createdAt]' --output table
else
    echo "No tasks currently running"
fi

# Get ALB target health (if applicable)
echo ""
echo "To check ALB target health, run:"
echo "aws elbv2 describe-target-health --target-group-arn <your-target-group-arn>"

echo ""
echo "=========================================="
echo "Frontend Service Refresh Completed!"
echo "=========================================="
echo "Cluster: $CLUSTER_NAME"
echo "Service: $SERVICE_NAME"
echo "Region: $AWS_REGION"
echo ""
echo "Useful commands for monitoring:"
echo "# Watch service status"
echo "aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $AWS_REGION"
echo ""
echo "# Check service logs"
echo "aws logs tail /ecs/runmypool-frontend --follow"
