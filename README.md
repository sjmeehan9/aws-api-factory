
# Account Wide Settings to Configure

## Basics for New AWS Account
 * Create AWS account
 * Enable Multi-Factor Authentication (MFA) on the Root Account
 * Set up Budget & Cost Management alerts
 * Create IAM user and group with AdministratorAccess managed policy on AdminGroup
 * Enable MFA for the admin IAM user
 * Set Up AWS CloudTrail


## AWS API Settings

### Creating Keys
 * IAM -> Users -> User -> Access keys -> Create access key

##### OR
`aws iam create-access-key --user-name <YourIAMUserName>`

##### THEN - add the credentials for local use
`aws configure`


### Add AWS Credentials to GitHub Repository Secrets
 * Settings -> Secrets and variables -> Actions


### Install CDK (Must have Node installed)
`npm install -g aws-cdk`


### Bootstrap AWS environment for AWS CDK
`cdk bootstrap aws://ACCOUNT_ID/REGION`


### Configure a CloudWatch Logs IAM Role for API Gateway

1. Create or Identify an IAM Role
```
aws iam create-role \
  --role-name APIGatewayCloudWatchLogsRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "Service": "apigateway.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
      }
    ]
  }'
```

2. Attach the Role Policy
```
aws iam attach-role-policy \
  --role-name APIGatewayCloudWatchLogsRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs
```

3. Update the Account Settings for API Gateway
```
aws apigateway update-account \
  --patch-operations op=replace,path=/cloudwatchRoleArn,value=arn:aws:iam::<ACCOUNT_ID>:role/APIGatewayCloudWatchLogsRole
```


### Add Users to Cognito
```
aws cognito-idp admin-create-user \
  --user-pool-id <USER_POOL_ID> \
  --username newuser@example.com \
  --temporary-password MyTempPass123
```


## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation
