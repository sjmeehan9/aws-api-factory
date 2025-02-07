import json
import logging
from typing import Any, Dict
from dataclasses import dataclass
import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

@dataclass
class RequestData:
    """
    RequestData represents the input payload data.
    """
    service_type: str
    message: str

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    lambda_handler is the entry point for AWS Lambda.
    """
    try:
        body = json.loads(event.get("body", "{}"))
        request_data = RequestData(**body)
        response = handle_service_request(request_data)
        return {
            "statusCode": 200,
            "body": json.dumps({"result": response})
        }
    except Exception as e:
        logger.error(f"Lambda error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

def handle_service_request(data: RequestData) -> str:
    """
    handle_service_request directs requests to the appropriate backend service.
    """
    service = service_factory(data.service_type)
    result = service.process(data.message)
    return result

def service_factory(service_type: str):
    """
    service_factory returns a backend service object based on service_type.
    """
    if service_type == "sqs":
        return SqsService()
    # if service_type == "sns":
    #     return SnsService()
    # if service_type == "eventbridge":
    #     return EventBridgeService()
    return DefaultService()

class BaseService:
    """
    BaseService is the interface for backend services.
    """
    def process(self, message: str) -> str:
        """
        process executes the main logic for the service.
        """
        raise NotImplementedError("Subclasses must implement process method.")

class SqsService(BaseService):
    """
    SqsService handles messages via SQS.
    """
    def __init__(self) -> None:
        self._sqs = boto3.resource("sqs")
        self._queue = self._sqs.get_queue_by_name(QueueName="FactoryQueue")

    def process(self, message: str) -> str:
        response = self._queue.send_message(MessageBody=message)
        return f"Message sent to SQS with ID {response.get('MessageId')}"

class SnsService(BaseService):
    """
    SnsService handles messages via SNS.
    """
    def __init__(self) -> None:
        self._sns = boto3.client("sns")
        self._topic_arn = "REPLACE_WITH_TOPIC_ARN"

    def process(self, message: str) -> str:
        response = self._sns.publish(TopicArn=self._topic_arn, Message=message)
        return f"Message published to SNS with ID {response.get('MessageId')}"

class EventBridgeService(BaseService):
    """
    EventBridgeService handles messages via EventBridge.
    """
    def __init__(self) -> None:
        self._events = boto3.client("events")
        self._event_bus_name = "FactoryEventBus"

    def process(self, message: str) -> str:
        response = self._events.put_events(
            Entries=[
                {
                    "Source": "factory.service",
                    "DetailType": "FactoryEvent",
                    "Detail": json.dumps({"message": message}),
                    "EventBusName": self._event_bus_name
                }
            ]
        )
        return "EventBridge event triggered successfully."

class DefaultService(BaseService):
    """
    DefaultService handles unrecognized service types.
    """
    def process(self, message: str) -> str:
        return f"No matching backend service found for message: {message}"