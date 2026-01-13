# Authentication Guide

Secure your APIs with API Keys, IAM, or Cognito authentication.

## Overview

AWS API Factory supports four authentication modes:

| Mode | Use Case | Complexity |
|------|----------|------------|
| `none` | Public endpoints | None |
| `api_key` | Third-party integrations, simple auth | Low |
| `iam` | AWS service-to-service, internal APIs | Medium |
| `cognito` | User authentication, mobile/web apps | High |

## Choosing an Auth Mode

```
┌─────────────────────────────────────────────────────────────┐
│                   Do you need authentication?               │
└─────────────────────────────────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
            No                          Yes
              │                           │
              ▼                           ▼
         auth: none            Who is the consumer?
                                          │
              ┌───────────────┬───────────┴───────────┐
              ▼               ▼                       ▼
         Third-party     AWS services            End users
         systems         or internal              (humans)
              │               │                       │
              ▼               ▼                       ▼
         auth: api_key   auth: iam            auth: cognito
```

## API Key Authentication

Simple key-based authentication using API Gateway usage plans.

### Configuration

```yaml
apis:
  rest:
    routes:
      - path: /webhook
        methods: [POST]
        service: webhook
        auth: api_key
```

### How It Works

1. API Gateway creates a usage plan with an API key
2. Clients include the key in the `x-api-key` header
3. Invalid or missing keys receive 403 Forbidden

### Client Usage

```bash
# Get your API key from the deployment outputs
API_KEY="your-api-key-here"  # pragma: allowlist secret

# Include in requests
curl -X POST https://api.example.com/webhook \
     -H "x-api-key: $API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"event": "order.created"}'
```

### Python Client

```python
import requests

API_KEY = "your-api-key-here"
API_URL = "https://api.example.com"

headers = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json"
}

response = requests.post(
    f"{API_URL}/webhook",
    headers=headers,
    json={"event": "order.created"}
)
```

### In Lambda Handler

```python
def handler(event, context):
    # API key is validated by API Gateway before reaching Lambda
    # Access key ID from request context (if needed)
    api_key_id = event.get("requestContext", {}).get("identity", {}).get("apiKeyId")

    # Your business logic
    return {"statusCode": 200, "body": "OK"}
```

### Managing API Keys

After deployment, manage keys via AWS Console or CLI:

```bash
# List API keys
aws apigateway get-api-keys

# Create a new API key
aws apigateway create-api-key \
    --name "partner-xyz" \
    --enabled

# Get key value
aws apigateway get-api-key \
    --api-key <key-id> \
    --include-value
```

### Best Practices

- **Rotate keys regularly** — Create new keys, migrate clients, delete old keys
- **Use descriptive names** — `partner-acme-prod`, `internal-service-orders`
- **Set usage limits** — Configure throttling per key
- **Never commit keys** — Use environment variables or secrets manager

## IAM Authentication

AWS SigV4 signing for service-to-service communication.

### Configuration

```yaml
apis:
  rest:
    routes:
      - path: /internal/sync
        methods: [POST]
        service: sync
        auth: iam
```

### How It Works

1. Caller signs request with AWS credentials (SigV4)
2. API Gateway verifies signature
3. IAM policy determines authorization
4. Invalid signatures receive 403 Forbidden

### Client Usage (AWS CLI)

```bash
# AWS CLI automatically signs requests
aws apigateway test-invoke-method \
    --rest-api-id abc123 \
    --resource-id xyz789 \
    --http-method POST \
    --body '{"action": "sync"}'
```

### Python Client (boto3)

```python
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import requests

def make_signed_request(url, method="GET", data=None):
    """Make a SigV4-signed request to API Gateway."""
    session = boto3.Session()
    credentials = session.get_credentials()
    region = session.region_name

    # Create request
    request = AWSRequest(method=method, url=url, data=data)

    # Sign request
    SigV4Auth(credentials, "execute-api", region).add_auth(request)

    # Make request with signed headers
    response = requests.request(
        method=method,
        url=url,
        headers=dict(request.headers),
        data=data
    )

    return response

# Usage
response = make_signed_request(
    "https://abc123.execute-api.us-east-1.amazonaws.com/dev/internal/sync",
    method="POST",
    data='{"action": "sync"}'
)
```

### Using requests-aws4auth

```bash
pip install requests-aws4auth
```

```python
import boto3
import requests
from requests_aws4auth import AWS4Auth

session = boto3.Session()
credentials = session.get_credentials()
auth = AWS4Auth(
    credentials.access_key,
    credentials.secret_key,
    session.region_name,
    "execute-api",
    session_token=credentials.token
)

response = requests.post(
    "https://abc123.execute-api.us-east-1.amazonaws.com/dev/internal/sync",
    auth=auth,
    json={"action": "sync"}
)
```

### In Lambda Handler

```python
def handler(event, context):
    # Access IAM identity from request context
    identity = event.get("requestContext", {}).get("identity", {})

    caller_arn = identity.get("userArn")
    account_id = identity.get("accountId")

    # Log who made the request
    print(f"Request from: {caller_arn}")

    return {"statusCode": 200, "body": "OK"}
```

### IAM Policy for Callers

Grant permission to invoke the API:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "execute-api:Invoke",
            "Resource": "arn:aws:execute-api:us-east-1:123456789:abc123/*/POST/internal/sync"
        }
    ]
}
```

### Best Practices

- **Use least-privilege policies** — Restrict to specific methods/paths
- **Use roles, not users** — For service-to-service calls
- **Enable CloudTrail** — Audit API access
- **Consider resource policies** — Restrict to specific accounts/VPCs

## Cognito Authentication

JWT-based authentication for user-facing applications.

### Prerequisites

1. Create a Cognito User Pool (via AWS Console or CDK)
2. Create an App Client
3. Note the User Pool ID and App Client ID

### Configuration

```yaml
apis:
  rest:
    routes:
      - path: /users/me
        methods: [GET]
        service: users
        auth: cognito

secrets:
  provider: ssm
  cognito:
    user_pool_id: us-east-1_ABC123XYZ
    app_client_id: 1234567890abcdef
```

### How It Works

1. User authenticates with Cognito (login flow)
2. Cognito returns JWT tokens (ID token, access token)
3. Client includes token in `Authorization` header
4. API Gateway validates token with Cognito
5. Invalid tokens receive 401 Unauthorized

### Client Usage

```bash
# Get token (example using Cognito Hosted UI callback)
TOKEN="eyJraWQiOiJ..."

# Include in requests
curl https://api.example.com/users/me \
     -H "Authorization: Bearer $TOKEN"
```

### JavaScript Client

```javascript
// Using Amazon Cognito Identity SDK
import { CognitoUserPool, CognitoUser, AuthenticationDetails } from 'amazon-cognito-identity-js';

const poolData = {
    UserPoolId: 'us-east-1_ABC123XYZ',  // pragma: allowlist secret
    ClientId: '1234567890abcdef'
};
const userPool = new CognitoUserPool(poolData);

// Authenticate
const authDetails = new AuthenticationDetails({
    Username: 'user@example.com',
    Password: 'password123'  // pragma: allowlist secret
});

const cognitoUser = new CognitoUser({
    Username: 'user@example.com',
    Pool: userPool
});

cognitoUser.authenticateUser(authDetails, {
    onSuccess: (result) => {
        const idToken = result.getIdToken().getJwtToken();

        // Use token in API calls
        fetch('https://api.example.com/users/me', {
            headers: {
                'Authorization': `Bearer ${idToken}`
            }
        });
    },
    onFailure: (err) => {
        console.error(err);
    }
});
```

### Python Client

```python
import boto3

# Authenticate with Cognito
client = boto3.client("cognito-idp", region_name="us-east-1")

response = client.initiate_auth(
    ClientId="1234567890abcdef",
    AuthFlow="USER_PASSWORD_AUTH",
    AuthParameters={
        "USERNAME": "user@example.com",
        "PASSWORD": "password123"
    }
)

id_token = response["AuthenticationResult"]["IdToken"]
access_token = response["AuthenticationResult"]["AccessToken"]

# Use token in API calls
import requests

response = requests.get(
    "https://api.example.com/users/me",
    headers={"Authorization": f"Bearer {id_token}"}
)
```

### In Lambda Handler

```python
def handler(event, context):
    # Access user claims from request context
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})

    # Common claims
    user_id = claims.get("sub")  # Cognito user ID (UUID)
    email = claims.get("email")
    username = claims.get("cognito:username")
    groups = claims.get("cognito:groups", "").split(",")

    # Custom claims (if configured)
    tenant_id = claims.get("custom:tenant_id")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "user_id": user_id,
            "email": email,
            "groups": groups
        })
    }
```

### Role-Based Access Control

Check user groups for authorization:

```python
def handler(event, context):
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    groups = claims.get("cognito:groups", "").split(",") if claims.get("cognito:groups") else []

    # Check for admin group
    if "admin" not in groups:
        return {
            "statusCode": 403,
            "body": '{"error": "Admin access required"}'
        }

    # Admin-only logic
    return {"statusCode": 200, "body": '{"admin": true}'}
```

### Best Practices

- **Use HTTPS everywhere** — Tokens are sensitive
- **Set short token expiration** — 1 hour for ID tokens
- **Implement token refresh** — Use refresh tokens for long sessions
- **Validate on backend** — Don't trust client-only validation
- **Use groups for RBAC** — Easier than custom claims
- **Enable MFA** — For sensitive operations

## Mixed Authentication

Different routes can use different auth modes:

```yaml
apis:
  rest:
    routes:
      # Public health check
      - path: /health
        methods: [GET]
        service: health
        auth: none

      # Webhook from third-party
      - path: /webhooks/stripe
        methods: [POST]
        service: webhooks
        auth: api_key

      # User-facing endpoints
      - path: /users/me
        methods: [GET, PUT]
        service: users
        auth: cognito

      # Internal service calls
      - path: /internal/sync
        methods: [POST]
        service: sync
        auth: iam
```

## Testing Authentication

### Testing API Key

```bash
# Without key (should fail)
curl https://api.example.com/webhook
# 403 Forbidden

# With key (should succeed)
curl https://api.example.com/webhook \
     -H "x-api-key: your-api-key"
# 200 OK
```

### Testing IAM Auth

```bash
# Using AWS CLI (auto-signs)
aws apigateway test-invoke-method \
    --rest-api-id abc123 \
    --resource-id xyz789 \
    --http-method GET
```

### Testing Cognito

```python
# test_cognito_auth.py
import requests

def test_unauthenticated_access():
    response = requests.get("https://api.example.com/users/me")
    assert response.status_code == 401

def test_authenticated_access():
    token = get_cognito_token()  # Your helper function
    response = requests.get(
        "https://api.example.com/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert "email" in response.json()
```

## Troubleshooting

### "Missing Authentication Token"

**Cause**: Request missing required auth header

**Solution**: Add appropriate header
- API Key: `x-api-key: your-key`
- Cognito: `Authorization: Bearer your-token`
- IAM: Use SigV4 signing

### "Invalid API Key"

**Cause**: Key doesn't exist or isn't associated with usage plan

**Solution**:
1. Verify key exists: `aws apigateway get-api-keys`
2. Check key is associated with correct usage plan
3. Ensure key is enabled

### "Token Expired"

**Cause**: Cognito token has expired (default: 1 hour)

**Solution**:
1. Refresh token using refresh token
2. Re-authenticate user
3. Consider longer token expiration (not recommended)

### "Signature Does Not Match"

**Cause**: SigV4 signature calculation error

**Solution**:
1. Verify region is correct
2. Check credentials are valid
3. Ensure request hasn't been modified after signing
4. Check clock skew (must be within 5 minutes)

## Security Checklist

- [ ] No routes with `auth: none` expose sensitive data
- [ ] API keys are not committed to version control
- [ ] Cognito tokens are transmitted over HTTPS only
- [ ] IAM policies follow least-privilege principle
- [ ] CloudWatch/CloudTrail logging enabled
- [ ] Token expiration is appropriately short
- [ ] Failed auth attempts are logged and monitored
- [ ] Rate limiting is configured for public endpoints

## Next Steps

- [REST API Guide](rest-api.md) — API Gateway configuration
- [Lambda Functions Guide](lambda-functions.md) — Handler patterns
- [Configuration Reference](../reference/configuration.md) — All auth options
