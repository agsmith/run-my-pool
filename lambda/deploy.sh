#!/bin/bash

# NFL Game Updater Lambda Deployment Script
# This script packages and deploys the Lambda function to AWS

set -e

# Configuration
LAMBDA_FUNCTION_NAME="nfl-game-updater"
LAMBDA_ROLE_ARN="arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-execution-role"
REGION="us-east-1"
PYTHON_VERSION="python3.11"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting NFL Game Updater Lambda deployment...${NC}"

# Create deployment directory
DEPLOY_DIR="./deploy"
mkdir -p $DEPLOY_DIR

# Copy source files
echo -e "${YELLOW}Copying source files...${NC}"
cp nfl_game_updater.py $DEPLOY_DIR/
cp models.py $DEPLOY_DIR/
cp requirements.txt $DEPLOY_DIR/

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
cd $DEPLOY_DIR
pip install -r requirements.txt -t .

# Remove unnecessary files to reduce package size
echo -e "${YELLOW}Cleaning up package...${NC}"
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
rm -rf .pytest_cache 2>/dev/null || true
rm -rf *.dist-info 2>/dev/null || true

# Create deployment package
echo -e "${YELLOW}Creating deployment package...${NC}"
zip -r ../nfl-game-updater.zip . -q

# Go back to original directory
cd ..

# Check if Lambda function exists
echo -e "${YELLOW}Checking if Lambda function exists...${NC}"
if aws lambda get-function --function-name $LAMBDA_FUNCTION_NAME --region $REGION >/dev/null 2>&1; then
    echo -e "${YELLOW}Function exists. Updating function code...${NC}"
    aws lambda update-function-code \
        --function-name $LAMBDA_FUNCTION_NAME \
        --zip-file fileb://nfl-game-updater.zip \
        --region $REGION
else
    echo -e "${YELLOW}Function does not exist. Creating new function...${NC}"
    aws lambda create-function \
        --function-name $LAMBDA_FUNCTION_NAME \
        --runtime $PYTHON_VERSION \
        --role $LAMBDA_ROLE_ARN \
        --handler nfl_game_updater.lambda_handler \
        --zip-file fileb://nfl-game-updater.zip \
        --timeout 300 \
        --memory-size 256 \
        --region $REGION \
        --description "Updates NFL game results and pool entries"
fi

# Update function configuration
echo -e "${YELLOW}Updating function configuration...${NC}"
aws lambda update-function-configuration \
    --function-name $LAMBDA_FUNCTION_NAME \
    --timeout 300 \
    --memory-size 256 \
    --environment Variables='{
        "MYSQL_HOST":"YOUR_RDS_ENDPOINT",
        "MYSQL_USER":"admin",
        "MYSQL_DB":"rmp",
        "DB_SECRET_NAME":"rmp-database-credentials"
    }' \
    --region $REGION

# Create or update EventBridge rules to run every 15 minutes during NFL game times
# Including 1 hour before and after expected game times
echo -e "${YELLOW}Setting up EventBridge schedules...${NC}"

# Sunday games: 12:00 PM - 12:30 AM ET next day (17:00 - 05:30 UTC next day)
# Covers 1 hour before 1:00 PM games through 1 hour after 11:30 PM games
aws events put-rule \
    --name "nfl-game-updater-sunday" \
    --schedule-expression "cron(0/15 17-23,0-5 ? * SUN *)" \
    --description "Run NFL game updater every 15 minutes during Sunday games (including 1hr buffer)" \
    --region $REGION

# Monday Night Football: 7:00 PM - 12:30 AM ET next day (00:00 - 05:30 UTC next day)
# Covers 1 hour before 8:00 PM through 1 hour after 11:30 PM
aws events put-rule \
    --name "nfl-game-updater-monday" \
    --schedule-expression "cron(0/15 0-5 ? * TUE *)" \
    --description "Run NFL game updater every 15 minutes during Monday Night Football (including 1hr buffer)" \
    --region $REGION

# Thursday Night Football: 7:00 PM - 12:30 AM ET next day (00:00 - 05:30 UTC next day)
# Covers 1 hour before 8:00 PM through 1 hour after 11:30 PM
aws events put-rule \
    --name "nfl-game-updater-thursday" \
    --schedule-expression "cron(0/15 0-5 ? * FRI *)" \
    --description "Run NFL game updater every 15 minutes during Thursday Night Football (including 1hr buffer)" \
    --region $REGION

# Saturday games (late season): 12:00 PM - 12:30 AM ET next day (17:00 - 05:30 UTC next day)
# Covers 1 hour before 1:00 PM games through 1 hour after 11:30 PM games
aws events put-rule \
    --name "nfl-game-updater-saturday" \
    --schedule-expression "cron(0/15 17-23,0-5 ? * SAT *)" \
    --description "Run NFL game updater every 15 minutes during Saturday games (including 1hr buffer)" \
    --region $REGION

# Add permissions for EventBridge to invoke Lambda
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
LAMBDA_ARN="arn:aws:lambda:$REGION:$ACCOUNT_ID:function:$LAMBDA_FUNCTION_NAME"

# Permission for Sunday games
aws lambda add-permission \
    --function-name $LAMBDA_FUNCTION_NAME \
    --statement-id "allow-eventbridge-sunday" \
    --action "lambda:InvokeFunction" \
    --principal events.amazonaws.com \
    --source-arn "arn:aws:events:$REGION:$ACCOUNT_ID:rule/nfl-game-updater-sunday" \
    --region $REGION 2>/dev/null || echo "Sunday permission already exists"

# Permission for Monday games
aws lambda add-permission \
    --function-name $LAMBDA_FUNCTION_NAME \
    --statement-id "allow-eventbridge-monday" \
    --action "lambda:InvokeFunction" \
    --principal events.amazonaws.com \
    --source-arn "arn:aws:events:$REGION:$ACCOUNT_ID:rule/nfl-game-updater-monday" \
    --region $REGION 2>/dev/null || echo "Monday permission already exists"

# Permission for Thursday games
aws lambda add-permission \
    --function-name $LAMBDA_FUNCTION_NAME \
    --statement-id "allow-eventbridge-thursday" \
    --action "lambda:InvokeFunction" \
    --principal events.amazonaws.com \
    --source-arn "arn:aws:events:$REGION:$ACCOUNT_ID:rule/nfl-game-updater-thursday" \
    --region $REGION 2>/dev/null || echo "Thursday permission already exists"

# Permission for Saturday games
aws lambda add-permission \
    --function-name $LAMBDA_FUNCTION_NAME \
    --statement-id "allow-eventbridge-saturday" \
    --action "lambda:InvokeFunction" \
    --principal events.amazonaws.com \
    --source-arn "arn:aws:events:$REGION:$ACCOUNT_ID:rule/nfl-game-updater-saturday" \
    --region $REGION 2>/dev/null || echo "Saturday permission already exists"

# Add targets to EventBridge rules
aws events put-targets \
    --rule "nfl-game-updater-sunday" \
    --targets "Id"="1","Arn"="$LAMBDA_ARN" \
    --region $REGION

aws events put-targets \
    --rule "nfl-game-updater-monday" \
    --targets "Id"="1","Arn"="$LAMBDA_ARN" \
    --region $REGION

aws events put-targets \
    --rule "nfl-game-updater-thursday" \
    --targets "Id"="1","Arn"="$LAMBDA_ARN" \
    --region $REGION

aws events put-targets \
    --rule "nfl-game-updater-saturday" \
    --targets "Id"="1","Arn"="$LAMBDA_ARN" \
    --region $REGION

# Clean up
echo -e "${YELLOW}Cleaning up temporary files...${NC}"
rm -rf $DEPLOY_DIR
rm nfl-game-updater.zip

echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${GREEN}Function Name: $LAMBDA_FUNCTION_NAME${NC}"
echo -e "${GREEN}Region: $REGION${NC}"
echo -e "${GREEN}Schedules (including 1-hour buffer):${NC}"
echo -e "  - Sunday: Every 15 minutes, 12:00 PM - 12:30 AM ET (11 hours)"
echo -e "  - Monday: Every 15 minutes, 7:00 PM - 12:30 AM ET (Monday Night Football)"
echo -e "  - Thursday: Every 15 minutes, 7:00 PM - 12:30 AM ET (Thursday Night Football)"
echo -e "  - Saturday: Every 15 minutes, 12:00 PM - 12:30 AM ET (Late season games)"

echo -e "${YELLOW}Next steps:${NC}"
echo -e "1. Update the LAMBDA_ROLE_ARN in this script with your actual IAM role ARN"
echo -e "2. Update the MYSQL_HOST environment variable with your RDS endpoint"
echo -e "3. Ensure your IAM role has the following permissions:"
echo -e "   - VPC access (if RDS is in VPC)"
echo -e "   - Secrets Manager read access"
echo -e "   - CloudWatch Logs write access"
echo -e "4. Test the function: aws lambda invoke --function-name $LAMBDA_FUNCTION_NAME output.json"
