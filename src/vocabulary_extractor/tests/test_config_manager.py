"""
配置管理器测试
"""

import os
import tempfile
import yaml
import unittest
from pathlib import Path
from vocabulary_extractor.config.manager import ConfigManager


class TestConfigManager(unittest.TestCase):
    """配置管理器测试类"""
    
    def setUp(self):
        """测试前的准备工作"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_config_path = Path(self.temp_dir.name) / "test_config.yaml"
        
        # 保存原始环境变量
        self.original_env = {}
        env_keys = [
            'VOCAB_API_TIMEOUT',
            'VOCAB_MAX_FILE_SIZE',
            'VOCAB_BATCH_SIZE',
            'VOCAB_PDF_FORMAT',
            'VOCAB_LOG_LEVEL'
        ]
        for key in env_keys:
            self.original_env[key] = os.environ.get(key)
            if key in os.environ:
                del os.environ[key]
    
    def tearDown(self):
        """测试后的清理工作"""
        # 恢复原始环境变量
        for key, value in self.original_env.items():
            if value is not None:
                os.environ[key] = value
            elif key in os.environ:
                del os.environ[key]
        
        self.temp_dir.cleanup()
    
    def test_default_config(self):
        """测试默认配置"""
        config_manager = ConfigManager()
        
        # 验证默认配置项存在
        self.assertIsNotNone(config_manager.get('api.timeout'))
        self.assertIsNotNone(config_manager.get('processing.max_file_size_mb'))
        self.assertIsNotNone(config_manager.get('output.pdf_format'))
        
        # 验证默认值
        self.assertEqual(config_manager.get('api.timeout'), 30)
        self.assertEqual(config_manager.get('processing.max_file_size_mb'), 50)
        self.assertEqual(config_manager.get('output.pdf_format'), 'A4')
    
    def test_load_config_file(self):
        """测试加载配置文件"""
        # 创建测试配置文件
        test_config = {
            'api': {
                'timeout': 60,
                'api_keys': {
                    'easypronunciation': 'test_key_123'
                }
            },
            'processing': {
                'max_file_size_mb': 100,
                'batch_size': 200
            }
        }
        
        with open(self.temp_config_path, 'w', encoding='utf-8') as f:
            yaml.dump(test_config, f)
        
        config_manager = ConfigManager(str(self.temp_config_path))
        
        # 验证配置已加载
        self.assertEqual(config_manager.get('api.timeout'), 60)
        self.assertEqual(config_manager.get('processing.max_file_size_mb'), 100)
        self.assertEqual(config_manager.get('api.api_keys.easypronunciation'), 'test_key_123')
    
    def test_env_override(self):
        """测试环境变量覆盖"""
        # 设置环境变量
        os.environ['VOCAB_API_TIMEOUT'] = '45'
        os.environ['VOCAB_MAX_FILE_SIZE'] = '75'
        os.environ['VOCAB_PDF_FORMAT'] = 'Letter'
        
        config_manager = ConfigManager()
        
        # 验证环境变量已覆盖默认值
        self.assertEqual(config_manager.get('api.timeout'), 45)
        self.assertEqual(config_manager.get('processing.max_file_size_mb'), 75)
        self.assertEqual(config_manager.get('output.pdf_format'), 'Letter')
    
    def test_nested_config_access(self):
        """测试嵌套配置访问"""
        config_manager = ConfigManager()
        
        # 测试点号分隔的键访问
        self.assertEqual(config_manager.get('api.timeout'), 30)
        self.assertEqual(config_manager.get('processing.batch_size'), 100)
        
        # 测试不存在的键返回默认值
        self.assertIsNone(config_manager.get('nonexistent.key'))
        self.assertEqual(config_manager.get('nonexistent.key', 'default'), 'default')
    
    def test_set_config(self):
        """测试设置配置值"""
        config_manager = ConfigManager()
        
        # 设置新值
        config_manager.set('api.timeout', 120)
        config_manager.set('processing.new_setting', 'test_value')
        
        # 验证值已设置
        self.assertEqual(config_manager.get('api.timeout'), 120)
        self.assertEqual(config_manager.get('processing.new_setting'), 'test_value')
    
    def test_config_validation(self):
        """测试配置验证"""
        config_manager = ConfigManager()
        
        # 默认配置应该有效
        self.assertTrue(config_manager.validate_config())
        
        # 设置无效值
        config_manager.set('api.timeout', -1)
        self.assertFalse(config_manager.validate_config())
        
        config_manager.set('api.timeout', 30)  # 恢复有效值
        config_manager.set('processing.max_file_size_mb', 0)
        self.assertFalse(config_manager.validate_config())
    
    def test_merge_config(self):
        """测试配置合并"""
        config_manager = ConfigManager()
        
        # 创建测试配置
        user_config = {
            'api': {
                'timeout': 90,
                'new_setting': 'added_value'
            },
            'output': {
                'font_size': 14
            }
        }
        
        # 保存原始值
        original_timeout = config_manager.get('api.timeout')
        original_batch_size = config_manager.get('processing.batch_size')
        
        # 合并配置
        config_manager._merge_config(config_manager._config, user_config)
        
        # 验证合并结果
        self.assertEqual(config_manager.get('api.timeout'), 90)  # 被覆盖
        self.assertEqual(config_manager.get('api.new_setting'), 'added_value')  # 新增
        self.assertEqual(config_manager.get('output.font_size'), 14)  # 新增
        self.assertEqual(config_manager.get('processing.batch_size'), original_batch_size)  # 保持不变
    
    def test_config_property(self):
        """测试配置属性"""
        config_manager = ConfigManager()
        
        # 获取完整配置
        full_config = config_manager.config
        
        # 验证是副本（只读）
        self.assertIsInstance(full_config, dict)
        self.assertIn('api', full_config)
        self.assertIn('processing', full_config)
        
        # 修改返回的字典不应影响原始配置
        original_timeout = config_manager.get('api.timeout')
        full_config['api']['timeout'] = 999
        self.assertEqual(config_manager.get('api.timeout'), original_timeout)
    
    def test_try_load_default_config(self):
        """测试尝试加载默认配置"""
        # 创建默认配置文件
        default_config = {
            'api': {'timeout': 25},
            'logging': {'level': 'DEBUG'}
        }
        
        default_path = Path('config.yaml')
        try:
            with open(default_path, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f)
            
            config_manager = ConfigManager()
            
            # 验证默认配置已加载
            self.assertEqual(config_manager.get('api.timeout'), 25)
            self.assertEqual(config_manager.get('logging.level'), 'DEBUG')
            
        finally:
            # 清理测试文件
            if default_path.exists():
                default_path.unlink()
    
    def test_invalid_config_file(self):
        """测试无效配置文件处理"""
        # 创建无效YAML文件
        with open(self.temp_config_path, 'w', encoding='utf-8') as f:
            f.write('invalid: yaml: content: [')
        
        # 应该不抛出异常，而是使用默认配置
        config_manager = ConfigManager(str(self.temp_config_path))
        self.assertTrue(config_manager.validate_config())
    
    def test_env_type_conversion(self):
        """测试环境变量类型转换"""
        os.environ['VOCAB_API_TIMEOUT'] = '45'
        os.environ['VOCAB_MAX_FILE_SIZE'] = '75'
        
        config_manager = ConfigManager()
        
        # 验证类型转换
        self.assertEqual(config_manager.get('api.timeout'), 45)  # int
        self.assertEqual(config_manager.get('processing.max_file_size_mb'), 75)  # int
    
    def test_env_invalid_type_conversion(self):
        """测试无效类型转换处理"""
        os.environ['VOCAB_API_TIMEOUT'] = 'invalid_number'
        
        config_manager = ConfigManager()
        
        # 应该保持原始值或使用默认值
        self.assertEqual(config_manager.get('api.timeout'), 30)  # 默认值


if __name__ == '__main__':
    unittest.main()