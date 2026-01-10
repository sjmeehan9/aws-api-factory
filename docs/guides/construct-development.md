# Construct Development Guide

This guide explains how to develop custom constructs for AWS API Factory. Whether you're extending the factory with new AWS services or creating organization-specific patterns, this guide covers everything you need to know.

## Overview

AWS API Factory uses a modular construct system where each feature (REST API, Lambda, Auth, etc.) is implemented as a separate construct that plugs into the main `FactoryStack`. This architecture enables:

- **Modularity**: Add or remove features without modifying core code
- **Testability**: Test constructs in isolation
- **Extensibility**: Create custom constructs for your organization
- **Consistency**: All constructs follow the same patterns

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                     FactoryStack                     │
│  ┌─────────────────────────────────────────────────┐│
│  │              ConstructRegistry                   ││
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐           ││
│  │  │RestApi  │ │Lambda   │ │Auth     │ ...       ││
│  │  │Construct│ │Construct│ │Construct│           ││
│  │  └─────────┘ └─────────┘ └─────────┘           ││
│  └─────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────┐│
│  │              OutputManager                       ││
│  │  Collects outputs from all constructs           ││
│  └─────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────┘
```

## Core Components

### BaseConstruct

All factory constructs extend `BaseConstruct`, which provides:

- Configuration validation before resource creation
- Consistent resource naming (`generate_resource_name()`)
- Output registration (`add_output()`)
- Tagging (`apply_tags()`)
- IAM role creation helpers (`create_service_role()`)

### ConstructRegistry

The registry manages dynamic construct loading:

- Register constructs with their enabling conditions
- Priority ordering for dependency resolution
- Lazy instantiation based on configuration

### OutputManager

Collects and exports stack outputs:

- Organized by category (api, compute, data, auth)
- CloudFormation CfnOutput generation
- JSON export for CLI consumption

## Creating a Custom Construct

### Step 1: Extend BaseConstruct

```python
from aws_api_factory.constructs.base import BaseConstruct
from aws_api_factory.config.models import FactoryConfig

class MyCustomConstruct(BaseConstruct):
    """My custom AWS construct.

    This construct creates [describe what it creates].
    """

    def validate_config(self) -> list[str]:
        """Validate configuration before resource creation.

        Returns:
            List of validation error messages. Empty if valid.
        """
        errors = []

        # Example validation
        if not self.config.compute.lambda_.enabled:
            errors.append("Lambda compute must be enabled for this construct")

        return errors

    def _create_resources(self) -> None:
        """Create AWS CDK resources."""
        # Use generate_resource_name for consistent naming
        bucket_name = self.generate_resource_name("bucket", "data")

        # Create resources
        from aws_cdk import aws_s3 as s3
        self.bucket = s3.Bucket(
            self,
            "DataBucket",
            bucket_name=bucket_name,
        )

        # Apply tags
        self.apply_tags(self.bucket, Purpose="data-storage")

        # Register outputs
        self.add_output(
            key="DataBucketArn",
            value=self.bucket.bucket_arn,
            description="Data bucket ARN",
            category="data",
        )
```

### Step 2: Register the Construct

Register your construct with the factory registry:

```python
from aws_api_factory.constructs import register_construct
from my_constructs import MyCustomConstruct

# Register with the default registry
register_construct(
    MyCustomConstruct,
    config_section="custom.data_bucket",
    enabled_check=lambda config: config.data.s3.enabled,
    priority=80,  # Lower = created first
)
```

### Step 3: Write Tests

Create comprehensive tests for your construct:

```python
import pytest
from aws_cdk import App, Stack
from aws_cdk import assertions

from aws_api_factory.config.models import FactoryConfig
from aws_api_factory.config.defaults import get_defaults, ProfileEnum
from aws_api_factory.constructs.outputs import OutputManager
from my_constructs import MyCustomConstruct


@pytest.fixture
def app() -> App:
    return App()


@pytest.fixture
def config() -> FactoryConfig:
    return FactoryConfig.model_validate({
        "project": {"name": "test", "envs": ["dev"]},
        "profile": "minimal",
        # ... rest of config
    })


class TestMyCustomConstruct:
    def test_creates_bucket(self, app, config):
        stack = Stack(app, "TestStack")
        output_manager = OutputManager(stack, "test", "dev")

        construct = MyCustomConstruct(
            stack, "Custom",
            config=config,
            profile_defaults=get_defaults(ProfileEnum.MINIMAL),
            output_manager=output_manager,
            environment="dev",
        )

        template = assertions.Template.from_stack(stack)
        template.has_resource("AWS::S3::Bucket", {
            "Properties": {
                "BucketName": "test-dev-bucket-data",
            }
        })

    def test_registers_output(self, app, config):
        stack = Stack(app, "TestStack")
        output_manager = OutputManager(stack, "test", "dev")

        MyCustomConstruct(
            stack, "Custom",
            config=config,
            profile_defaults=get_defaults(ProfileEnum.MINIMAL),
            output_manager=output_manager,
            environment="dev",
        )

        assert "DataBucketArn" in output_manager
```

## Naming Conventions

### Resource Names

Use `generate_resource_name()` for consistent naming:

```python
# Format: {project}-{env}-{resource_type}-{logical_name}
name = self.generate_resource_name("lambda", "orders")
# Result: "my-api-dev-lambda-orders"

# Without environment (for global resources)
name = self.generate_resource_name("bucket", "assets", include_env=False)
# Result: "my-api-bucket-assets"
```

### Construct IDs

Use `sanitize_resource_id()` for path-based IDs:

```python
from aws_api_factory.constructs.base import sanitize_resource_id

construct_id = sanitize_resource_id("/orders/{orderId}/items")
# Result: "OrdersOrderidItems"
```

## Output Categories

Register outputs with appropriate categories:

| Category | Use For |
|----------|---------|
| `api` | API endpoints, URLs |
| `compute` | Lambda ARNs, App Runner URLs |
| `data` | DynamoDB table names, S3 bucket ARNs |
| `auth` | Cognito User Pool IDs, API Key ARNs |
| `metadata` | Stack info, project metadata |
| `custom` | User-defined outputs |

## Profile-Aware Development

Access profile defaults in your construct:

```python
def _create_resources(self) -> None:
    # Check profile
    if self.config.profile.value == "scalable":
        # Enhanced configuration for production
        retention = logs.RetentionDays.ONE_MONTH
    else:
        # Cost-effective for development
        retention = logs.RetentionDays.ONE_WEEK

    # Or use profile defaults directly
    memory = self.profile_defaults.lambda_.memory_mb
    timeout = self.profile_defaults.lambda_.timeout_s
```

## Escape Hatches

### Extra CDK Props

Allow users to pass additional CDK properties:

```python
def _create_resources(self) -> None:
    # Get extra props from config (if supported)
    extra_props = getattr(self.config, 'extra_lambda_props', {})

    self.function = lambda_.Function(
        self, "Function",
        runtime=lambda_.Runtime.PYTHON_3_11,
        handler="handler.handler",
        code=lambda_.Code.from_asset("src"),
        **extra_props,  # User overrides
    )
```

### Custom IAM Statements

Support custom IAM policies:

```python
def _create_resources(self) -> None:
    role = self.create_service_role(
        "ExecutionRole",
        assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        description="Lambda execution role",
    )

    # Add custom statements from config
    if hasattr(self.config, 'custom_iam_statements'):
        for statement in self.config.custom_iam_statements:
            role.add_to_policy(iam.PolicyStatement.from_json(statement))
```

### Importing Existing Resources

Support importing existing AWS resources:

```python
def _create_resources(self) -> None:
    # Check if user wants to import existing VPC
    vpc_id = getattr(self.config, 'existing_vpc_id', None)

    if vpc_id:
        self.vpc = ec2.Vpc.from_lookup(self, "Vpc", vpc_id=vpc_id)
    else:
        self.vpc = ec2.Vpc(self, "Vpc", max_azs=2)
```

## Best Practices

### 1. Fail Fast

Validate configuration early:

```python
def validate_config(self) -> list[str]:
    errors = []

    # Check required config
    if not self.config.apis.rest.enabled:
        errors.append("REST API must be enabled")

    # Check service references
    for route in self.config.apis.rest.routes:
        if route.service not in self.config.compute.lambda_.services:
            errors.append(f"Service '{route.service}' not found")

    return errors
```

### 2. Least Privilege IAM

Always use minimal IAM permissions:

```python
# Good: Specific actions on specific resources
role.add_to_policy(iam.PolicyStatement(
    effect=iam.Effect.ALLOW,
    actions=["dynamodb:GetItem", "dynamodb:PutItem"],
    resources=[table.table_arn],
))

# Bad: Overly permissive
role.add_to_policy(iam.PolicyStatement(
    effect=iam.Effect.ALLOW,
    actions=["dynamodb:*"],
    resources=["*"],
))
```

### 3. Consistent Tagging

Always tag resources:

```python
def _create_resources(self) -> None:
    bucket = s3.Bucket(self, "Bucket")

    # Apply standard + custom tags
    self.apply_tags(
        bucket,
        Service="data-storage",
        CostCenter="engineering",
    )
```

### 4. Register Meaningful Outputs

Register outputs that users need:

```python
def _create_resources(self) -> None:
    # Good: Useful information
    self.add_output(
        key="ApiEndpoint",
        value=api.url,
        description="REST API endpoint URL",
        category="api",
        export=True,  # Enable cross-stack references
    )

    # Avoid: Internal details that users don't need
```

### 5. Handle Dependencies

Use priority ordering for dependencies:

```python
# Auth constructs should be created before API constructs
register_construct(CognitoConstruct, "auth.cognito", priority=20)
register_construct(RestApiConstruct, "apis.rest", priority=50)
```

## Common Patterns

### Lambda with DynamoDB

```python
class LambdaDynamoConstruct(BaseConstruct):
    def _create_resources(self) -> None:
        # Create table
        self.table = dynamodb.Table(
            self, "Table",
            partition_key=dynamodb.Attribute(
                name="pk",
                type=dynamodb.AttributeType.STRING,
            ),
        )

        # Create Lambda
        self.function = lambda_.Function(
            self, "Function",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.handler",
            code=lambda_.Code.from_asset("src"),
            environment={
                "TABLE_NAME": self.table.table_name,
            },
        )

        # Grant permissions
        self.table.grant_read_write_data(self.function)
```

### API Gateway with Authorizer

```python
class AuthorizedApiConstruct(BaseConstruct):
    def _create_resources(self) -> None:
        # Create authorizer (from another construct)
        authorizer = self._create_cognito_authorizer()

        # Create API with authorizer on methods
        api = apigateway.RestApi(self, "Api")

        orders = api.root.add_resource("orders")
        orders.add_method(
            "GET",
            apigateway.LambdaIntegration(self.list_function),
            authorizer=authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )
```

## Troubleshooting

### Construct Not Being Created

1. Check that the enabled_check returns True
2. Verify the config section matches your registration
3. Check the priority order for dependencies

### CloudFormation Errors

1. Use CDK assertions in tests to validate templates
2. Check resource naming doesn't exceed AWS limits
3. Verify IAM permissions are valid

### Output Missing

1. Ensure `add_output()` is called in `_create_resources()`
2. Check the output key is unique
3. Verify `export_to_cfn()` is called (happens automatically in FactoryStack)

## Further Reading

- [AWS CDK Python Reference](https://docs.aws.amazon.com/cdk/api/v2/python/)
- [AWS CDK Best Practices](https://docs.aws.amazon.com/cdk/v2/guide/best-practices.html)
- [CDK Patterns](https://cdkpatterns.com/)
