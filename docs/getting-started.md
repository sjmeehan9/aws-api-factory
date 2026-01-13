# Getting Started with AWS API Factory

Deploy your first REST API to AWS in under 15 minutes! This guide walks you through installing AWS API Factory, creating a project, and deploying a working API.

## Prerequisites

Before you begin, ensure you have:

- **Python 3.12 or higher** — [Download Python](https://www.python.org/downloads/)
- **AWS CLI** configured with credentials — [Install AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- **AWS CDK CLI** — Install with `npm install -g aws-cdk`
- **Docker** (optional, for App Runner) — [Install Docker](https://docs.docker.com/get-docker/)

> **New to AWS?** See our [AWS Setup Guide](guides/aws-setup.md) for detailed instructions on creating an AWS account, configuring credentials, and setting up named profiles.

### Verify Prerequisites

```bash
# Check Python version
python --version  # Should be 3.12+

# Check AWS CLI
aws --version
aws sts get-caller-identity  # Should show your AWS account

# Check CDK
cdk --version  # Should be 2.x

# Bootstrap CDK (first time only)
cdk bootstrap aws://ACCOUNT-ID/REGION
```

## Step 1: Install AWS API Factory

```bash
pip install aws-api-factory
```

Verify the installation:

```bash
factory --version
```

## Step 2: Create a New Project

Scaffold a new project with the `factory init` command:

```bash
factory init my-first-api
cd my-first-api
```

This creates a project with the following structure:

```
my-first-api/
├── factory.yaml           # Your API configuration
├── infra/                 # CDK infrastructure
│   └── app.py
├── src/
│   └── services/
│       ├── hello/         # Example Lambda handler
│       │   └── handler.py
│       └── orders/        # CRUD example
│           └── handler.py
└── tests/
```

## Step 3: Explore the Configuration

Open `factory.yaml` to see your API configuration:

```yaml
project:
  name: my-first-api
  envs:
    - dev
    - prod

profile: minimal

apis:
  rest:
    enabled: true
    routes:
      - path: /hello
        methods: [GET]
        service: hello
        auth: none

compute:
  lambda:
    enabled: true
    services:
      hello:
        entry: src/services/hello/handler.py:handler
        memory_mb: auto
        timeout_s: auto
```

Key concepts:
- **profile**: `minimal` or `scalable` — controls default resource configurations
- **apis.rest.routes**: Defines your API endpoints
- **compute.lambda.services**: Defines your Lambda functions

## Step 4: Validate Your Configuration

Before deploying, validate your configuration:

```bash
factory validate
```

You should see output like:

```
✅ Configuration is valid!

Project: my-first-api
Profile: minimal
Environment: dev

Resources to be created:
  • REST API: my-first-api-dev-api
  • Lambda: hello
  • Routes: GET /hello
```

Add `--show-defaults` to see all resolved values:

```bash
factory validate --show-defaults
```

## Step 5: Deploy to AWS

Deploy your API to the dev environment:

```bash
factory deploy dev
```

This command:
1. Synthesizes CloudFormation templates via CDK
2. Creates all AWS resources (API Gateway, Lambda, IAM roles)
3. Outputs the API endpoint URL

Example output:

```
Deploying my-first-api to dev environment...

 ✅ Deployment complete!

Outputs:
  RestApiUrl: https://abc123xyz.execute-api.us-east-1.amazonaws.com/dev
  HelloFunctionArn: arn:aws:lambda:us-east-1:123456789:function:my-first-api-dev-hello

Deployment time: 2m 34s
```

## Step 6: Test Your API

Use curl or your browser to test the deployed API:

```bash
# Test the hello endpoint
curl https://abc123xyz.execute-api.us-east-1.amazonaws.com/dev/hello
```

Response:

```json
{"message": "Hello, World!"}
```

Try with a query parameter:

```bash
curl "https://abc123xyz.execute-api.us-east-1.amazonaws.com/dev/hello?name=Developer"
```

Response:

```json
{"message": "Hello, Developer!"}
```

## Step 7: View Logs in CloudWatch

Your Lambda function logs are available in CloudWatch. View them in the AWS Console or with the CLI:

```bash
# View recent logs
aws logs tail /aws/lambda/my-first-api-dev-hello --follow
```

## Step 8: Make Changes and Redeploy

Let's add a new endpoint. Edit `factory.yaml`:

```yaml
apis:
  rest:
    routes:
      - path: /hello
        methods: [GET]
        service: hello
        auth: none
      # Add this route
      - path: /orders
        methods: [GET, POST]
        service: orders
        auth: none

compute:
  lambda:
    services:
      hello:
        entry: src/services/hello/handler.py:handler
      # Add this service
      orders:
        entry: src/services/orders/handler.py:handler
```

Validate and redeploy:

```bash
factory validate
factory deploy dev
```

Test the new endpoint:

```bash
# List orders
curl https://abc123xyz.execute-api.us-east-1.amazonaws.com/dev/orders

# Create an order
curl -X POST https://abc123xyz.execute-api.us-east-1.amazonaws.com/dev/orders \
     -H "Content-Type: application/json" \
     -d '{"customer_name": "Jane Doe", "items": [{"name": "Book", "quantity": 1}]}'
```

## Step 9: Clean Up Resources

When you're done, destroy the stack to avoid charges:

```bash
factory destroy dev
```

Confirm the deletion when prompted.

## What's Next?

Congratulations! You've deployed your first API with AWS API Factory. Here are some next steps:

### Add Authentication

Protect your endpoints with API keys:

```yaml
apis:
  rest:
    routes:
      - path: /secure
        methods: [GET]
        service: hello
        auth: api_key
```

See the [Authentication Guide](guides/authentication.md) for more options.

### Switch to Scalable Profile

For production workloads, use the scalable profile:

```yaml
profile: scalable
```

This enables:
- Higher Lambda memory and timeouts
- Reserved concurrency
- Enhanced logging and tracing
- CloudWatch alarms

### Deploy Containers with App Runner

For containerized workloads, enable App Runner:

```yaml
compute:
  apprunner:
    enabled: true
    services:
      api:
        dockerfile: src/services/public_api/Dockerfile
        port: 8000
```

See the [App Runner Guide](guides/app-runner-containers.md) for details.

### Add Data Storage

Enable DynamoDB for persistent storage:

```yaml
data:
  dynamodb:
    enabled: true
    tables:
      - name: orders
        pk: order_id
```

## Troubleshooting

### "CDK not found" Error

Install the CDK CLI:

```bash
npm install -g aws-cdk
```

### "No credentials" Error

Your AWS credentials are not configured. See the [AWS Setup Guide](guides/aws-setup.md) for detailed instructions.

Quick fix:

```bash
# Configure default credentials
aws configure

# Or use a named profile
aws configure --profile api-factory
export AWS_PROFILE=api-factory

# Or pass profile directly to commands
factory deploy dev --profile api-factory
```

### Deployment Timeout

Large deployments may take longer. Check the CloudFormation console for progress.

### Lambda Cold Starts

Initial requests may be slower due to cold starts. For lower latency:
- Use `profile: scalable` for provisioned concurrency
- Optimize Lambda package size
- Use smaller memory sizes for faster initialization

See [Troubleshooting](troubleshooting.md) for more common issues.

## Learn More

- [Configuration Reference](reference/configuration.md) — All factory.yaml options
- [REST API Guide](guides/rest-api.md) — Deep dive into API Gateway
- [Lambda Functions Guide](guides/lambda-functions.md) — Handler patterns and best practices
- [Examples](examples/crud-api.md) — Complete example projects
