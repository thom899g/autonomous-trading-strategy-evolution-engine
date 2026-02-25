"""
Configuration management for the Trading Strategy Evolution Engine.
Centralizes all environment variables, constants, and Firebase configuration.
"""
import os
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('trading_engine.log')
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class FirebaseConfig:
    """Firebase configuration dataclass"""
    project_id: str
    private_key_id: str
    private_key: str
    client_email: str
    client_id: str
    auth_uri: str = "https://accounts.google.com/o/oauth2/auth"
    token_uri: str = "https://oauth2.googleapis.com/token"
    auth_provider_x509_cert_url: str = "https://www.googleapis.com/oauth2/v1/certs"
    client_x509_cert_url: str = ""

@dataclass
class ExchangeConfig:
    """Exchange API configuration"""
    name: str
    api_key: str
    api_secret: str
    paper_trading: bool = True
    rate_limit: int = 1000

@dataclass
class EngineConfig:
    """Main engine configuration"""
    # Data settings
    historical_data_days: int = 365
    candle_timeframe: str = "1h"
    
    # Strategy settings
    max_strategies: int = 100
    generation_size: int = 20
    mutation_rate: float = 0.15
    
    # Risk management
    max_position_size: float = 0.1  # 10% of portfolio
    stop_loss_pct: float = 0.02     # 2% stop loss
    take_profit_pct: float = 0.05   # 5% take profit
    
    # Backtesting
    initial_capital: float = 10000.0
    commission_rate: float = 0.001  # 0.1% commission
    
    # Performance thresholds
    min_sharpe_ratio: float = 0.5
    min_win_rate: float = 0.45
    max_drawdown: float = 0.25

class ConfigManager:
    """Manages configuration loading and validation"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or Path.home() / ".trading_engine" / "config.json"
        self.firebase_config: Optional[FirebaseConfig] = None
        self.exchange_config: Optional[ExchangeConfig] = None
        self.engine_config = EngineConfig()
        self._secrets_loaded = False
        
    def load_configuration(self) -> bool:
        """Load configuration from file and environment variables"""
        try:
            # Load from file if exists
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config_data = json.load(f)
                    self._load_from_dict(config_data)
                    logger.info(f"Loaded configuration from {self.config_path}")
            
            # Override with environment variables
            self._load_from_env()
            
            # Validate critical configurations
            if not self._validate_config():
                logger.error("Configuration validation failed")
                return False
                
            self._secrets_loaded = True
            logger.info("Configuration loaded successfully")
            return True
            
        except FileNotFoundError:
            logger.warning(f"Config file not found at {self.config_path}")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            return False
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return False
    
    def _load_from_dict(self, config_data: Dict[str, Any]):
        """Load configuration from dictionary"""
        # Load Firebase config
        if 'firebase' in config_data:
            firebase_data = config_data['firebase']
            self.firebase_config = FirebaseConfig(**firebase_data)
        
        # Load Exchange config
        if 'exchange' in config_data:
            exchange_data = config_data['exchange']
            self.exchange_config = ExchangeConfig(**exchange_data)
        
        # Load Engine config
        if 'engine' in config_data:
            engine_data = config_data['engine']
            for key, value in engine_data.items():
                if hasattr(self.engine_config, key):
                    setattr(self.engine_config, key, value)
    
    def _load_from_env(self):
        """Load sensitive data from environment variables"""
        # Firebase environment variables
        firebase_vars = {
            'project_id': 'FIREBASE_PROJECT_ID',
            'private_key_id': 'FIREBASE_PRIVATE_KEY_ID',
            'private_key': 'FIREBASE_PRIVATE_KEY',
            'client_email': 'FIREBASE_CLIENT_EMAIL',
            'client_id': 'FIREBASE_CLIENT_ID'
        }
        
        firebase_data = {}
        for attr, env_var in firebase_vars.items():
            value = os.getenv(env_var)
            if value:
                firebase_data[attr] = value
        
        if firebase_data and len(firebase_data) == len(firebase_vars):
            self.firebase_config = FirebaseConfig(**firebase_data)
            logger.info("Firebase config loaded from environment variables")
        
        # Exchange environment variables
        exchange_name = os.getenv('EXCHANGE_NAME', 'binance')
        api_key = os.getenv('EXCHANGE_API_KEY')
        api_secret = os.getenv('EXCHANGE_API_SECRET')
        
        if api_key and api_secret:
            self.exchange_config = ExchangeConfig(
                name=exchange_name,
                api_key=api_key,
                api_secret=api_secret,
                paper_trading=os.getenv('P