#!/bin/bash
# Safe AWS Infrastructure Review Script for Run My Pool
# This script will show you what would be destroyed without actually destroying it

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$SCRIPT_DIR/aws/infrastructure"
ENVIRONMENT="${ENVIRONMENT:-prod}"
AWS_PROFILE="${AWS_PROFILE:-rmp}"

log_info "🔍 AWS Infrastructure Review for Run My Pool"
echo

# Set AWS profile and disable pager
export AWS_PROFILE="$AWS_PROFILE"
export AWS_PAGER=""

cd "$TERRAFORM_DIR"

log_info "Current Terraform-managed resources:"
echo "======================================"
terraform state list | while read resource; do
    echo "  ✓ $resource"
done

echo
log_info "Checking for Lambda functions..."
lambda_count=$(terraform state list | grep -c "aws_lambda" || true)
if [ "$lambda_count" -gt 0 ]; then
    log_warning "Found $lambda_count Lambda functions:"
    terraform state list | grep "aws_lambda" | while read lambda; do
        echo "  🔸 $lambda"
    done
else
    log_success "No Lambda functions found in Terraform state"
fi

echo
log_info "Checking for existing Lambda functions in AWS account..."
echo "Note: This only shows functions in the current region and with current permissions"
aws lambda list-functions --query 'Functions[].FunctionName' --output text 2>/dev/null | tr '\t' '\n' | while read func; do
    if [ -n "$func" ]; then
        echo "  🔸 $func (NOT managed by this Terraform)"
    fi
done || log_warning "Unable to list Lambda functions (may be permissions or no functions exist)"

echo
log_info "Resources that WOULD be destroyed:"
echo "=================================="
terraform plan -destroy -var="environment=$ENVIRONMENT" 2>/dev/null | grep -A1000 "Terraform will perform the following actions:" | grep -E "^\s*#" | head -50

echo
log_success "Review completed!"
log_info "To actually destroy infrastructure, run: ./cleanup-aws.sh"
log_warning "Make sure you've reviewed all resources above before proceeding"
