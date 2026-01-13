# Configuration Reference

Complete reference for all `factory.yaml` configuration options.

## Table of Contents

- [Overview](#overview)
- [Project Configuration](#project-configuration)
- [Profile](#profile)
- [APIs Configuration](#apis-configuration)
- [Compute Configuration](#compute-configuration)
- [Data Configuration](#data-configuration)
- [Secrets Configuration](#secrets-configuration)
- [Observability Configuration](#observability-configuration)
- [Full Example](#full-example)

---

## Overview

AWS API Factory uses a single `factory.yaml` file to define your entire API infrastructure. The configuration is validated using Pydantic, providing helpful error messages for invalid values.

### Validation

Validate your configuration anytime with:

```bash
factory validate
factory validate --show-defaults  # Show resolved values
factory validate --show-resources # Preview resources
```

### JSON Schema

Export the JSON Schema for IDE autocomplete:

```bash
factory schema export factory-schema.json
```

---

## Project Configuration

Basic project metadata used for resource naming and tagging.

```yaml
project:
  name: my-api
  envs:
    - dev
    - staging
    - prod
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Project name (lowercase, alphanumeric with hyphens, 1-64 chars) |
| `envs` | list[string] | Yes | List of environment names |

### Naming Rules

- **name**: Must start with a letter, contain only lowercase letters, numbers, and hyphens
- **envs**: Each environment must be alphanumeric (hyphens/underscores allowed), max 32 chars

### Examples

```yaml
# Simple project
project:
  name: orders-api
  envs: [dev, prod]

# Multi-environment
project:
  name: ecommerce-backend
  envs:
    - dev
    - staging
    - prod
```

---

## Profile

Deployment profile controlling default resource configurations.

```yaml
profile: minimal  # or: scalable
```

| Value | Description |
|-------|-------------|
| `minimal` | Lower cost, simpler setup, development-friendly |
| `scalable` | Production-ready with higher resilience and observability |

### Profile Comparison

| Setting | Minimal | Scalable |
|---------|---------|----------|
| Lambda Memory | 512 MB | 1024 MB |
| Lambda Timeout | 30s | 60s |
| Reserved Concurrency | None | 10 |
| API Gateway Throttle | None | 1000 req/s |
| X-Ray Tracing | Off | On |
| CloudWatch Alarms | Off | On |
| DynamoDB PITR | Off | On |
| App Runner Instances | 1-10 | 2-25 |

See [Defaults Reference](defaults.md) for complete comparison.

---

## APIs Configuration

Configure REST and GraphQL APIs.

### REST API

```yaml
apis:
  rest:
    enabled: true
    cors:
      allow_origins: ["*"]
      allow_methods: [GET, POST, PUT, DELETE]
      allow_headers: [Content-Type, Authorization]
    routes:
      - path: /hello
        methods: [GET]
        service: hello
        auth: none
```

#### REST API Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `enabled` | boolean | No | false | Enable REST API |
| `cors` | object | No | null | CORS configuration |
| `routes` | list[Route] | Yes (if enabled) | - | API routes |

#### CORS Configuration

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `allow_origins` | list[string] | No | ["*"] | Allowed origins |
| `allow_methods` | list[string] | No | All methods | Allowed HTTP methods |
| `allow_headers` | list[string] | No | Common headers | Allowed headers |

#### Route Configuration

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `path` | string | Yes | - | URL path (must start with /) |
| `methods` | list[string] | Yes | - | HTTP methods (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS) |
| `service` | string | Yes | - | Name of compute service handling this route |
| `auth` | string | No | none | Authentication mode |

#### Authentication Modes

| Value | Description |
|-------|-------------|
| `none` | No authentication required |
| `api_key` | Require API key in x-api-key header |
| `iam` | AWS IAM authentication (SigV4) |
| `cognito` | Cognito User Pool JWT token |

### Path Parameters

Use `{param}` syntax for path parameters:

```yaml
routes:
  - path: /users/{id}
    methods: [GET, PUT, DELETE]
    service: users
    auth: none

  - path: /users/{userId}/orders/{orderId}
    methods: [GET]
    service: orders
    auth: none
```

### GraphQL API

```yaml
apis:
  graphql:
    enabled: true
    schema_path: src/graphql/schema.graphql
    auth: cognito
    resolvers:
      - type: Query
        field: getOrder
        service: orders
        resolver: get_order
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `enabled` | boolean | No | false | Enable GraphQL API |
| `schema_path` | string | Yes (if enabled) | - | Path to GraphQL schema file |
| `auth` | string | No | api_key | Default auth mode |
| `resolvers` | list[Resolver] | Yes (if enabled) | - | Resolver mappings |

---

## Compute Configuration

Configure Lambda functions and App Runner services.

### Lambda Configuration

```yaml
compute:
  lambda:
    enabled: true
    services:
      hello:
        entry: src/services/hello/handler.py:handler
        memory_mb: 512
        timeout_s: 30
        environment:
          LOG_LEVEL: INFO
        reserved_concurrency: 10
```

#### Lambda Service Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `entry` | string | Yes | - | Handler path (file.py:function) |
| `memory_mb` | int\|"auto" | No | auto | Memory in MB (128-10240) |
| `timeout_s` | int\|"auto" | No | auto | Timeout in seconds (1-900) |
| `environment` | dict | No | {} | Environment variables |
| `reserved_concurrency` | int | No | null | Reserved concurrent executions |
| `runtime` | string | No | python3.12 | Lambda runtime |

#### Entry Point Format

The entry point must be in the format `path/to/file.py:handler_function`:

```yaml
services:
  # Handler at src/services/hello/handler.py with function named "handler"
  hello:
    entry: src/services/hello/handler.py:handler

  # Handler at src/orders/main.py with function named "process_request"
  orders:
    entry: src/orders/main.py:process_request
```

#### Memory and Timeout

Use `auto` to inherit profile defaults, or specify explicit values:

```yaml
services:
  # Use profile defaults
  simple:
    entry: src/simple/handler.py:handler
    memory_mb: auto
    timeout_s: auto

  # Explicit values
  heavy:
    entry: src/heavy/handler.py:handler
    memory_mb: 2048
    timeout_s: 120
```

### App Runner Configuration

```yaml
compute:
  apprunner:
    enabled: true
    services:
      api:
        dockerfile: src/services/api/Dockerfile
        port: 8000
        healthcheck_path: /healthz
        cpu: 1
        memory: 2
        min_instances: 1
        max_instances: 10
        environment:
          ENVIRONMENT: production
```

#### App Runner Service Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `dockerfile` | string | Yes | - | Path to Dockerfile |
| `port` | int | Yes | - | Container port |
| `healthcheck_path` | string | No | /healthz | Health check endpoint |
| `cpu` | float | No | 1 | vCPU (0.25, 0.5, 1, 2, 4) |
| `memory` | float | No | 2 | Memory in GB (0.5, 1, 2, 3, 4, 6, 8, 10, 12) |
| `min_instances` | int | No | 1 | Minimum instances |
| `max_instances` | int | No | 10 | Maximum instances |
| `environment` | dict | No | {} | Environment variables |

---

## Data Configuration

Configure data stores.

### DynamoDB

```yaml
data:
  dynamodb:
    enabled: true
    tables:
      - name: orders
        pk: order_id
        sk: created_at
        billing_mode: PAY_PER_REQUEST
        pitr: true
```

#### Table Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | Yes | - | Table name |
| `pk` | string | Yes | - | Partition key attribute |
| `sk` | string | No | null | Sort key attribute |
| `billing_mode` | string | No | PAY_PER_REQUEST | PROVISIONED or PAY_PER_REQUEST |
| `pitr` | boolean | No | profile-dependent | Point-in-time recovery |

### S3

```yaml
data:
  s3:
    enabled: true
    buckets:
      - name: uploads
        versioning: true
        cors: true
```

#### Bucket Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | Yes | - | Bucket name suffix |
| `versioning` | boolean | No | false | Enable versioning |
| `cors` | boolean | No | false | Enable CORS |

### Aurora Serverless v2

```yaml
data:
  aurora:
    enabled: true
    engine: postgres
    mode: serverless_v2
    min_acu: 0.5
    max_acu: 8
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `enabled` | boolean | No | false | Enable Aurora |
| `engine` | string | No | postgres | postgres or mysql |
| `mode` | string | No | serverless_v2 | serverless_v2 or provisioned |
| `min_acu` | float | No | 0.5 | Minimum ACUs |
| `max_acu` | float | No | 8 | Maximum ACUs |

---

## Secrets Configuration

Configure secrets management.

```yaml
secrets:
  provider: secrets_manager
  cognito:
    user_pool_id: us-east-1_XXXXXXXXX
    app_client_id: xxxxxxxxxxxxxxxxxxxxxxxxxx
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `provider` | string | No | ssm | ssm or secrets_manager |
| `cognito` | object | No | null | Cognito configuration (for auth: cognito) |

### Cognito Configuration

Required when using `auth: cognito`:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_pool_id` | string | Yes | Cognito User Pool ID |
| `app_client_id` | string | Yes | Cognito App Client ID |

---

## Observability Configuration

Configure logging, metrics, and tracing.

```yaml
observability:
  level: enhanced
  log_retention_days: 30
  tracing: true
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `level` | string | No | basic | basic or enhanced |
| `log_retention_days` | int | No | 14 | CloudWatch log retention |
| `tracing` | boolean | No | profile-dependent | Enable X-Ray tracing |

### Observability Levels

| Level | Features |
|-------|----------|
| `basic` | CloudWatch logs, standard metrics |
| `enhanced` | Structured logging, X-Ray tracing, alarms, dashboards |

---

## Full Example

Complete `factory.yaml` demonstrating all options:

```yaml
project:
  name: ecommerce-api
  envs:
    - dev
    - staging
    - prod

profile: scalable

apis:
  rest:
    enabled: true
    cors:
      allow_origins:
        - "https://app.example.com"
      allow_methods:
        - GET
        - POST
        - PUT
        - DELETE
      allow_headers:
        - Content-Type
        - Authorization
    routes:
      - path: /health
        methods: [GET]
        service: health
        auth: none
      - path: /orders
        methods: [GET, POST]
        service: orders
        auth: cognito
      - path: /orders/{id}
        methods: [GET, PUT, DELETE]
        service: orders
        auth: cognito
      - path: /admin/stats
        methods: [GET]
        service: admin
        auth: iam

compute:
  lambda:
    enabled: true
    services:
      health:
        entry: src/services/health/handler.py:handler
        memory_mb: 256
        timeout_s: 10
      orders:
        entry: src/services/orders/handler.py:handler
        memory_mb: 1024
        timeout_s: 60
        environment:
          TABLE_NAME: orders
        reserved_concurrency: 50
      admin:
        entry: src/services/admin/handler.py:handler
        memory_mb: 512
        timeout_s: 30

data:
  dynamodb:
    enabled: true
    tables:
      - name: orders
        pk: order_id
        sk: created_at
        pitr: true
      - name: customers
        pk: customer_id
        pitr: true
  s3:
    enabled: true
    buckets:
      - name: uploads
        versioning: true
        cors: true

secrets:
  provider: secrets_manager
  cognito:
    user_pool_id: us-east-1_ABC123XYZ
    app_client_id: 1234567890abcdef

observability:
  level: enhanced
  log_retention_days: 90
  tracing: true
```
