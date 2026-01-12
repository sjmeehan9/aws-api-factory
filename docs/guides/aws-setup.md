# AWS Account Setup Guide

This guide walks you through setting up AWS credentials for AWS API Factory, including creating a dedicated IAM user, configuring a named profile, and bootstrapping CDK.

## Overview

AWS API Factory uses the AWS CDK to deploy resources to your AWS account. Before deploying, you need:

1. **AWS Account** — An active AWS account
2. **IAM User or Role** — Credentials with permissions to create resources
3. **AWS CLI** — Configured with your credentials
4. **CDK Bootstrap** — One-time setup per account/region

## Option 1: Quick Setup (Default Profile)

If you're new to AWS or want a simple setup:

```bash
# Install AWS CLI (if not installed)
# macOS
brew install awscli

# Or download from: https://aws.amazon.com/cli/

# Configure with your credentials
aws configure
```

When prompted, enter:
- **AWS Access Key ID**: Your access key
- **AWS Secret Access Key**: Your secret key
- **Default region**: e.g., `us-east-1`
- **Default output format**: `json`

Verify it works:

```bash
aws sts get-caller-identity
```

You should see your account ID and user ARN.

## Option 2: Named Profile (Recommended)

Using a named profile keeps your API Factory credentials separate from other AWS work. This is especially useful if you work with multiple AWS accounts.

### Step 1: Create an IAM User

1. Log into the [AWS Console](https://console.aws.amazon.com/)
2. Go to **IAM** → **Users** → **Create user**
3. Enter a username: `api-factory-deployer`
4. Select **Attach policies directly**
5. Attach the **AdministratorAccess** policy (or see [Minimal Permissions](#minimal-permissions) below)
6. Click **Create user**
7. Go to the user → **Security credentials** → **Create access key**
8. Choose **Command Line Interface (CLI)**
9. Save the **Access Key ID** and **Secret Access Key**

### Step 2: Configure a Named Profile

```bash
# Create a named profile called 'api-factory'
aws configure --profile api-factory
```

Enter the credentials from Step 1:
- **AWS Access Key ID**: `AKIA...` (from IAM)
- **AWS Secret Access Key**: `wJal...` (from IAM)
- **Default region**: `us-east-1` (or your preferred region)
- **Default output format**: `json`

### Step 3: Verify the Profile

```bash
aws sts get-caller-identity --profile api-factory
```

### Step 4: Use the Profile

There are three ways to use your named profile:

#### Option A: Set Environment Variable (Session)

```bash
# Set for current terminal session
export AWS_PROFILE=api-factory

# Now all commands use this profile
factory deploy dev
```

#### Option B: Set in Shell Config (Persistent)

Add to your `~/.zshrc` or `~/.bashrc`:

```bash
# Default AWS profile for API Factory projects
export AWS_PROFILE=api-factory
```

Then reload: `source ~/.zshrc`

#### Option C: Pass to Commands (Explicit)

```bash
# Use --profile flag with factory commands
factory deploy dev --profile api-factory
factory destroy dev --profile api-factory
factory synth --profile api-factory
```

## CDK Bootstrap

AWS CDK requires a one-time bootstrap in each account/region where you'll deploy:

```bash
# With default profile
cdk bootstrap aws://ACCOUNT_ID/REGION

# With named profile
cdk bootstrap aws://ACCOUNT_ID/REGION --profile api-factory

# Example
cdk bootstrap aws://123456789012/us-east-1 --profile api-factory
```

You can find your account ID with:

```bash
aws sts get-caller-identity --query Account --output text
```

## Minimal Permissions

For production environments, use least-privilege permissions instead of AdministratorAccess. Create a custom IAM policy with these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CDKBootstrap",
      "Effect": "Allow",
      "Action": [
        "cloudformation:*",
        "s3:*",
        "iam:*",
        "ssm:GetParameter",
        "ssm:PutParameter"
      ],
      "Resource": "*"
    },
    {
      "Sid": "APIFactory",
      "Effect": "Allow",
      "Action": [
        "apigateway:*",
        "lambda:*",
        "logs:*",
        "iam:CreateRole",
        "iam:DeleteRole",
        "iam:AttachRolePolicy",
        "iam:DetachRolePolicy",
        "iam:PutRolePolicy",
        "iam:DeleteRolePolicy",
        "iam:GetRole",
        "iam:PassRole",
        "iam:CreateServiceLinkedRole",
        "cognito-idp:*",
        "apprunner:*",
        "ecr:*",
        "dynamodb:*",
        "secretsmanager:*",
        "ssm:*"
      ],
      "Resource": "*"
    }
  ]
}
```

> **Note**: This policy is broader than strictly necessary. For maximum security, scope resources to specific ARN patterns matching your project naming convention.

## Multiple Environments

For separate dev/staging/prod accounts, create profiles for each:

```bash
# Configure each profile
aws configure --profile api-factory-dev
aws configure --profile api-factory-staging
aws configure --profile api-factory-prod

# Bootstrap each account
cdk bootstrap aws://111111111111/us-east-1 --profile api-factory-dev
cdk bootstrap aws://222222222222/us-east-1 --profile api-factory-staging
cdk bootstrap aws://333333333333/us-east-1 --profile api-factory-prod

# Deploy to specific account
factory deploy dev --profile api-factory-dev
factory deploy staging --profile api-factory-staging
factory deploy prod --profile api-factory-prod
```

## Using AWS SSO (Identity Center)

If your organization uses AWS SSO:

```bash
# Configure SSO profile
aws configure sso --profile api-factory

# Login when session expires
aws sso login --profile api-factory

# Use with factory commands
export AWS_PROFILE=api-factory
factory deploy dev
```

## Troubleshooting

### "Unable to locate credentials"

Your credentials aren't configured or the profile doesn't exist:

```bash
# Check current identity
aws sts get-caller-identity

# List configured profiles
aws configure list-profiles

# Verify specific profile
aws configure list --profile api-factory
```

### "ExpiredToken" Error

Your session token has expired (common with SSO or assumed roles):

```bash
# For SSO
aws sso login --profile api-factory

# For MFA/assumed roles
# Re-run your assume-role command
```

### "Access Denied" Error

Your IAM user/role lacks required permissions. Check:

1. The IAM policy attached to your user/role
2. Any Service Control Policies (SCPs) in AWS Organizations
3. Resource-based policies on target resources

### CDK Bootstrap Issues

If CDK commands fail with bootstrap errors:

```bash
# Check if bootstrapped
aws cloudformation describe-stacks --stack-name CDKToolkit --profile api-factory

# Re-bootstrap if needed
cdk bootstrap aws://ACCOUNT_ID/REGION --profile api-factory
```

## Security Best Practices

1. **Never commit credentials** — Use `.gitignore` to exclude `.env` files
2. **Use named profiles** — Avoid using root account or default profile
3. **Enable MFA** — Require MFA for IAM users
4. **Rotate keys regularly** — Create new access keys every 90 days
5. **Use SSO when possible** — Temporary credentials are safer than long-lived keys
6. **Least privilege** — Only grant permissions that are needed
7. **Separate accounts** — Use different AWS accounts for dev/staging/prod

## Next Steps

Once your AWS credentials are configured:

1. [Create your first project](../getting-started.md)
2. [Configure your API](../reference/configuration.md)
3. [Deploy to AWS](../getting-started.md#step-5-deploy-to-aws)
