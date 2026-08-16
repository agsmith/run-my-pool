# RunMyPool ECS Deployment Guide

This guide covers deploying the RunMyPool application to Amazon ECS using Docker containers.

## Prerequisites

1. AWS CLI configured with appropriate permissions
2. Docker installed locally
3. An AWS account with ECS, ECR, RDS, and ALB access
4. A MySQL RDS instance set up

## Architecture Overview

The application consists of:
- **Frontend**: Next.js React application (Port 3000)
- **Backend**: FastAPI Python application (Port 8000)
- **Database**: MySQL RDS instance

## Quick Start

### 1. Set Environment Variables

```bash
export AWS_ACCOUNT_ID=123456789012
export AWS_REGION=us-east-1
```

### 2. Build and Push Images

```bash
./build-and-push.sh prod
```

### 3. Create AWS Resources

#### Create CloudWatch Log Groups
```bash
aws logs create-log-group --log-group-name /ecs/runmypool-backend --region $AWS_REGION
aws logs create-log-group --log-group-name /ecs/runmypool-frontend --region $AWS_REGION
```

#### Create Secrets in AWS Secrets Manager
```bash
# Database URL
aws secretsmanager create-secret \
    --name "runmypool/database-url" \
    --description "Database connection string for RunMyPool" \
    --secret-string "mysql://username:password@your-rds-endpoint:3306/runmypool" \
    --region $AWS_REGION

# JWT Secret
aws secretsmanager create-secret \
    --name "runmypool/jwt-secret" \
    --description "JWT secret key for RunMyPool" \
    --secret-string "your-super-secure-jwt-secret-key" \
    --region $AWS_REGION
```

#### Create ECS Cluster
```bash
aws ecs create-cluster \
    --cluster-name runmypool-cluster \
    --capacity-providers FARGATE \
    --default-capacity-provider-strategy capacityProvider=FARGATE,weight=1 \
    --region $AWS_REGION
```

### 4. Register Task Definitions

```bash
# Backend
aws ecs register-task-definition \
    --cli-input-json file://ecs-backend-task-definition-prod.json \
    --region $AWS_REGION

# Frontend
aws ecs register-task-definition \
    --cli-input-json file://ecs-frontend-task-definition-prod.json \
    --region $AWS_REGION
```

### 5. Create Services

#### Backend Service
```bash
aws ecs create-service \
    --cluster runmypool-cluster \
    --service-name runmypool-backend \
    --task-definition runmypool-backend:1 \
    --desired-count 2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-12345,subnet-67890],securityGroups=[sg-backend],assignPublicIp=ENABLED}" \
    --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:region:account:targetgroup/backend-tg/12345,containerName=backend,containerPort=8000" \
    --region $AWS_REGION
```

#### Frontend Service
```bash
aws ecs create-service \
    --cluster runmypool-cluster \
    --service-name runmypool-frontend \
    --task-definition runmypool-frontend:1 \
    --desired-count 2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-12345,subnet-67890],securityGroups=[sg-frontend],assignPublicIp=ENABLED}" \
    --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:region:account:targetgroup/frontend-tg/12345,containerName=frontend,containerPort=3000" \
    --region $AWS_REGION
```

## Environment-Specific Configurations

### Development
- Single instance of each service
- Smaller resource allocations
- Development database

### Staging
- 1-2 instances of each service
- Staging database
- Same configuration as production for testing

### Production
- 2+ instances of each service
- Production database with backups
- Enhanced monitoring and logging

## Monitoring and Logging

### CloudWatch Logs
Logs are automatically sent to CloudWatch:
- Backend: `/ecs/runmypool-backend`
- Frontend: `/ecs/runmypool-frontend`

### Health Checks
Both services include health checks:
- Backend: `GET /` endpoint
- Frontend: `GET /` endpoint

### Scaling
Configure auto-scaling based on:
- CPU utilization (target: 70%)
- Memory utilization (target: 80%)
- Custom metrics (request count, response time)

## Security Considerations

1. **Network Security**
   - Use private subnets for ECS tasks
   - Configure security groups with minimal required access
   - Enable VPC Flow Logs

2. **Secrets Management**
   - Store sensitive data in AWS Secrets Manager
   - Use IAM roles for ECS tasks
   - Rotate secrets regularly

3. **Database Security**
   - Use RDS with encryption at rest
   - Enable automated backups
   - Configure VPC security groups

4. **Application Security**
   - Use HTTPS/TLS for all communications
   - Implement proper CORS policies
   - Regular security updates

## Troubleshooting

### Common Issues

1. **Service Won't Start**
   - Check CloudWatch logs
   - Verify task definition configuration
   - Ensure secrets are accessible

2. **Database Connection Issues**
   - Verify RDS security groups
   - Check database credentials in Secrets Manager
   - Ensure network connectivity

3. **Load Balancer Health Checks Failing**
   - Verify health check endpoints
   - Check security group rules
   - Review application logs

### Useful Commands

```bash
# Check service status
aws ecs describe-services --cluster runmypool-cluster --services runmypool-backend

# View logs
aws logs get-log-events --log-group-name /ecs/runmypool-backend --log-stream-name ecs/backend/task-id

# Update service
aws ecs update-service --cluster runmypool-cluster --service runmypool-backend --task-definition runmypool-backend:2
```

## Cost Optimization

1. **Right-sizing**
   - Monitor CPU/memory usage
   - Adjust task definitions accordingly
   - Use Fargate Spot for non-critical workloads

2. **Auto Scaling**
   - Scale down during low usage periods
   - Use predictive scaling for known patterns

3. **Resource Management**
   - Use Application Load Balancer efficiently
   - Optimize Docker images for smaller sizes
   - Regular cleanup of unused ECR images

## Backup and Disaster Recovery

1. **Database Backups**
   - Enable automated RDS backups
   - Configure backup retention period
   - Test restore procedures

2. **Application Backups**
   - Tag ECR images for easy rollback
   - Maintain multiple task definition revisions
   - Document rollback procedures

3. **Infrastructure as Code**
   - Use Terraform or CloudFormation for reproducible deployments
   - Version control all configuration files
   - Automate disaster recovery procedures
