"""
Configuration loader for the Financial Email Agent.

This module handles loading and merging configuration from YAML files
and environment variables, with validation using Pydantic models.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from .models import AppConfig


class ConfigLoader:
    """Load and manage application configuration."""

    def __init__(self, config_path: Optional[str] = None, env_file: Optional[str] = None):
        """
        Initialize the configuration loader.

        Args:
            config_path: Path to YAML configuration file. Defaults to config/config.yaml
            env_file: Path to .env file. Defaults to .env in project root
        """
        self.project_root = Path(__file__).parent.parent.parent
        self.config_path = Path(config_path) if config_path else self.project_root / "config" / "config.yaml"
        self.env_file = Path(env_file) if env_file else self.project_root / ".env"
        
        # Load environment variables
        if self.env_file.exists():
            load_dotenv(self.env_file)

    def load(self) -> AppConfig:
        """
        Load configuration from YAML and environment variables.

        Returns:
            AppConfig: Validated application configuration

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If configuration is invalid
        """
        # Load YAML configuration
        yaml_config = self._load_yaml()
        
        # Override with environment variables
        config_dict = self._merge_env_vars(yaml_config)
        
        # Validate and create config object
        try:
            config = AppConfig(**config_dict)
            return config
        except Exception as e:
            raise ValueError(f"Invalid configuration: {e}")

    def _load_yaml(self) -> Dict[str, Any]:
        """
        Load configuration from YAML file.

        Returns:
            Dict containing YAML configuration

        Raises:
            FileNotFoundError: If config file doesn't exist
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        return config or {}

    def _merge_env_vars(self, yaml_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge environment variables into configuration.

        Environment variables take precedence over YAML configuration.

        Args:
            yaml_config: Configuration loaded from YAML

        Returns:
            Merged configuration dictionary
        """
        config = yaml_config.copy()

        # Email configuration
        if 'email' not in config:
            config['email'] = {}
        
        if 'oauth2' not in config['email']:
            config['email']['oauth2'] = {}
        
        if os.getenv('GMAIL_CREDENTIALS_FILE'):
            config['email']['oauth2']['credentials_file'] = os.getenv('GMAIL_CREDENTIALS_FILE')
        
        if os.getenv('GMAIL_TOKEN_FILE'):
            config['email']['oauth2']['token_file'] = os.getenv('GMAIL_TOKEN_FILE')
        
        if 'monitoring' not in config['email']:
            config['email']['monitoring'] = {}
        
        if os.getenv('EMAIL_CHECK_INTERVAL_MINUTES'):
            config['email']['monitoring']['interval_minutes'] = int(os.getenv('EMAIL_CHECK_INTERVAL_MINUTES'))
        
        if os.getenv('EMAIL_MAX_PER_CHECK'):
            config['email']['monitoring']['max_emails_per_check'] = int(os.getenv('EMAIL_MAX_PER_CHECK'))
        
        if 'filters' not in config['email']:
            config['email']['filters'] = {}
        
        if os.getenv('EMAIL_UNREAD_ONLY'):
            config['email']['filters']['unread_only'] = os.getenv('EMAIL_UNREAD_ONLY').lower() == 'true'

        # Llama configuration
        if 'llama' not in config:
            config['llama'] = {}
        
        if os.getenv('OLLAMA_API_URL'):
            config['llama']['api_url'] = os.getenv('OLLAMA_API_URL')
        
        if os.getenv('LLAMA_MODEL'):
            config['llama']['model'] = os.getenv('LLAMA_MODEL')
        
        if os.getenv('LLAMA_TEMPERATURE'):
            config['llama']['temperature'] = float(os.getenv('LLAMA_TEMPERATURE'))
        
        if os.getenv('LLAMA_MAX_TOKENS'):
            config['llama']['max_tokens'] = int(os.getenv('LLAMA_MAX_TOKENS'))

        # MongoDB configuration
        if 'mongodb' not in config:
            config['mongodb'] = {}
        
        if os.getenv('MONGODB_CONNECTION_STRING'):
            config['mongodb']['connection_string'] = os.getenv('MONGODB_CONNECTION_STRING')
        
        if os.getenv('MONGODB_DATABASE'):
            config['mongodb']['database'] = os.getenv('MONGODB_DATABASE')

        # Logging configuration
        if 'logging' not in config:
            config['logging'] = {}
        
        if os.getenv('LOG_LEVEL'):
            config['logging']['level'] = os.getenv('LOG_LEVEL')
        
        if os.getenv('LOG_FILE'):
            config['logging']['file'] = os.getenv('LOG_FILE')
        
        if os.getenv('LOG_MAX_SIZE_MB'):
            config['logging']['max_size_mb'] = int(os.getenv('LOG_MAX_SIZE_MB'))
        
        if os.getenv('LOG_BACKUP_COUNT'):
            config['logging']['backup_count'] = int(os.getenv('LOG_BACKUP_COUNT'))

        # Scheduler configuration
        if 'scheduler' not in config:
            config['scheduler'] = {}
        
        if os.getenv('SCHEDULER_ENABLED'):
            config['scheduler']['enabled'] = os.getenv('SCHEDULER_ENABLED').lower() == 'true'
        
        if os.getenv('SCHEDULER_RETRY_FAILED'):
            config['scheduler']['retry_failed'] = os.getenv('SCHEDULER_RETRY_FAILED').lower() == 'true'
        
        if os.getenv('SCHEDULER_MAX_RETRIES'):
            config['scheduler']['max_retries'] = int(os.getenv('SCHEDULER_MAX_RETRIES'))

        # Security configuration
        if 'security' not in config:
            config['security'] = {}
        
        if os.getenv('MASK_SENSITIVE_DATA'):
            config['security']['mask_sensitive_data'] = os.getenv('MASK_SENSITIVE_DATA').lower() == 'true'
        
        if os.getenv('ENCRYPT_TOKENS'):
            config['security']['encrypt_tokens'] = os.getenv('ENCRYPT_TOKENS').lower() == 'true'

        # Application environment
        if os.getenv('ENVIRONMENT'):
            config['environment'] = os.getenv('ENVIRONMENT')
        
        if os.getenv('DEBUG'):
            config['debug'] = os.getenv('DEBUG').lower() == 'true'

        return config


# Global configuration instance
_config: Optional[AppConfig] = None


def get_config(reload: bool = False) -> AppConfig:
    """
    Get the global configuration instance.

    Args:
        reload: Force reload configuration from files

    Returns:
        AppConfig: Application configuration
    """
    global _config
    
    if _config is None or reload:
        loader = ConfigLoader()
        _config = loader.load()
    
    return _config


def load_config(config_path: Optional[str] = None, env_file: Optional[str] = None) -> AppConfig:
    """
    Load configuration from specified files.

    Args:
        config_path: Path to YAML configuration file
        env_file: Path to .env file

    Returns:
        AppConfig: Application configuration
    """
    loader = ConfigLoader(config_path=config_path, env_file=env_file)
    return loader.load()

# Made with Bob
