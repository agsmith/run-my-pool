# GitHub Actions CI/CD Setup

This repository uses GitHub Actions for automated testing, building, and deployment to AWS ECS.

## Workflows

### 1. `deploy.yml` - Application Deployment
**Trigger:** Push to `main` branch (for application code changes)

**Steps:**
1. **Test** - Runs Python tests with pytest
2. **Build** - Creates Docker image and pushes to ECR
3. **Deploy** - Updates ECS service with new image
4. **Verify** - Checks deployment health

### 2. `terraform.yml` - Infrastructure Management  
**Trigger:** Changes to `terraform/**` files

**Steps:**
1. **Plan** - Shows infrastructure changes on PRs
2. **Apply** - Applies changes when merged to `main`

### 3. `tests.yml` - Code Quality
**Trigger:** All pushes and PRs

**Steps:**
1. **Lint** - Code quality checks with flake8
2. **Test** - Unit tests with coverage reporting
3. **Security** - Vulnerability scanning with Trivy

## Required GitHub Secrets

Add these secrets to your repository settings:

```
AWS_ACCESS_KEY_ID     - AWS access key for deployment
AWS_SECRET_ACCESS_KEY - AWS secret key for deployment
```

## AWS IAM Permissions

The GitHub Actions user needs these permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "ecr:InitiateLayerUpload",
                "ecr:UploadLayerPart",
                "ecr:CompleteLayerUpload",
                "ecr:PutImage"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ecs:DescribeTaskDefinition",
                "ecs:RegisterTaskDefinition",
                "ecs:UpdateService",
                "ecs:DescribeServices"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "elbv2:DescribeLoadBalancers"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "iam:PassRole"
            ],
            "Resource": "arn:aws:iam::*:role/ecs_task_execution_role"
        }
    ]
}
```

## Deployment Flow

### Application Changes
1. **Push to feature branch** → Runs tests
2. **Create PR** → Runs tests + shows Terraform plan if infrastructure changed
3. **Merge to main** → Builds Docker image → Pushes to ECR → Updates ECS service

### Infrastructure Changes  
1. **Modify `terraform/` files** → Shows plan on PR
2. **Merge to main** → Applies Terraform changes

## Monitoring

- **GitHub Actions tab** - View workflow runs
- **Security tab** - View vulnerability scans
- **ECS Console** - Monitor service health
- **CloudWatch** - Application logs

## Local Development

To test the Docker build locally:
```bash
docker build -t run-my-pool-app .
docker run -p 8000:8000 run-my-pool-app
```

To run tests locally:
```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```

## Rollback

If deployment fails:
```bash
# Rollback to previous task definition
aws ecs update-service --cluster run-my-pool-cluster --service run-my-pool-service --task-definition run-my-pool-task:PREVIOUS_REVISION
```
