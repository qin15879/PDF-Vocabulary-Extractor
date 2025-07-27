"""
基础配置管理系统

提供配置文件加载、环境变量处理和配置验证功能
"""

import os
import yaml
from typing import Any, Dict, Optional
from pathlib import Path
from ..core.interfaces import ConfigManagerInterface


class ConfigManager(ConfigManagerInterface):
    """配置管理器实现"""
    
    # 默认配置
    DEFAULT_CONFIG = {
        'api': {
            'primary_dictionary': 'easypronunciation',
            'backup_dictionary': 'leskoff',
            'timeout': 30,
            'max_retries': 3,
            'api_keys': {}
        },
        'processing': {
            'max_file_size_mb': 50,
            'batch_size': 100,
            'parallel_workers': 4
        },
        'output': {
            'pdf_format': 'A4',
            'font_size': 12,
            'words_per_page': 50,
            'font_family': 'DejaVu Sans'
        },
        'logging': {
            'level': 'INFO',
            'file': 'vocabulary_extractor.log'
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化配置管理器
        
        Args:
            config_path: 配置文件路径，如果为None则使用默认路径
        """
        self._config = self.DEFAULT_CONFIG.copy()
        self._config_path = config_path
        
        # 尝试加载配置文件
        if config_path and Path(config_path).exists():
            self.load_config(config_path)
        else:
            # 尝试加载默认配置文件
            self._try_load_default_config()
        
        # 应用环境变量覆盖
        self._apply_env_overrides()
    
    def get(self, key: str, default=None) -> Any:
        """获取配置值
        
        支持点号分隔的嵌套键，如 'api.timeout'
        """
        keys = key.split('.')
        value = self._config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any):
        """设置配置值
        
        支持点号分隔的嵌套键
        """
        keys = key.split('.')
        config = self._config
        
        # 导航到父级字典
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # 设置最终值
        config[keys[-1]] = value
    
    def load_config(self, config_path: Optional[str] = None):
        """加载配置文件"""
        if config_path is None:
            config_path = self._config_path
        
        if not config_path or not Path(config_path).exists():
            return
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = yaml.safe_load(f)
                if user_config:
                    self._merge_config(self._config, user_config)
        except Exception as e:
            print(f"警告: 无法加载配置文件 {config_path}: {e}")
    
    def validate_config(self) -> bool:
        """验证配置的有效性"""
        try:
            # 验证必需的配置项
            required_keys = [
                'api.timeout',
                'processing.max_file_size_mb',
                'output.pdf_format'
            ]
            
            for key in required_keys:
                if self.get(key) is None:
                    return False
            
            # 验证数值范围
            if self.get('api.timeout', 0) <= 0:
                return False
            
            if self.get('processing.max_file_size_mb', 0) <= 0:
                return False
            
            return True
            
        except Exception:
            return False
    
    def _try_load_default_config(self):
        """尝试加载默认位置的配置文件"""
        default_paths = [
            'config.yaml',
            'config.yml',
            os.path.expanduser('~/.vocabulary_extractor/config.yaml'),
            '/etc/vocabulary_extractor/config.yaml'
        ]
        
        for path in default_paths:
            if Path(path).exists():
                self.load_config(path)
                self._config_path = path
                break
    
    def _apply_env_overrides(self):
        """应用环境变量覆盖"""
        env_mappings = {
            'VOCAB_API_TIMEOUT': 'api.timeout',
            'VOCAB_MAX_FILE_SIZE': 'processing.max_file_size_mb',
            'VOCAB_BATCH_SIZE': 'processing.batch_size',
            'VOCAB_PDF_FORMAT': 'output.pdf_format',
            'VOCAB_LOG_LEVEL': 'logging.level'
        }
        
        for env_key, config_key in env_mappings.items():
            env_value = os.getenv(env_key)
            if env_value is not None:
                # 尝试转换数据类型
                try:
                    if config_key.endswith(('timeout', 'max_file_size_mb', 'batch_size')):
                        env_value = int(env_value)
                    elif config_key.endswith('font_size'):
                        env_value = float(env_value)
                except ValueError:
                    continue
                
                self.set(config_key, env_value)
    
    def _merge_config(self, base: Dict, update: Dict):
        """递归合并配置字典"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    @property
    def config(self) -> Dict:
        """获取完整配置字典（只读）"""
        return self._config.copy()