import os
import yaml
from typing import Dict, Any, Optional


def load_yaml_config(file_path: str) -> Dict[str, Any]:
    """
    Load a YAML configuration file and process environment variables
    
    Args:
        file_path: Path to the YAML file
        
    Returns:
        Dictionary containing the configuration
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Config file not found: {file_path}")
    
    with open(file_path, 'r') as file:
        config = yaml.safe_load(file)
    
    # Process environment variables in the config
    config = _process_env_vars(config)
    
    return config


def _process_env_vars(config: Any) -> Any:
    """
    Recursively process environment variables in config values
    
    Args:
        config: Config object (dict, list, or scalar value)
        
    Returns:
        Config with environment variables replaced
    """
    if isinstance(config, dict):
        return {key: _process_env_vars(value) for key, value in config.items()}
    elif isinstance(config, list):
        return [_process_env_vars(item) for item in config]
    elif isinstance(config, str) and config.startswith("${") and config.endswith("}"):
        env_var = config[2:-1]
        return os.environ.get(env_var, "")
    else:
        return config


def save_yaml_config(config: Dict[str, Any], file_path: str) -> None:
    """
    Save a configuration dictionary to a YAML file
    
    Args:
        config: Configuration dictionary to save
        file_path: Path where to save the YAML file
    """
    # Ensure directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, 'w') as file:
        yaml.dump(config, file, default_flow_style=False)


def get_brands_config(config_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Load the brands configuration
    
    Args:
        config_dir: Optional directory where config files are located
        
    Returns:
        Brands configuration dictionary
    """
    config_dir = config_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
    return load_yaml_config(os.path.join(config_dir, "brands.yaml"))


def get_sources_config(config_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Load the news sources configuration
    
    Args:
        config_dir: Optional directory where config files are located
        
    Returns:
        News sources configuration dictionary
    """
    config_dir = config_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
    return load_yaml_config(os.path.join(config_dir, "sources.yaml"))


def get_agent_config(config_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Load the agent configuration
    
    Args:
        config_dir: Optional directory where config files are located
        
    Returns:
        Agent configuration dictionary
    """
    config_dir = config_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
    return load_yaml_config(os.path.join(config_dir, "agent_config.yaml"))


def get_app_config(config_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Load the app configuration
    
    Args:
        config_dir: Optional directory where config files are located
        
    Returns:
        App configuration dictionary
    """
    config_dir = config_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
    return load_yaml_config(os.path.join(config_dir, "app_config.yaml"))