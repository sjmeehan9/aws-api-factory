"""config_models.py"""
from typing import Optional
from pydantic import BaseModel, Field

class AppConfig(BaseModel):
    """
    AppConfig is a data model for storing application configurations.
    """
    environment: str = Field(..., description="Application environment")
    api_name: str = Field(..., description="Name of the API")
    throttling_burst_limit: int = Field(..., description="API Gateway burst limit")
    throttling_rate_limit: int = Field(..., description="API Gateway steady-state request rate limit")
    additional_setting: Optional[str] = Field(None, description="An optional additional setting")
