#!/usr/bin/env python3
import os
import yaml
from aws_cdk import App, Environment
from app.api.api_stack import ApiStack
from app.api.config_models import AppConfig

def load_config(path: str) -> AppConfig:
    """
    load_config reads the YAML settings file and returns an AppConfig instance.
    """
    with open(path, "r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
    return AppConfig(**data)

def main() -> None:
    """
    main is the entry point for the CDK app.
    """
    app = App()

    # Point to the new config file location
    config = load_config("app/config/settings.yaml")

    # If you need environment variables (optional):
    # env = Environment(account=os.environ["CDK_DEFAULT_ACCOUNT"], region=os.environ.get("AWS_REGION", "us-east-1"))

    # Instantiate the stack with the new import paths

    ApiStack(app, "ApiStack", config=config
        # If you don't specify 'env', this stack will be environment-agnostic.
        # Account/Region-dependent features and context lookups will not work,
        # but a single synthesized template can be deployed anywhere.

        # Uncomment the next line to specialize this stack for the AWS Account
        # and Region that are implied by the current CLI configuration.

        #env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),

        # Uncomment the next line if you know exactly what Account and Region you
        # want to deploy the stack to. */

        #env=cdk.Environment(account='123456789012', region='us-east-1'),

        # For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html
        )

    app.synth()

if __name__ == "__main__":
    main()
