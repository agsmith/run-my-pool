# Docker Build and Push Scripts

This directory contains three build and push scripts for deploying the Run My Pool application to AWS ECS:

## Scripts Overview

### 1. `build-and-push.sh` (Original - Full Stack)
Builds and pushes **both** frontend and backend Docker images.

```bash
./build-and-push.sh [environment]
```

### 2. `build-and-push-frontend.sh` (New - Frontend Only)
Builds and pushes **only** the frontend Docker image.

```bash
./build-and-push-frontend.sh [environment]
```

### 3. `build-and-push-backend.sh` (New - Backend Only)
Builds and pushes **only** the backend Docker image.

```bash
./build-and-push-backend.sh [environment]
```

## Prerequisites

1. **AWS CLI** configured with appropriate permissions
2. **Docker** installed and running
3. **AWS_ACCOUNT_ID** environment variable set:
   ```bash
   export AWS_ACCOUNT_ID=your-12-digit-account-id
   ```

## Usage Examples

### Deploy Everything (Full Stack)
```bash
# Development environment
./build-and-push.sh dev

# Production environment
./build-and-push.sh prod
```

### Deploy Only Frontend (After Frontend Changes)
```bash
# Development environment - frontend only
./build-and-push-frontend.sh dev

# Production environment - frontend only
./build-and-push-frontend.sh prod
```

### Deploy Only Backend (After Backend Changes)
```bash
# Development environment - backend only
./build-and-push-backend.sh dev

# Production environment - backend only
./build-and-push-backend.sh prod
```

## Environment Options

- `dev` (default) - Development environment
- `staging` - Staging environment  
- `prod` - Production environment

## What Each Script Does

1. **ECR Login**: Authenticates with AWS Elastic Container Registry
2. **Repository Creation**: Creates ECR repositories if they don't exist
3. **Docker Build**: Builds the Docker image(s) from Dockerfile(s)
4. **Image Tagging**: Tags images with environment and timestamp
5. **ECR Push**: Pushes images to ECR with both specific tag and 'latest'
6. **Task Definition Update**: Updates ECS task definition files
7. **Cleanup Option**: Optionally removes local Docker images

## Output Files

Each script generates environment-specific task definition files:
- `ecs-frontend-task-definition-{environment}.json`
- `ecs-backend-task-definition-{environment}.json`

## Docker Images Created

### Frontend Images
- Repository: `runmypool-frontend`
- Tags: `{environment}-{timestamp}` and `latest`

### Backend Images  
- Repository: `runmypool-backend`
- Tags: `{environment}-{timestamp}` and `latest`

## Deployment to ECS

After running the build scripts, deploy to ECS using:

```bash
# Deploy frontend
aws ecs register-task-definition --cli-input-json file://ecs-frontend-task-definition-{environment}.json

# Deploy backend
aws ecs register-task-definition --cli-input-json file://ecs-backend-task-definition-{environment}.json
```

## Use Cases for Individual Scripts

### When to Use Frontend-Only Script
- UI/UX changes and mobile optimizations
- Frontend configuration updates
- React component modifications
- Styling and layout changes
- Frontend dependency updates

### When to Use Backend-Only Script
- API endpoint changes
- Database model updates
- Authentication/authorization changes
- Backend configuration updates
- Python dependency updates

### When to Use Full Stack Script
- Initial deployment
- Major releases affecting both frontend and backend
- Database migrations that require both components
- Configuration changes affecting the entire stack

## Performance Benefits

Using individual scripts provides:
- **Faster Deployments**: Only rebuild/deploy what changed
- **Reduced Risk**: Isolate changes to specific components
- **Better Resource Usage**: Smaller, focused deployments
- **Easier Debugging**: Simpler to isolate issues

## Troubleshooting

### Common Issues

1. **AWS_ACCOUNT_ID not set**
   ```bash
   export AWS_ACCOUNT_ID=123456789012
   ```

2. **Docker not running**
   ```bash
   docker ps  # Check if Docker is running
   ```

3. **AWS CLI not configured**
   ```bash
   aws configure  # Set up AWS credentials
   ```

4. **Permission denied**
   ```bash
   chmod +x *.sh  # Make scripts executable
   ```

### Script Validation

All scripts include validation for:
- Required environment variables
- Directory structure
- Dockerfile existence
- ECR repository access
- Docker build success

## Security Notes

- Scripts use AWS ECR for secure image storage
- Images are tagged with timestamps for traceability
- Local images can be cleaned up after push
- AWS credentials should follow least-privilege principle

## Next Steps After Running Scripts

1. **Verify Images**: Check ECR console for uploaded images
2. **Update Services**: Update ECS services to use new task definitions
3. **Monitor Deployment**: Watch ECS service deployment progress
4. **Test Application**: Verify functionality after deployment
5. **Clean Up**: Remove old/unused ECR images periodically
