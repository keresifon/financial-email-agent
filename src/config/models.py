"""
Configuration models for the Financial Email Agent.

This module defines Pydantic models for validating and managing
application configuration from YAML files and environment variables.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class EmailProvider(str, Enum):
    """Supported email providers."""
    GMAIL = "gmail"


class LogLevel(str, Enum):
    """Supported logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Environment(str, Enum):
    """Application environment."""
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class OAuth2Config(BaseModel):
    """OAuth2 configuration for email authentication."""
    credentials_file: str = Field(default="credentials.json", description="Path to OAuth2 credentials file")
    token_file: str = Field(default="token.json", description="Path to OAuth2 token file")


class EmailFiltersConfig(BaseModel):
    """Email filtering configuration."""
    unread_only: bool = Field(default=True, description="Only process unread emails")
    labels: List[str] = Field(default_factory=list, description="Filter by specific labels")


class EmailMonitoringConfig(BaseModel):
    """Email monitoring configuration."""
    interval_minutes: int = Field(default=15, ge=1, le=1440, description="Check interval in minutes")
    max_emails_per_check: int = Field(default=50, ge=1, le=500, description="Maximum emails to process per check")


class EmailConfig(BaseModel):
    """Email service configuration."""
    provider: EmailProvider = Field(default=EmailProvider.GMAIL, description="Email provider")
    oauth2: OAuth2Config = Field(default_factory=OAuth2Config, description="OAuth2 configuration")
    monitoring: EmailMonitoringConfig = Field(default_factory=EmailMonitoringConfig, description="Monitoring settings")
    filters: EmailFiltersConfig = Field(default_factory=EmailFiltersConfig, description="Email filters")


class LlamaConfig(BaseModel):
    """Llama LLM configuration."""
    model: str = Field(default="llama3.1:8b", description="Llama model name")
    api_url: str = Field(default="http://localhost:11434", description="Ollama API URL")
    temperature: float = Field(default=0.1, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(default=2048, ge=1, le=32768, description="Maximum tokens in response")
    timeout_seconds: int = Field(default=60, ge=1, le=600, description="Request timeout in seconds")

    @field_validator('api_url')
    @classmethod
    def validate_api_url(cls, v: str) -> str:
        """Validate API URL format."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('API URL must start with http:// or https://')
        return v.rstrip('/')


class MongoDBCollectionsConfig(BaseModel):
    """MongoDB collections configuration."""
    emails: str = Field(default="emails", description="Emails collection name")
    invoices: str = Field(default="invoices", description="Invoices collection name")
    receipts: str = Field(default="receipts", description="Receipts collection name")
    bank_statements: str = Field(default="bank_statements", description="Bank statements collection name")
    expense_reports: str = Field(default="expense_reports", description="Expense reports collection name")


class MongoDBConfig(BaseModel):
    """MongoDB configuration."""
    connection_string: str = Field(default="mongodb://localhost:27017", description="MongoDB connection string")
    database: str = Field(default="financial_data", description="Database name")
    collections: MongoDBCollectionsConfig = Field(default_factory=MongoDBCollectionsConfig, description="Collection names")
    timeout_ms: int = Field(default=10000, ge=1000, le=60000, description="Connection timeout in milliseconds")


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: LogLevel = Field(default=LogLevel.INFO, description="Logging level")
    file: str = Field(default="logs/agent.log", description="Log file path")
    max_size_mb: int = Field(default=100, ge=1, le=1000, description="Maximum log file size in MB")
    backup_count: int = Field(default=5, ge=1, le=100, description="Number of backup log files")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format"
    )


class SchedulerConfig(BaseModel):
    """Scheduler configuration."""
    enabled: bool = Field(default=True, description="Enable scheduler")
    check_interval_minutes: int = Field(default=15, ge=1, le=1440, description="Check interval in minutes")
    retry_failed: bool = Field(default=True, description="Retry failed tasks")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    retry_delay_seconds: int = Field(default=300, ge=1, le=3600, description="Delay between retries in seconds")


class ReportingConfig(BaseModel):
    """Reporting configuration."""
    enabled: bool = Field(default=True, description="Enable reporting")
    daily_summary: bool = Field(default=True, description="Generate daily summary")
    email_alerts: bool = Field(default=False, description="Send email alerts")


class SecurityConfig(BaseModel):
    """Security configuration."""
    mask_sensitive_data: bool = Field(default=True, description="Mask sensitive data in logs")
    encrypt_tokens: bool = Field(default=True, description="Encrypt stored tokens")
    data_retention_days: int = Field(default=365, ge=1, le=3650, description="Data retention period in days")


class ClassificationConfig(BaseModel):
    """Classification configuration."""
    min_confidence: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum confidence threshold")
    categories: List[str] = Field(
        default_factory=lambda: [
            "invoice",
            "receipt",
            "statement",
            "tax_document",
            "contract",
            "payment_confirmation",
            "other"
        ],
        description="Classification categories"
    )



class AppConfig(BaseModel):
    """Main application configuration."""
    email: EmailConfig = Field(default_factory=EmailConfig, description="Email configuration")
    llama: LlamaConfig = Field(default_factory=LlamaConfig, description="Llama LLM configuration")
    mongodb: MongoDBConfig = Field(default_factory=MongoDBConfig, description="MongoDB configuration")
    logging: LoggingConfig = Field(default_factory=LoggingConfig, description="Logging configuration")
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig, description="Scheduler configuration")
    reporting: ReportingConfig = Field(default_factory=ReportingConfig, description="Reporting configuration")
    security: SecurityConfig = Field(default_factory=SecurityConfig, description="Security configuration")
    classification: ClassificationConfig = Field(default_factory=ClassificationConfig, description="Classification configuration")
    environment: Environment = Field(default=Environment.DEVELOPMENT, description="Application environment")
    debug: bool = Field(default=False, description="Debug mode")

    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True

# Made with Bob
