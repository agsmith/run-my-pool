#!/bin/bash

# GitHub Actions IAM User Setup Script
set -e

USER_NAME="github-actions-runmypool"
POLICY_NAME="GitHubActionsRunMyPoolPolicy"

echo "🚀 Setting up GitHub Actions IAM user..."

# Check if user already exists
if aws iam get-user --user-name "$USER_NAME" >/dev/null 2>&1; then
    echo "⚠️  User $USER_NAME already exists"
else
    echo "📝 Creating IAM user: $USER_NAME"
    aws iam create-user --user-name "$USER_NAME"
fi

# Get account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
POLICY_ARN="arn:aws:iam::${ACCOUNT_ID}:policy/${POLICY_NAME}"

# Check if policy already exists
if aws iam get-policy --policy-arn "$POLICY_ARN" >/dev/null 2>&1; then
    echo "⚠️  Policy $POLICY_NAME already exists"
else
    echo "📝 Creating IAM policy: $POLICY_NAME"
    aws iam create-policy \
        --policy-name "$POLICY_NAME" \
        --policy-document file://github-actions-policy.json
fi

# Attach policy to user
echo "🔗 Attaching policy to user"
aws iam attach-user-policy \
    --user-name "$USER_NAME" \
    --policy-arn "$POLICY_ARN"

# Create access key
echo "🔑 Creating access key for user"
ACCESS_KEY_OUTPUT=$(aws iam create-access-key --user-name "$USER_NAME")

# Extract credentials
ACCESS_KEY_ID=$(echo "$ACCESS_KEY_OUTPUT" | jq -r '.AccessKey.AccessKeyId')
SECRET_ACCESS_KEY=$(echo "$ACCESS_KEY_OUTPUT" | jq -r '.AccessKey.SecretAccessKey')

echo ""
echo "✅ Setup completed successfully!"
echo ""
echo "🔐 Add these secrets to your GitHub repository:"
echo "   Repository → Settings → Secrets and variables → Actions"
echo ""
echo "AWS_ACCESS_KEY_ID:"
echo "$ACCESS_KEY_ID"
echo ""
echo "AWS_SECRET_ACCESS_KEY:"
echo "$SECRET_ACCESS_KEY"
echo ""
echo "⚠️  IMPORTANT: Save these credentials securely. The secret key cannot be retrieved again!"
echo ""
echo "🚀 Your GitHub Actions are now ready to deploy!"
