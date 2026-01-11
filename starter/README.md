# My API - AWS API Factory Project

This project was created with [AWS API Factory](https://github.com/seanmeehan/aws-api-factory) — a config-driven framework for deploying production-ready APIs on AWS.

## 📁 Project Structure

```
my-api/
├── factory.yaml                 # API configuration (edit this!)
├── infra/                       # CDK infrastructure code
│   ├── app.py                   # CDK entry point
│   └── stacks/                  # Custom stack definitions
├── src/
│   └── services/                # Your Lambda handlers & services
│       ├── hello/               # Hello World example
│       │   └── handler.py
│       ├── orders/              # CRUD example
│       │   └── handler.py
│       └── public_api/          # App Runner example (FastAPI)
│           ├── app.py
│           └── Dockerfile
└── tests/                       # Test suite
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.12+**
- **AWS CLI** configured with credentials
- **AWS CDK CLI** (`npm install -g aws-cdk`)
- **Docker** (for App Runner deployments)

### 1. Validate Configuration

```bash
factory validate
```

This checks your `factory.yaml` for errors and shows what resources will be created.

### 2. Deploy to AWS

```bash
# Deploy to dev environment
factory deploy dev

# Deploy to production
factory deploy prod
```

### 3. Test Your API

After deployment, you'll see the API endpoint URL:

```bash
# Test the hello endpoint
curl https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/dev/hello

# Test with a name parameter
curl "https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/dev/hello?name=Developer"

# Create an order
curl -X POST https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/dev/orders \
     -H "Content-Type: application/json" \
     -d '{"customer_name": "John Doe", "items": [{"name": "Widget", "quantity": 2}]}'
```

### 4. Clean Up

```bash
factory destroy dev
```

## ⚙️ Configuration

Edit `factory.yaml` to customize your API:

### Add a New Route

```yaml
apis:
  rest:
    routes:
      - path: /users
        methods: [GET, POST]
        service: users
        auth: none
```

### Add a New Lambda Service

```yaml
compute:
  lambda:
    services:
      users:
        entry: src/services/users/handler.py:handler
        memory_mb: 512
        timeout_s: 30
```

### Enable Authentication

```yaml
apis:
  rest:
    routes:
      - path: /secure
        methods: [GET]
        service: hello
        auth: api_key  # Options: none, api_key, iam, cognito
```

### Switch to Scalable Profile

```yaml
profile: scalable  # Higher performance defaults
```

## 🔧 Development

### Create a New Service

1. Create a new directory under `src/services/`:
   ```bash
   mkdir -p src/services/users
   ```

2. Create a handler file:
   ```python
   # src/services/users/handler.py
   def handler(event, context):
       return {
           "statusCode": 200,
           "body": '{"message": "Users service"}'
       }
   ```

3. Add the service to `factory.yaml`:
   ```yaml
   compute:
     lambda:
       services:
         users:
           entry: src/services/users/handler.py:handler
   ```

4. Add routes in `factory.yaml`:
   ```yaml
   apis:
     rest:
       routes:
         - path: /users
           methods: [GET]
           service: users
           auth: none
   ```

5. Deploy:
   ```bash
   factory deploy dev
   ```

### Local Testing

Test your Lambda handlers locally:

```python
# test_handler.py
from src.services.hello.handler import handler

event = {
    "httpMethod": "GET",
    "path": "/hello",
    "queryStringParameters": {"name": "Test"}
}
response = handler(event, None)
print(response)
```

### View CloudWatch Logs

After deployment, view logs in the AWS Console or with AWS CLI:

```bash
aws logs tail /aws/lambda/my-api-dev-hello-function --follow
```

## 📖 Documentation

- [Getting Started Guide](https://github.com/seanmeehan/aws-api-factory/blob/main/docs/getting-started.md)
- [Configuration Reference](https://github.com/seanmeehan/aws-api-factory/blob/main/docs/reference/configuration.md)
- [REST API Guide](https://github.com/seanmeehan/aws-api-factory/blob/main/docs/guides/rest-api.md)
- [Lambda Functions Guide](https://github.com/seanmeehan/aws-api-factory/blob/main/docs/guides/lambda-functions.md)
- [Authentication Guide](https://github.com/seanmeehan/aws-api-factory/blob/main/docs/guides/authentication.md)

## 🔐 Security

- Never commit AWS credentials or secrets
- Use `secrets.provider: secrets_manager` for sensitive values
- Enable authentication (`auth: api_key` or `auth: cognito`) for production
- Review IAM permissions in deployed stacks

## 📝 License

This project template is licensed under the MIT License.
