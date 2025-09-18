# NFL Game Updater Lambda Function

This Lambda function automatically checks NFL game results from ESPN API and updates the RunMyPool database accordingly. It processes game outcomes, updates pick results, and eliminates losing entries from survivor pools.

## Features

- **Automated Game Result Fetching**: Retrieves real-time NFL scores from ESPN's free API
- **Database Updates**: Updates schedule table with game results
- **Pick Processing**: Marks picks as win/loss based on game outcomes
- **Entry Elimination**: Automatically eliminates entries with losing picks
- **Audit Logging**: Comprehensive logging for all database changes
- **Error Handling**: Robust error handling and recovery mechanisms
- **Scheduled Execution**: Runs automatically every hour during NFL season

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   EventBridge   │───▶│  Lambda Function │───▶│   RDS MySQL     │
│   (Scheduler)   │    │  (NFL Updater)   │    │   (Database)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │    ESPN API      │
                       │  (Game Results)  │
                       └──────────────────┘
```

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **RDS MySQL Database** with RunMyPool schema
3. **VPC Configuration** for Lambda to access RDS
4. **AWS CLI** configured with appropriate credentials

## Files Structure

```
lambda/
├── nfl_game_updater.py          # Main Lambda function
├── models.py                    # Database models
├── requirements.txt             # Python dependencies
├── deploy.sh                    # Deployment script
├── cloudformation-template.yaml # Infrastructure as Code
├── test_lambda.py              # Local testing script
└── README.md                   # This file
```

## Setup Instructions

### 1. Database Preparation

Ensure your RDS MySQL database has the required tables:
- `teams` - NFL team information
- `schedule` - Game schedule with results
- `picks` - User picks
- `entries` - Pool entries
- `audit_logs` - Audit trail

### 2. Environment Configuration

Create a `.env` file for local testing (not included in deployment):

```bash
# Database Configuration
MYSQL_HOST=your-rds-endpoint.region.rds.amazonaws.com
MYSQL_USER=admin
MYSQL_PASSWORD=your-secure-password
MYSQL_DB=rmp
MYSQL_PORT=3306

# AWS Configuration
AWS_REGION=us-east-1
DB_SECRET_NAME=rmp-database-credentials
```

### 3. Local Testing

Before deployment, test the function locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export MYSQL_HOST=your-rds-endpoint.region.rds.amazonaws.com
export MYSQL_USER=admin
export MYSQL_PASSWORD=your-password

# Run tests
python test_lambda.py
```

### 4. Infrastructure Deployment

Deploy the infrastructure using CloudFormation:

```bash
# Deploy CloudFormation stack
aws cloudformation create-stack \
    --stack-name nfl-game-updater-infrastructure \
    --template-body file://cloudformation-template.yaml \
    --parameters ParameterKey=DatabaseEndpoint,ParameterValue=your-rds-endpoint \
                 ParameterKey=VpcId,ParameterValue=vpc-xxxxxx \
                 ParameterKey=SubnetIds,ParameterValue=subnet-xxxxx,subnet-yyyyy \
                 ParameterKey=DatabaseSecurityGroupId,ParameterValue=sg-xxxxxx \
    --capabilities CAPABILITY_NAMED_IAM
```

### 5. Function Deployment

Deploy the Lambda function code:

```bash
# Make deployment script executable
chmod +x deploy.sh

# Update configuration in deploy.sh
# - Set LAMBDA_ROLE_ARN to your IAM role ARN
# - Set REGION to your preferred AWS region
# - Update environment variables

# Deploy the function
./deploy.sh
```

## Configuration

### Environment Variables

The Lambda function uses these environment variables:

- `MYSQL_HOST` - RDS endpoint
- `MYSQL_DB` - Database name (default: rmp)
- `DB_SECRET_NAME` - AWS Secrets Manager secret name
- `AWS_REGION` - AWS region for Secrets Manager

### Scheduling

The function is scheduled to run every 15 minutes during NFL game times using multiple EventBridge rules:

- **Sunday Games**: Every 15 minutes, 1:00 PM - 11:30 PM ET
- **Monday Night Football**: Every 15 minutes, 8:00 PM - 11:30 PM ET  
- **Thursday Night Football**: Every 15 minutes, 8:00 PM - 11:30 PM ET
- **Saturday Games**: Every 15 minutes, 1:00 PM - 11:30 PM ET (late season only)

The function also includes intelligent game-time checking that will skip execution if it's not during typical NFL game hours, even if triggered by the schedule.

To modify schedules:

```bash
# Update Sunday schedule to every 10 minutes
aws events put-rule \
    --name "nfl-game-updater-sunday" \
    --schedule-expression "cron(0/10 18-23,0-4 ? * SUN *)"
```

### Game Time Logic

The function automatically detects NFL game times based on:
- Current month (September through February)
- Day of week and time
- Current NFL week (for Saturday games)

## Monitoring and Debugging

### CloudWatch Logs

Monitor function execution:

```bash
# View recent logs
aws logs tail /aws/lambda/nfl-game-updater --follow

# View specific log stream
aws logs describe-log-streams \
    --log-group-name /aws/lambda/nfl-game-updater \
    --order-by LastEventTime \
    --descending
```

### CloudWatch Alarms

The CloudFormation template creates these alarms:
- **Error Alarm**: Triggers on function errors
- **Duration Alarm**: Triggers on long execution times

### Manual Execution

Test the function manually:

```bash
# Invoke function synchronously
aws lambda invoke \
    --function-name nfl-game-updater \
    --payload '{}' \
    output.json

# View output
cat output.json
```

## API Data Source

This function uses ESPN's free NFL API:
- **Endpoint**: `https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard`
- **Rate Limits**: No authentication required, reasonable rate limits
- **Data**: Real-time scores, game status, team information

### Alternative APIs

For production use, consider these alternatives:
- **NFL API**: Official but requires approval
- **SportsData.io**: Paid service with comprehensive data
- **The Sports DB**: Free tier available

## Database Schema Requirements

The function expects these database tables and columns:

### Teams Table
```sql
CREATE TABLE teams (
    id INT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    abbrv VARCHAR(10) NOT NULL UNIQUE,
    logo VARCHAR(255)
);
```

### Schedule Table
```sql
CREATE TABLE schedule (
    game_id INT PRIMARY KEY,
    week_num INT NOT NULL,
    home_team_id INT NOT NULL,
    away_team_id INT NOT NULL,
    start_time DATETIME NOT NULL,
    winning_team_id VARCHAR(100) DEFAULT '99',
    FOREIGN KEY (home_team_id) REFERENCES teams(id),
    FOREIGN KEY (away_team_id) REFERENCES teams(id)
);
```

### Picks Table
```sql
CREATE TABLE picks (
    id VARCHAR(36) PRIMARY KEY,
    entry_id VARCHAR(36) NOT NULL,
    week INT,
    team_id INT,
    result VARCHAR(10), -- 'win', 'loss', 'pending'
    FOREIGN KEY (team_id) REFERENCES teams(id)
);
```

### Entries Table
```sql
CREATE TABLE entries (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    pool_id VARCHAR(36) NOT NULL,
    alive BOOLEAN DEFAULT TRUE
);
```

## Security Considerations

1. **VPC Configuration**: Lambda runs in VPC for database access
2. **Secrets Management**: Database credentials stored in AWS Secrets Manager
3. **IAM Permissions**: Minimal required permissions only
4. **Input Validation**: All API responses validated before database updates
5. **SQL Injection Protection**: Uses SQLAlchemy ORM for safe queries

## Troubleshooting

### Common Issues

1. **Database Connection Timeout**
   - Check VPC configuration
   - Verify security group rules
   - Ensure subnets have internet access for API calls

2. **API Rate Limiting**
   - Implement exponential backoff
   - Cache results to reduce API calls
   - Consider alternative data sources

3. **Function Timeout**
   - Increase timeout limit (max 15 minutes)
   - Optimize database queries
   - Process games in batches

### Debug Mode

Enable debug logging by setting environment variable:
```bash
aws lambda update-function-configuration \
    --function-name nfl-game-updater \
    --environment Variables='{"LOG_LEVEL":"DEBUG"}'
```

## Maintenance

### Weekly Tasks
- Monitor CloudWatch logs for errors
- Verify game results accuracy
- Check eliminated entries

### Seasonal Tasks
- Update team rosters and logos
- Adjust schedule for playoff format
- Archive previous season data

## Cost Optimization

Estimated monthly costs (during NFL season):
- **Lambda**: ~$2-5 (744 invocations/month)
- **CloudWatch**: ~$1-2 (logs and alarms)
- **Secrets Manager**: ~$0.40 (1 secret)
- **Total**: ~$3-7 per month

### Cost Reduction Tips
1. Reduce execution frequency during off-season
2. Use CloudWatch Logs retention policies
3. Optimize function memory allocation
4. Cache API responses when possible

## Support

For issues and questions:
1. Check CloudWatch logs first
2. Verify database connectivity
3. Test API endpoints manually
4. Review function configuration

## License

This code is part of the RunMyPool application and follows the same licensing terms.
