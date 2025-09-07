"""
Configuration management for Apple Notes Research Bot
"""

import os
import json
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Optional, List
import keyring

logger = logging.getLogger(__name__)

@dataclass
class Config:
    """Configuration for the research bot"""
    
    # API Keys (retrieved from environment or keychain)
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    
    # Monitoring settings
    check_interval: int = 30  # seconds
    monitor_folders: List[str] = field(default_factory=lambda: ["Notes"])
    
    # Research settings
    research_confidence_threshold: float = 0.7
    max_research_time: int = 60  # seconds
    parallel_research: bool = True
    
    # AI Model settings
    claude_analysis_model: str = "claude-3-5-haiku-20241022"
    claude_research_model: str = "claude-3-5-sonnet-20250107"
    openai_model: str = "gpt-4o-mini"
    
    # Token limits
    max_analysis_tokens: int = 300
    max_research_tokens: int = 800
    
    # Categories
    research_categories: List[str] = field(default_factory=lambda: [
        "software", "ai", "business", "building", "lifestyle", "productivity", "general"
    ])
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = "research_bot.log"
    
    # Storage
    state_file: str = ".research_bot_state.json"
    processed_notes_cache: str = ".processed_notes_cache.json"
    
    # Rate limiting
    rate_limit_delay: float = 1.0  # seconds between API calls
    max_retries: int = 3
    retry_delay: float = 2.0  # seconds
    
    @classmethod
    def from_file(cls, config_file: str = "config.json") -> "Config":
        """Load configuration from file with environment variable override"""
        config = cls()
        
        # Load from file if exists
        config_path = Path(config_file)
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    file_config = json.load(f)
                    for key, value in file_config.items():
                        if hasattr(config, key):
                            setattr(config, key, value)
                logger.info(f"Loaded configuration from {config_file}")
            except Exception as e:
                logger.warning(f"Failed to load config file: {e}")
        
        # Override with environment variables
        config._load_api_keys()
        
        # Environment overrides for other settings
        env_mappings = {
            'CORAL_CHECK_INTERVAL': ('check_interval', int),
            'CORAL_CONFIDENCE_THRESHOLD': ('research_confidence_threshold', float),
            'CORAL_MAX_RESEARCH_TIME': ('max_research_time', int),
            'CORAL_LOG_LEVEL': ('log_level', str),
        }
        
        for env_var, (attr, type_func) in env_mappings.items():
            if env_value := os.getenv(env_var):
                try:
                    setattr(config, attr, type_func(env_value))
                    logger.debug(f"Override {attr} from environment: {env_value}")
                except ValueError as e:
                    logger.warning(f"Invalid {env_var} value: {e}")
        
        return config
    
    def _load_api_keys(self):
        """Load API keys from environment or macOS keychain"""
        # Try environment variables first
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        
        # Try macOS keychain if not in environment
        if not self.anthropic_api_key:
            try:
                self.anthropic_api_key = keyring.get_password(
                    "coral_collective", "anthropic_api_key"
                )
                if self.anthropic_api_key:
                    logger.info("Loaded Anthropic API key from keychain")
            except Exception as e:
                logger.debug(f"Keychain access failed: {e}")
        
        if not self.openai_api_key:
            try:
                self.openai_api_key = keyring.get_password(
                    "coral_collective", "openai_api_key"
                )
                if self.openai_api_key:
                    logger.info("Loaded OpenAI API key from keychain")
            except Exception as e:
                logger.debug(f"Keychain access failed: {e}")
    
    def save_api_keys_to_keychain(self):
        """Save API keys to macOS keychain for secure storage"""
        if self.anthropic_api_key:
            try:
                keyring.set_password(
                    "coral_collective", "anthropic_api_key", self.anthropic_api_key
                )
                logger.info("Saved Anthropic API key to keychain")
            except Exception as e:
                logger.error(f"Failed to save Anthropic key: {e}")
        
        if self.openai_api_key:
            try:
                keyring.set_password(
                    "coral_collective", "openai_api_key", self.openai_api_key
                )
                logger.info("Saved OpenAI API key to keychain")
            except Exception as e:
                logger.error(f"Failed to save OpenAI key: {e}")
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of issues"""
        issues = []
        
        if not self.anthropic_api_key:
            issues.append("Missing Anthropic API key")
        
        if not self.openai_api_key:
            issues.append("Missing OpenAI API key")
        
        if self.check_interval < 10:
            issues.append("Check interval too short (minimum 10 seconds)")
        
        if self.research_confidence_threshold < 0 or self.research_confidence_threshold > 1:
            issues.append("Confidence threshold must be between 0 and 1")
        
        return issues
    
    def to_dict(self) -> Dict:
        """Convert config to dictionary (excluding sensitive data)"""
        config_dict = {}
        for key, value in self.__dict__.items():
            if 'api_key' not in key.lower() and not key.startswith('_'):
                config_dict[key] = value
        return config_dict
    
    def save(self, filepath: Optional[str] = None):
        """Save configuration to file (excluding API keys)"""
        filepath = filepath or "config.json"
        config_dict = self.to_dict()
        
        with open(filepath, 'w') as f:
            json.dump(config_dict, f, indent=2)
        
        logger.info(f"Saved configuration to {filepath}")

def setup_logging(config: Config):
    """Setup logging based on configuration"""
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(config.log_file) if config.log_file else logging.NullHandler()
        ]
    )
    
    # Set specific loggers
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('anthropic').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)