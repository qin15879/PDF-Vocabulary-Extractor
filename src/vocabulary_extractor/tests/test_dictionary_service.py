"""
词典服务测试

测试词典查询、缓存和服务管理功能
"""

import unittest
import time
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from vocabulary_extractor.dictionary import (
    DictionaryServiceManager,
    EasyPronunciationService,
    LocalDictionaryService,
    DictionaryCache,
    MemoryCache,
    ServicePriority,
    ServiceStatus,
    DictionaryServiceError
)
from vocabulary_extractor.core.models import WordInfo


class TestMemoryCache(unittest.TestCase):
    """测试内存缓存功能"""
    
    def setUp(self):
        self.cache = MemoryCache(max_size=3, default_ttl=1.0)
    
    def test_basic_operations(self):
        """测试基本缓存操作"""
        # 设置和获取
        self.cache.set("key1", "value1")
        self.assertEqual(self.cache.get("key1"), "value1")
        
        # 不存在的键
        self.assertIsNone(self.cache.get("nonexistent"))
        
        # 删除
        self.assertTrue(self.cache.delete("key1"))
        self.assertIsNone(self.cache.get("key1"))
        self.assertFalse(self.cache.delete("key1"))
    
    def test_ttl_expiration(self):
        """测试TTL过期"""
        self.cache.set("key1", "value1", ttl=0.1)  # 100ms TTL
        self.assertEqual(self.cache.get("key1"), "value1")
        
        time.sleep(0.2)  # 等待过期
        self.assertIsNone(self.cache.get("key1"))
    
    def test_lru_eviction(self):
        """测试LRU淘汰"""
        # 填满缓存
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2") 
        self.cache.set("key3", "value3")
        
        # 访问key1使其成为最近使用
        self.cache.get("key1")
        
        # 添加新键，应该淘汰key2
        self.cache.set("key4", "value4")
        
        self.assertEqual(self.cache.get("key1"), "value1")
        self.assertIsNone(self.cache.get("key2"))
        self.assertEqual(self.cache.get("key3"), "value3")
        self.assertEqual(self.cache.get("key4"), "value4")
    
    def test_stats(self):
        """测试统计信息"""
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2", ttl=0.1)
        
        stats = self.cache.stats()
        self.assertEqual(stats['total_entries'], 2)
        self.assertEqual(stats['max_size'], 3)
        
        time.sleep(0.2)  # 等待key2过期
        stats = self.cache.stats()
        self.assertEqual(stats['expired_entries'], 1)


class TestDictionaryCache(unittest.TestCase):
    """测试词典缓存功能"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cache = DictionaryCache(
            memory_cache_size=10,
            memory_ttl=1.0,
            persistent_ttl=3600,
            cache_dir=self.temp_dir
        )
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_definition_cache(self):
        """测试释义缓存"""
        word = "test"
        definition = "测试"
        
        # 设置缓存
        self.cache.set_definition(word, definition)
        
        # 获取缓存
        cached_def = self.cache.get_definition(word)
        self.assertEqual(cached_def, definition)
        
        # 不存在的单词
        self.assertIsNone(self.cache.get_definition("nonexistent"))
    
    def test_pronunciation_cache(self):
        """测试音标缓存"""
        word = "test"
        pronunciation = "/test/"
        
        # 设置缓存
        self.cache.set_pronunciation(word, pronunciation)
        
        # 获取缓存
        cached_pron = self.cache.get_pronunciation(word)
        self.assertEqual(cached_pron, pronunciation)
    
    def test_word_info_cache(self):
        """测试完整单词信息缓存"""
        word = "test"
        definition = "测试"
        pronunciation = "/test/"
        
        # 设置完整信息
        self.cache.set_word_info(word, definition, pronunciation)
        
        # 获取完整信息
        cached_info = self.cache.get_word_info(word)
        self.assertIsNotNone(cached_info)
        self.assertEqual(cached_info[0], definition)
        self.assertEqual(cached_info[1], pronunciation)


class TestLocalDictionaryService(unittest.TestCase):
    """测试本地词典服务"""
    
    def setUp(self):
        self.service = LocalDictionaryService()
    
    def test_builtin_dictionary(self):
        """测试内置词典"""
        # 测试内置单词
        definition = self.service.get_definition("hello")
        self.assertEqual(definition, "你好")
        
        pronunciation = self.service.get_pronunciation("hello")
        self.assertEqual(pronunciation, "/həˈloʊ/")
        
        # 测试不存在的单词
        self.assertEqual(self.service.get_definition("nonexistent"), "")
        self.assertEqual(self.service.get_pronunciation("nonexistent"), "")
    
    def test_batch_lookup(self):
        """测试批量查询"""
        words = ["hello", "world", "nonexistent"]
        results = self.service.batch_lookup(words)
        
        self.assertEqual(len(results), 3)
        self.assertEqual(results["hello"].definition, "你好")
        self.assertEqual(results["world"].definition, "世界")
        self.assertEqual(results["nonexistent"].definition, "")


class TestEasyPronunciationService(unittest.TestCase):
    """测试EasyPronunciation服务"""
    
    def setUp(self):
        self.api_key = "test_api_key"
        self.service = EasyPronunciationService(self.api_key)
    
    @patch('requests.Session.request')
    def test_get_definition_success(self, mock_request):
        """测试成功获取释义"""
        # 模拟成功响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"definition": "测试"}
        mock_request.return_value = mock_response
        
        result = self.service.get_definition("test")
        self.assertEqual(result, "测试")
    
    @patch('requests.Session.request')
    def test_get_pronunciation_success(self, mock_request):
        """测试成功获取音标"""
        # 模拟成功响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ipa": "/test/"}
        mock_request.return_value = mock_response
        
        result = self.service.get_pronunciation("test")
        self.assertEqual(result, "/test/")
    
    @patch('requests.Session.request')
    def test_api_error_handling(self, mock_request):
        """测试API错误处理"""
        # 模拟API错误
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_request.return_value = mock_response
        
        result = self.service.get_definition("test")
        self.assertEqual(result, "")
    
    @patch('requests.Session.request')
    def test_authentication_error(self, mock_request):
        """测试认证错误"""
        # 模拟认证错误
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_request.return_value = mock_response
        
        result = self.service.get_definition("test")
        self.assertEqual(result, "")


class TestDictionaryServiceManager(unittest.TestCase):
    """测试词典服务管理器"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.manager = DictionaryServiceManager(cache_enabled=True)
        
        # 设置测试服务
        self.local_service = LocalDictionaryService()
        self.manager.register_service("local", self.local_service, ServicePriority.FALLBACK)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_service_registration(self):
        """测试服务注册"""
        # 检查服务是否已注册
        self.assertIn("local", self.manager.services)
        
        service_info = self.manager.services["local"]
        self.assertEqual(service_info['priority'], ServicePriority.FALLBACK)
        self.assertEqual(service_info['status'], ServiceStatus.ACTIVE)
    
    def test_get_definition(self):
        """测试获取释义"""
        definition = self.manager.get_definition("hello")
        self.assertEqual(definition, "你好")
        
        # 测试不存在的单词
        definition = self.manager.get_definition("nonexistent")
        self.assertEqual(definition, "")
    
    def test_get_pronunciation(self):
        """测试获取音标"""
        pronunciation = self.manager.get_pronunciation("hello")
        self.assertEqual(pronunciation, "/həˈloʊ/")
    
    def test_batch_lookup(self):
        """测试批量查询"""
        words = ["hello", "world"]
        results = self.manager.batch_lookup(words)
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results["hello"].definition, "你好")
        self.assertEqual(results["world"].definition, "世界")
    
    def test_cache_functionality(self):
        """测试缓存功能"""
        # 第一次查询
        definition1 = self.manager.get_definition("hello")
        
        # 第二次查询应该命中缓存
        definition2 = self.manager.get_definition("hello")
        
        self.assertEqual(definition1, definition2)
        
        # 检查缓存命中统计
        stats = self.manager.get_statistics()
        self.assertGreater(stats['cache_hits'], 0)
    
    def test_service_failure_handling(self):
        """测试服务失败处理"""
        # 创建一个会失败的模拟服务
        failing_service = Mock()
        failing_service.get_definition.side_effect = Exception("Service failed")
        
        self.manager.register_service("failing", failing_service, ServicePriority.PRIMARY)
        
        # 查询应该降级到本地服务
        definition = self.manager.get_definition("hello")
        self.assertEqual(definition, "你好")
        
        # 检查失败服务的状态
        status = self.manager.get_service_status()
        # 由于失败次数可能还没达到阈值，状态可能还是ACTIVE或DEGRADED
        self.assertIn(status["failing"]["status"], ["active", "degraded", "failed"])
    
    def test_service_priority(self):
        """测试服务优先级"""
        # 添加一个高优先级的模拟服务
        primary_service = Mock()
        primary_service.get_definition.return_value = "主要服务释义"
        
        self.manager.register_service("primary", primary_service, ServicePriority.PRIMARY)
        
        # 查询应该使用主要服务
        definition = self.manager.get_definition("test")
        self.assertEqual(definition, "主要服务释义")
        
        # 验证主要服务被调用
        primary_service.get_definition.assert_called_with("test")
    
    def test_statistics(self):
        """测试统计信息"""
        # 执行一些查询
        self.manager.get_definition("hello")
        self.manager.get_pronunciation("hello")
        
        stats = self.manager.get_statistics()
        
        # 检查基本统计
        self.assertGreater(stats['total_requests'], 0)
        self.assertIn('service_calls', stats)
        self.assertIn('services', stats)
        self.assertIn('cache', stats)
    
    def test_service_enable_disable(self):
        """测试服务启用/禁用"""
        # 禁用服务
        self.assertTrue(self.manager.disable_service("local"))
        
        # 检查状态
        status = self.manager.get_service_status()
        self.assertEqual(status["local"]["status"], "disabled")
        
        # 启用服务
        self.assertTrue(self.manager.enable_service("local"))
        
        # 检查状态
        status = self.manager.get_service_status()
        self.assertEqual(status["local"]["status"], "active")


if __name__ == '__main__':
    unittest.main()