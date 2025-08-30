# GitHub Actions IAM User Setup

Follow these steps to create an IAM user for GitHub Actions:

## 1. Create IAM User

```bash
aws iam create-user --user-name github-actions-runmypool
```

## 2. Create Access Keys

```bash
aws iam create-access-key --user-name github-actions-runmypool
```

Save the `AccessKeyId` and `SecretAccessKey` - you'll need these for GitHub secrets.

## 3. Create IAM Policy

Create a file `github-actions-policy.json`:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "ECRPermissions",
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
            "Sid": "ECSPermissions",
            "Effect": "Allow",
            "Action": [
                "ecs:DescribeTaskDefinition",
                "ecs:RegisterTaskDefinition",
                "ecs:UpdateService",
                "ecs:DescribeServices",
                "ecs:DescribeClusters"
            ],
            "Resource": "*"
        },
        {
            "Sid": "ALBPermissions",
            "Effect": "Allow",
            "Action": [
                "elbv2:DescribeLoadBalancers",
                "elbv2:DescribeTargetGroups",
                "elbv2:DescribeListeners"
            ],
            "Resource": "*"
        },
        {
            "Sid": "IAMPassRole",
            "Effect": "Allow",
            "Action": "iam:PassRole",
            "Resource": [
                "arn:aws:iam::*:role/ecs_task_execution_role",
                "arn:aws:iam::*:role/ecs_task_role"
            ]
        },
        {
            "Sid": "TerraformPermissions",
            "Effect": "Allow",
            "Action": [
                "ec2:*",
                "vpc:*",
                "iam:*",
                "rds:*",
                "secretsmanager:*",
                "acm:*",
                "route53:*",
                "logs:*"
            ],
            "Resource": "*"
        }
    ]
}
```

## 4. Attach Policy

```bash
# Create the policy
aws iam create-policy \
    --policy-name GitHubActionsRunMyPoolPolicy \
    --policy-document file://github-actions-policy.json

# Attach policy to user
aws iam attach-user-policy \
    --user-name github-actions-runmypool \
    --policy-arn arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):policy/GitHubActionsRunMyPoolPolicy
```

## 5. Add Secrets to GitHub

Go to your GitHub repository → Settings → Secrets and variables → Actions

Add these secrets:
- `AWS_ACCESS_KEY_ID`: The access key from step 2
- `AWS_SECRET_ACCESS_KEY`: The secret key from step 2

## 6. Test the Setup

Push a commit to the `main` branch and check the Actions tab to see if the deployment works.

## Security Notes

- The IAM user has broad permissions for Terraform. In production, consider:
  - Using temporary credentials with assume role
  - Restricting permissions to specific resources
  - Using separate AWS accounts for different environments
  - Implementing approval workflows for production deployments
