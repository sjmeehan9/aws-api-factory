import aws_cdk.assertions as assertions
from aws_cdk import App
from app.api.api_stack import ApiStack
from app.api.config_models import AppConfig

# example tests. To run these tests, uncomment this file along with the example
# resource in api/api_stack.py
def test_sqs_queue_created():
    app = App()
    test_config = AppConfig(
        environment="test",
        api_name="test-api",
        throttling_burst_limit=10,
        throttling_rate_limit=5
    )
    stack = ApiStack(app, "api", config=test_config)
    template = assertions.Template.from_stack(stack)

    assert "AWS::SQS::Queue" in template["Resources"]
