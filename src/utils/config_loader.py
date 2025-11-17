"""Configuration loader for the project."""
import os
import yaml
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to the configuration YAML file
        
    Returns:
        Dictionary containing configuration values
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is invalid YAML
    """
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config or {}


def load_env_vars(env_path: str = ".env") -> None:
    """
    Load environment variables from .env file.
    
    Args:
        env_path: Path to the .env file
    """
    env_file = Path(env_path)
    if env_file.exists():
        load_dotenv(env_file)
    else:
        # Try to load from default location
        load_dotenv()


def get_config_value(config: Dict[str, Any], key_path: str, default: Any = None) -> Any:
    """
    Get a configuration value using dot notation (e.g., 'api.base_url').
    
    Args:
        config: Configuration dictionary
        key_path: Dot-separated path to the configuration value
        default: Default value if key is not found
        
    Returns:
        Configuration value or default
    """
    keys = key_path.split('.')
    value = config
    
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    
    return value


def get_api_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Get API configuration section."""
    return config.get('api', {})


def get_paths_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Get paths configuration section."""
    return config.get('paths', {})


def get_filtering_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Get filtering configuration section."""
    return config.get('filtering', {})

