# Troubleshooting Guide

Common issues and solutions when using AWS API Factory.

## Table of Contents

- [CLI Issues](#cli-issues)
- [Configuration Errors](#configuration-errors)
- [Deployment Failures](#deployment-failures)
- [Runtime Errors](#runtime-errors)
- [Authentication Issues](#authentication-issues)
- [Performance Issues](#performance-issues)
- [Debugging Tips](#debugging-tips)

---

## CLI Issues

### "command not found: factory"

**Cause**: CLI not installed or not in PATH

**Solution**:
```bash
# Install or reinstall
pip install aws-api-factory

# Verify installation
pip show aws-api-factory

# Check CLI is available
which factory
factory --version
```

If using a virtual environment, ensure it's activated:
```bash
source .venv/bin/activate
```

### "No module named 'aws_api_factory'"

**Cause**: Package not installed in current environment

**Solution**:
```bash
# Install in development mode
pip install -e .

# Or install from PyPI
pip install aws-api-factory
```

### "CDK CLI not found"

**Cause**: AWS CDK CLI not installed

**Solution**:
```bash
# Install CDK CLI globally
npm install -g aws-cdk

# Verify installation
cdk --version
```

---

## Configuration Errors

### "Invalid configuration: missing required field"

**Cause**: Required field missing from factory.yaml

**Example error**:
```
Configuration Error:
  project.name: Field required
```

**Solution**: Add the missing field:
```yaml
project:
  name: my-api  # Add this
  envs: [dev]
```

### "Invalid configuration: service 'xyz' not found"

**Cause**: Route references a service not defined in compute.lambda.services

**Example**:
```yaml
apis:
  rest:
    routes:
      - path: /users
        service: users  # ← Error: not defined below

compute:
  lambda:
    services:
      orders:  # Only 'orders' is defined, not 'users'
        entry: src/orders/handler.py:handler
```

**Solution**: Define the missing service:
```yaml
compute:
  lambda:
    services:
      users:
        entry: src/services/users/handler.py:handler
```

### "Invalid entry point format"

**Cause**: Entry point doesn't match expected format

**Example**:
```
Error: Entry point must be in format 'path/to/file.py:handler_function'
Invalid: src/handler.py (missing handler function)
```

**Solution**: Use correct format `file.py:function`:
```yaml
services:
  hello:
    entry: src/services/hello/handler.py:handler
```

### "Invalid profile: must be 'minimal' or 'scalable'"

**Cause**: Typo in profile name

**Solution**:
```yaml
profile: minimal   # Correct
# profile: Minimal  # Wrong (case-sensitive)
# profile: min      # Wrong (abbreviated)
```

### YAML Syntax Errors

**Cause**: Incorrect YAML formatting

**Common issues**:
```yaml
# Wrong: tabs instead of spaces
services:
	hello:  # ← Tab character (use spaces!)
    entry: ...

# Wrong: missing colon
routes
  - path: /hello  # ← Missing colon after 'routes'

# Wrong: incorrect indentation
routes:
- path: /hello  # ← Should be indented
```

**Solution**: Use a YAML validator or linter:
```bash
# Install yamllint
pip install yamllint

# Check syntax
yamllint factory.yaml
```

---

## Deployment Failures

### "Unable to resolve AWS account"

**Cause**: AWS credentials not configured

**Solution**:
```bash
# Configure AWS CLI
aws configure

# Or use environment variables
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export AWS_DEFAULT_REGION=us-east-1

# Verify credentials
aws sts get-caller-identity
```

### "CDK bootstrap required"

**Cause**: CDK not bootstrapped in target region

**Example error**:
```
This stack uses assets, so the toolkit stack must be deployed
```

**Solution**:
```bash
# Bootstrap CDK in your account/region
cdk bootstrap aws://ACCOUNT-ID/REGION

# Example
cdk bootstrap aws://123456789012/us-east-1
```

### "Resource limit exceeded"

**Cause**: AWS account limits reached

**Common limits**:
- Lambda functions per region: 1000
- API Gateway APIs per region: 600
- IAM roles per account: 1000

**Solution**:
1. Request limit increase in AWS console
2. Delete unused resources
3. Use a different region

### "Deployment timeout"

**Cause**: CloudFormation stack creation taking too long

**Solution**:
1. Check CloudFormation console for progress
2. Look for resources stuck in CREATE_IN_PROGRESS
3. Consider breaking into smaller stacks
4. Check for circular dependencies

### "UPDATE_ROLLBACK_FAILED"

**Cause**: Failed deployment that couldn't roll back

**Solution**:
```bash
# Option 1: Continue rollback
aws cloudformation continue-update-rollback \
    --stack-name my-api-dev

# Option 2: Delete and recreate
factory destroy dev --force
factory deploy dev
```

### "Resource already exists"

**Cause**: Resource with same name exists from previous deployment

**Solution**:
```bash
# Delete orphaned resources manually
aws lambda delete-function --function-name my-api-dev-hello

# Or use unique naming
project:
  name: my-api-v2  # Change project name
```

---

## Runtime Errors

### Lambda 502 Bad Gateway

**Cause**: Lambda returned invalid response format

**Example Lambda logs**:
```
Response payload is not valid JSON
```

**Solution**: Return proper API Gateway format:
```python
# Wrong
def handler(event, context):
    return {"message": "Hello"}  # Missing statusCode

# Correct
def handler(event, context):
    return {
        "statusCode": 200,
        "body": '{"message": "Hello"}'
    }
```

### Lambda Timeout

**Cause**: Function exceeds configured timeout

**Example logs**:
```
Task timed out after 30.00 seconds
```

**Solutions**:
1. Increase timeout in config:
```yaml
compute:
  lambda:
    services:
      slow_task:
        timeout_s: 120  # Increase to 2 minutes
```

2. Optimize code performance
3. Break into smaller operations
4. Use async patterns (Step Functions, SQS)

### Lambda Out of Memory

**Cause**: Function exceeds memory limit

**Example logs**:
```
Runtime exited with error: signal: killed
REPORT RequestId: xxx Duration: xxx ms Memory Size: 512 MB Max Memory Used: 512 MB
```

**Solution**: Increase memory:
```yaml
compute:
  lambda:
    services:
      heavy_task:
        memory_mb: 1024  # Double memory
```

### "No module named 'x'"

**Cause**: Dependency not included in Lambda package

**Solution**: Ensure dependencies are installed:
```bash
# Create requirements.txt
pip freeze > requirements.txt

# Or use Lambda layers for common dependencies
```

### App Runner Container Crash

**Cause**: Container exits unexpectedly

**Check logs**:
```bash
aws logs tail /aws/apprunner/my-api-dev-api/application --follow
```

**Common causes**:
- Missing environment variables
- Database connection failure
- Port mismatch

---

## Authentication Issues

### 403 Forbidden with API Key

**Cause**: Invalid or missing API key

**Solutions**:
1. Verify key is correct:
```bash
aws apigateway get-api-key --api-key KEY_ID --include-value
```

2. Check key is associated with usage plan

3. Ensure header is correct:
```bash
curl -H "x-api-key: YOUR_KEY" https://api.example.com/endpoint
```

### 401 Unauthorized with Cognito

**Cause**: Invalid or expired JWT token

**Solutions**:
1. Check token hasn't expired:
```python
import jwt
token = "eyJ..."
decoded = jwt.decode(token, options={"verify_signature": False})
print(decoded["exp"])  # Expiration timestamp
```

2. Verify token is from correct user pool

3. Use ID token (not access token) for API Gateway

### "Signature does not match" with IAM Auth

**Cause**: SigV4 signature calculation error

**Solutions**:
1. Check system clock is accurate (within 5 minutes)
2. Verify region matches API region
3. Use boto3 or AWS SDK for signing:
```python
from requests_aws4auth import AWS4Auth
import boto3

session = boto3.Session()
credentials = session.get_credentials()
auth = AWS4Auth(
    credentials.access_key,
    credentials.secret_key,
    session.region_name,
    "execute-api"
)
```

---

## Performance Issues

### High Lambda Cold Start Times

**Cause**: Large package size or slow initialization

**Solutions**:
1. Reduce package size:
```bash
# Check package size
du -sh .

# Remove unnecessary files
pip install --target . -r requirements.txt --upgrade
rm -rf *.dist-info __pycache__
```

2. Initialize outside handler:
```python
# Do this at module level, not in handler
import boto3
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("my-table")

def handler(event, context):
    # Use pre-initialized resources
    pass
```

3. Use provisioned concurrency for critical functions

### Slow API Response Times

**Causes and solutions**:

1. **Lambda cold starts**: Use `profile: scalable` for provisioned concurrency

2. **Network latency**: Ensure Lambda is in same region as data sources

3. **Inefficient code**: Profile and optimize hot paths

4. **Large response payloads**: Paginate results, compress responses

### App Runner Scale-Up Lag

**Cause**: New instances take ~30s to start

**Solutions**:
1. Increase min_instances:
```yaml
compute:
  apprunner:
    services:
      api:
        min_instances: 2  # Always have 2 warm
```

2. Optimize container startup time
3. Use smaller base images

---

## Debugging Tips

### Enable Verbose Logging

Add logging to your handlers:
```python
import logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def handler(event, context):
    logger.debug(f"Event: {event}")
    logger.info(f"Processing request")
    # ...
```

### View CloudWatch Logs

```bash
# Lambda logs
aws logs tail /aws/lambda/my-api-dev-hello --follow

# API Gateway logs (if enabled)
aws logs tail /aws/apigateway/my-api-dev --follow

# App Runner logs
aws logs tail /aws/apprunner/my-api-dev-api/application --follow
```

### Use CloudWatch Logs Insights

Query logs in AWS Console:
```
# Find errors
fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc
| limit 100

# Calculate duration
fields @timestamp, @duration
| stats avg(@duration), max(@duration) by bin(5m)
```

### Test Locally

Test Lambda handlers without deploying:
```python
# test_local.py
from src.services.hello.handler import handler

event = {
    "httpMethod": "GET",
    "path": "/hello",
    "queryStringParameters": None,
    "pathParameters": None,
    "body": None
}

response = handler(event, None)
print(response)
```

### CDK Diff Before Deploy

See what changes will be made:
```bash
cdk diff --context env=dev
```

### Validate CloudFormation Template

Check synthesized template:
```bash
factory synth --show

# Or save to file
factory synth --output template.yaml
```

---

## Getting Help

If you can't resolve an issue:

1. **Check GitHub Issues**: [github.com/seanmeehan/aws-api-factory/issues](https://github.com/seanmeehan/aws-api-factory/issues)

2. **Search AWS Documentation**:
   - [API Gateway Troubleshooting](https://docs.aws.amazon.com/apigateway/latest/developerguide/troubleshooting.html)
   - [Lambda Troubleshooting](https://docs.aws.amazon.com/lambda/latest/dg/troubleshooting.html)

3. **Open an Issue**: Include:
   - AWS API Factory version (`factory --version`)
   - Python version (`python --version`)
   - Full error message
   - Relevant config (redact secrets)
   - Steps to reproduce
