from constructs import Construct
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_kms as kms,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    aws_cognito as cognito,
    aws_logs as logs,
    aws_wafv2 as waf,
    aws_sqs as sqs,
    aws_sns as sns,
    aws_events as events,
    aws_events_targets as targets,
    aws_lambda_event_sources as lambda_event_sources
)

# Change import to point to app.api.config_models
from app.api.config_models import AppConfig

class ApiStack(Stack):
    """
    ApiStack builds the AWS infrastructure for the reusable API.
    """
    def __init__(self, scope: Construct, construct_id: str, config: AppConfig, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self._config = config

        self._kms_key = kms.Key(
            self, 
            "KmsKey",
            enable_key_rotation=True
        )

        self._vpc = ec2.Vpc(
            self,
            "Vpc",
            max_azs=2,
            nat_gateways=1
        )

        self._vpc.add_interface_endpoint(
            "SQSEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.SQS
        )
        self._vpc.add_interface_endpoint(
            "SNSEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.SNS
        )
        # self._vpc.add_interface_endpoint(
        #     "LambdaEndpoint",
        #     service=ec2.InterfaceVpcEndpointAwsService.LAMBDA
        # )

        self._user_pool = cognito.UserPool(
            self,
            "UserPool",
            user_pool_name=f"{self._config.api_name}-userpool"
        )

        self._user_pool_client = cognito.UserPoolClient(
            self,
            "UserPoolClient",
            user_pool=self._user_pool
        )

        self._lambda_role = iam.Role(
            self,
            "LambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
        )
        self._lambda_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
        )
        self._lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["kms:Encrypt","kms:Decrypt","kms:GenerateDataKey","kms:DescribeKey"],
                resources=[self._kms_key.key_arn]
            )
        )

        # Updated code path to "app/lambdas"
        self._lambda_function = _lambda.Function(
            self,
            "FactoryApiLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="main.lambda_handler",
            code=_lambda.Code.from_asset("app/lambdas"),
            role=self._lambda_role,
            vpc=self._vpc,
            environment={
                "KMS_KEY_ARN": self._kms_key.key_arn,
                "USER_POOL_ID": self._user_pool.user_pool_id,
                "USER_POOL_CLIENT_ID": self._user_pool_client.user_pool_client_id
            }
        )

        self._api = apigw.RestApi(
            self,
            "FactoryApi",
            rest_api_name=self._config.api_name,
            deploy_options=apigw.StageOptions(
                throttling_burst_limit=self._config.throttling_burst_limit,
                throttling_rate_limit=self._config.throttling_rate_limit,
                metrics_enabled=True,
                logging_level=apigw.MethodLoggingLevel.INFO,
                data_trace_enabled=False
            )
        )

        request_validator = self._api.add_request_validator(
            "RequestValidator",
            validate_request_body=True,
            validate_request_parameters=True
        )

        integration = apigw.LambdaIntegration(self._lambda_function)

        resource = self._api.root.add_resource("services")
        resource.add_method(
            "POST",
            integration,
            request_validator=request_validator,
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=apigw.CognitoUserPoolsAuthorizer(
                self,
                "CognitoAuthorizer",
                cognito_user_pools=[self._user_pool]
            ),
            method_responses=[
                apigw.MethodResponse(status_code="200"),
                apigw.MethodResponse(status_code="400"),
                apigw.MethodResponse(status_code="500")
            ]
        )

        self._api_gateway_waf = waf.CfnWebACL(
            self,
            "ApiWaf",
            default_action=waf.CfnWebACL.DefaultActionProperty(allow={}),
            scope="REGIONAL",
            visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name="FactoryApiWAF",
                sampled_requests_enabled=True
            ),
            name="FactoryApiWAF",
            rules=[]
        )
        waf.CfnWebACLAssociation(
            self,
            "ApiWafAssociation",
            resource_arn=self._api.deployment_stage.stage_arn,
            web_acl_arn=self._api_gateway_waf.attr_arn
        )

        self._api.root.add_cors_preflight(
            apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS
            )
        )

        self._queue = sqs.Queue(
            self,
            "FactoryQueue"
        )

        self._sns_topic = sns.Topic(
            self,
            "FactoryTopic"
        )

        self._event_bus = events.EventBus(
            self,
            "FactoryEventBus"
        )

        self._lambda_function.add_event_source(
            lambda_event_sources.SqsEventSource(self._queue)
        )

        events.Rule(
            self,
            "FactoryEventRule",
            event_bus=self._event_bus,
            event_pattern=events.EventPattern(source=["factory.service"]),
            targets=[targets.LambdaFunction(self._lambda_function)]
        )

    @property
    def api_url(self) -> str:
        """
        api_url returns the URL of the deployed API.
        """
        return self._api.url
