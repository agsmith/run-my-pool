#!/bin/bash

# Cleanup Local AWS Deployment and Terraform Files
# This script removes all AWS-related deployment files and Terraform infrastructure

set -e

echo "🧹 Cleaning up local AWS deployment and Terraform files..."
echo "==========================================================="

# Function to safely remove files/directories
safe_remove() {
    local path="$1"
    if [[ -e "$path" ]]; then
        echo "  ❌ Removing: $path"
        rm -rf "$path"
    else
        echo "  ✅ Already gone: $path"
    fi
}

# Navigate to project root
cd "$(dirname "$0")"

echo ""
echo "1️⃣ Removing Terraform infrastructure directory..."
safe_remove "aws/"

echo ""
echo "2️⃣ Removing AWS deployment scripts..."
safe_remove "deploy-aws.sh"
safe_remove "deploy-aws-secure.sh"
safe_remove "deploy-production.sh"
safe_remove "deploy-simple.sh"
safe_remove "check-aws-profile.sh"
safe_remove "check-aws-status.sh"
safe_remove "review-aws-resources.sh"
safe_remove "cleanup-aws.sh"

echo ""
echo "3️⃣ Removing AWS configuration files..."
safe_remove "simple-stack.yaml"
safe_remove "apprunner-service.json"
safe_remove "task-definition.json"
safe_remove "debug-task.json"
safe_remove "debug-task-custom-dns.json"
safe_remove "test-basic-connectivity.json"
safe_remove "test-ecr-connectivity.json"

echo ""
echo "4️⃣ Removing AWS deployment documentation..."
safe_remove "AWS_DEPLOYMENT_PLAN.md"
safe_remove "DEPLOYMENT_GUIDE.md"
safe_remove "DEPLOYMENT_SUMMARY.md"
safe_remove "DEPLOYMENT_UPDATE.md"
safe_remove "PRODUCTION_DEPLOYMENT_SUCCESS.md"
safe_remove "DNS_SETUP.md"
safe_remove "HTTPS_SETUP.md"

echo ""
echo "5️⃣ Removing AWS-related environment files..."
safe_remove ".env.production"

echo ""
echo "6️⃣ Removing AWS-related shell scripts..."
safe_remove "configure-dns.sh"
safe_remove "check-dns-status.sh"

echo ""
echo "7️⃣ Removing AWS Makefile..."
safe_remove "Makefile"

echo ""
echo "8️⃣ Checking for any remaining AWS-related files..."
echo "Searching for files containing 'aws', 'terraform', or 'ecs'..."

# Find any remaining AWS-related files (excluding .git and common files)
remaining_files=$(find . -type f \( -name "*.tf" -o -name "*.tfstate*" -o -name "*.tfplan" -o -name "terraform*" \) 2>/dev/null | grep -v ".git" || true)

if [[ -n "$remaining_files" ]]; then
    echo "⚠️  Found remaining Terraform files:"
    echo "$remaining_files"
    echo ""
    echo "Would you like to remove these as well? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo "$remaining_files" | xargs rm -f
        echo "✅ Additional files removed"
    fi
else
    echo "✅ No additional Terraform files found"
fi

echo ""
echo "9️⃣ Updating .gitignore to prevent future AWS files..."

# Add AWS-related entries to .gitignore if they don't exist
gitignore_entries=(
    "# AWS and Terraform files"
    "*.tfstate"
    "*.tfstate.*"
    "*.tfplan"
    ".terraform/"
    ".terraform.lock.hcl"
    "aws/infrastructure/"
    "*.pem"
    "*.key"
    ".env.production"
    "apprunner-service.json"
    "task-definition.json"
)

if [[ -f ".gitignore" ]]; then
    for entry in "${gitignore_entries[@]}"; do
        if ! grep -qF "$entry" .gitignore; then
            echo "$entry" >> .gitignore
        fi
    done
    echo "✅ Updated .gitignore with AWS-related exclusions"
else
    printf "%s\n" "${gitignore_entries[@]}" > .gitignore
    echo "✅ Created .gitignore with AWS-related exclusions"
fi

echo ""
echo "🎉 Cleanup completed successfully!"
echo "======================================"
echo ""
echo "📋 Summary of removed items:"
echo "  - Terraform infrastructure (aws/ directory)"
echo "  - AWS deployment scripts"
echo "  - AWS configuration files"
echo "  - AWS deployment documentation"
echo "  - Production environment files"
echo "  - DNS and HTTPS setup files"
echo "  - AWS Makefile"
echo ""
echo "📁 Remaining project files:"
echo "  - Core application code (main.py, models.py, etc.)"
echo "  - Templates and static files"
echo "  - Local development configuration"
echo "  - Tests and documentation"
echo ""
echo "💡 Next steps:"
echo "  1. Your local development environment is intact"
echo "  2. You can still run the app locally with: uvicorn main:app --reload"
echo "  3. If you need AWS deployment again, you'll need to recreate the infrastructure"
echo ""
echo "✅ Local AWS cleanup complete!"
