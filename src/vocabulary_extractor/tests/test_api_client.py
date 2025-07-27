"""
API客户端基础功能测试

专门测试任务4.1中实现的基础API客户端功能：
- DictionaryService基类和HTTP客户端
- API认证和请求头设置
- 网络错误处理和重试机制
- API响应解析功能
"""

import unittest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

import requests
from vocabulary_extractor.dictionary.service import (
    BaseDictionaryService, 
    EasyPronunciationService,
    LocalDictionaryService,
    DictionaryServiceError,
    HTTPClientError,
    APIAuthenticationError,
    RateLimitError
)
from vocabulary_extractor.core.models import WordInfo


class TestBaseDictionaryService(unittest.TestCase):
    """测试基础词典服务API客户端功能"""
    
    def setUp(self):
        """测试准备"""
        self.base_url = "https://api.example.com"
        self.api_key = "test_api_key"
        self.service = BaseDictionaryService(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=5,
            max_retries=2,
            retry_delay=0.1
        )
    
    def test_initialization(self):
        """测试服务初始化"""
        # 检查基本配置
        self.assertEqual(self.service.base_url, self.base_url)
        self.assertEqual(self.service.api_key, self.api_key)
        self.assertEqual(self.service.timeout, 5)
        self.assertEqual(self.service.max_retries, 2)
        self.assertEqual(self.service.retry_delay, 0.1)
        
        # 检查会话设置
        self.assertIsInstance(self.service.session, requests.Session)
        self.assertIn('User-Agent', self.service.session.headers)
        self.assertEqual(self.service.session.headers['Accept'], 'application/json')
        self.assertEqual(self.service.session.headers['Authorization'], f'Bearer {self.api_key}')
    
    def test_setup_session(self):
        """测试HTTP会话设置"""
        # 检查默认请求头
        headers = self.service.session.headers
        self.assertEqual(headers['User-Agent'], 'VocabularyExtractor/1.0')
        self.assertEqual(headers['Accept'], 'application/json')
        self.assertEqual(headers['Content-Type'], 'application/json')
    
    def test_setup_authentication(self):
        """测试API认证设置"""
        # 默认Bearer认证
        self.assertEqual(
            self.service.session.headers['Authorization'], 
            f'Bearer {self.api_key}'
        )
        
        # 测试无API密钥的情况
        service_no_key = BaseDictionaryService(base_url=self.base_url)
        self.assertNotIn('Authorization', service_no_key.session.headers)
    
    @patch('requests.Session.request')
    def test_make_request_success(self, mock_request):
        """测试成功的HTTP请求"""
        # 模拟成功响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_request.return_value = mock_response
        
        response = self.service._make_request('GET', '/test')
        
        # 验证请求调用
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        self.assertEqual(call_args[1]['method'], 'GET')
        self.assertEqual(call_args[1]['url'], f'{self.base_url}/test')
        self.assertEqual(call_args[1]['timeout'], 5)
        
        # 验证响应
        self.assertEqual(response.status_code, 200)
    
    @patch('requests.Session.request')
    def test_make_request_with_params(self, mock_request):
        """测试带参数的HTTP请求"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        
        params = {'word': 'test', 'lang': 'en'}
        data = {'action': 'lookup'}
        
        self.service._make_request('POST', '/search', params=params, data=data)
        
        call_args = mock_request.call_args
        self.assertEqual(call_args[1]['params'], params)
        self.assertEqual(call_args[1]['json'], data)
    
    @patch('requests.Session.request')
    def test_authentication_error_handling(self, mock_request):
        """测试认证错误处理"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_request.return_value = mock_response
        
        with self.assertRaises(APIAuthenticationError) as context:
            self.service._make_request('GET', '/test')
        
        self.assertIn("API认证失败", str(context.exception))
    
    @patch('requests.Session.request')
    def test_rate_limit_error_handling(self, mock_request):
        """测试速率限制错误处理"""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.text = "Too Many Requests"
        mock_request.return_value = mock_response
        
        with self.assertRaises(RateLimitError) as context:
            self.service._make_request('GET', '/test')
        
        self.assertIn("API请求频率过高", str(context.exception))
    
    @patch('requests.Session.request')
    def test_http_error_handling(self, mock_request):
        """测试HTTP错误处理"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_request.return_value = mock_response
        
        with self.assertRaises(HTTPClientError) as context:
            self.service._make_request('GET', '/test')
        
        self.assertIn("HTTP请求失败: 500", str(context.exception))
    
    @patch('requests.Session.request')
    def test_retry_mechanism(self, mock_request):
        """测试重试机制"""
        # 前两次失败，第三次成功
        side_effects = [
            requests.exceptions.ConnectionError("Connection failed"),
            requests.exceptions.Timeout("Request timeout"),
            Mock(status_code=200)
        ]
        mock_request.side_effect = side_effects
        
        start_time = time.time()
        response = self.service._make_request('GET', '/test')
        end_time = time.time()
        
        # 验证重试次数
        self.assertEqual(mock_request.call_count, 3)
        
        # 验证重试延迟（应该有延迟时间）
        self.assertGreater(end_time - start_time, 0.2)  # 至少0.1 + 0.2 = 0.3秒延迟
        
        # 验证最终成功
        self.assertEqual(response.status_code, 200)
    
    @patch('requests.Session.request')
    def test_retry_exhaustion(self, mock_request):
        """测试重试耗尽"""
        # 所有尝试都失败
        mock_request.side_effect = requests.exceptions.ConnectionError("Connection failed")
        
        with self.assertRaises(HTTPClientError) as context:
            self.service._make_request('GET', '/test')
        
        # 验证重试次数
        self.assertEqual(mock_request.call_count, 3)  # max_retries + 1
        self.assertIn("已重试2次", str(context.exception))
    
    def test_parse_response_success(self):
        """测试成功的响应解析"""
        mock_response = Mock()
        test_data = {"word": "test", "definition": "测试"}
        mock_response.json.return_value = test_data
        
        result = self.service._parse_response(mock_response)
        self.assertEqual(result, test_data)
    
    def test_parse_response_json_error(self):
        """测试JSON解析错误"""
        mock_response = Mock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        
        with self.assertRaises(DictionaryServiceError) as context:
            self.service._parse_response(mock_response)
        
        self.assertIn("响应JSON解析失败", str(context.exception))
    
    def test_cache_operations(self):
        """测试缓存操作"""
        # 设置缓存
        self.service._set_cache("test_key", "test_value")
        
        # 获取缓存
        cached_value = self.service._get_from_cache("test_key")
        self.assertEqual(cached_value, "test_value")
        
        # 不存在的键
        self.assertIsNone(self.service._get_from_cache("nonexistent"))
        
        # 清空缓存
        self.service.clear_cache()
        self.assertIsNone(self.service._get_from_cache("test_key"))
    
    def test_cache_enable_disable(self):
        """测试缓存启用/禁用"""
        # 设置缓存
        self.service._set_cache("test_key", "test_value")
        self.assertEqual(self.service._get_from_cache("test_key"), "test_value")
        
        # 禁用缓存
        self.service.enable_cache(False)
        self.assertIsNone(self.service._get_from_cache("test_key"))
        
        # 重新启用缓存
        self.service.enable_cache(True)
        self.assertIsNone(self.service._get_from_cache("test_key"))  # 缓存已清空
    
    def test_abstract_methods(self):
        """测试抽象方法"""
        # 基类的抽象方法应该抛出NotImplementedError
        with self.assertRaises(NotImplementedError):
            self.service.get_definition("test")
        
        with self.assertRaises(NotImplementedError):
            self.service.get_pronunciation("test")


class TestEasyPronunciationService(unittest.TestCase):
    """测试EasyPronunciation服务的API客户端功能"""
    
    def setUp(self):
        """测试准备"""
        self.api_key = "test_api_key"
        self.service = EasyPronunciationService(self.api_key)
    
    def test_initialization(self):
        """测试服务初始化"""
        self.assertEqual(self.service.api_key, self.api_key)
        self.assertEqual(self.service.base_url, EasyPronunciationService.DEFAULT_BASE_URL)
        
        # 检查特定的认证头
        self.assertEqual(self.service.session.headers['X-API-Key'], self.api_key)
        self.assertNotIn('Authorization', self.service.session.headers)
    
    def test_custom_base_url(self):
        """测试自定义基础URL"""
        custom_url = "https://custom.api.com"
        service = EasyPronunciationService(self.api_key, base_url=custom_url)
        self.assertEqual(service.base_url, custom_url)
    
    @patch('vocabulary_extractor.dictionary.service.BaseDictionaryService._make_request')
    def test_get_definition_success(self, mock_request):
        """测试成功获取释义"""
        # 模拟API响应
        mock_response = Mock()
        mock_response.json.return_value = {"definition": "测试定义"}
        mock_request.return_value = mock_response
        
        result = self.service.get_definition("test")
        
        # 验证请求参数
        mock_request.assert_called_once_with(
            method='GET',
            endpoint='/v1/definition',
            params={'word': 'test', 'language': 'zh-CN'}
        )
        
        # 验证结果
        self.assertEqual(result, "测试定义")
    
    @patch('vocabulary_extractor.dictionary.service.BaseDictionaryService._make_request')
    def test_get_pronunciation_success(self, mock_request):
        """测试成功获取音标"""
        # 模拟API响应
        mock_response = Mock()
        mock_response.json.return_value = {"ipa": "/test/"}
        mock_request.return_value = mock_response
        
        result = self.service.get_pronunciation("test")
        
        # 验证请求参数
        mock_request.assert_called_once_with(
            method='GET',
            endpoint='/v1/pronunciation',
            params={'word': 'test', 'format': 'ipa'}
        )
        
        # 验证结果
        self.assertEqual(result, "/test/")
    
    def test_extract_definition_various_formats(self):
        """测试从不同格式的响应中提取释义"""
        test_cases = [
            ({"definition": "测试"}, "测试"),
            ({"definitions": ["测试1", "测试2"]}, "测试1"),
            ({"meaning": "含义"}, "含义"),
            ({"other": "其他"}, ""),
            ({}, ""),
        ]
        
        for data, expected in test_cases:
            with self.subTest(data=data):
                result = self.service._extract_definition(data)
                self.assertEqual(result, expected)
    
    def test_extract_pronunciation_various_formats(self):
        """测试从不同格式的响应中提取音标"""
        test_cases = [
            ({"ipa": "/test/"}, "/test/"),
            ({"pronunciation": "/pron/"}, "/pron/"),
            ({"phonetic": "/phon/"}, "/phon/"),
            ({"other": "其他"}, ""),
            ({}, ""),
        ]
        
        for data, expected in test_cases:
            with self.subTest(data=data):
                result = self.service._extract_pronunciation(data)
                self.assertEqual(result, expected)
    
    @patch('vocabulary_extractor.dictionary.service.BaseDictionaryService._make_request')
    def test_api_error_handling(self, mock_request):
        """测试API错误处理"""
        # 模拟API错误
        mock_request.side_effect = HTTPClientError("API错误")
        
        result = self.service.get_definition("test")
        self.assertEqual(result, "")
        
        result = self.service.get_pronunciation("test")
        self.assertEqual(result, "")
    
    def test_invalid_input_handling(self):
        """测试无效输入处理"""
        # 空输入
        self.assertEqual(self.service.get_definition(""), "")
        self.assertEqual(self.service.get_definition(None), "")
        
        # 非字符串输入
        self.assertEqual(self.service.get_definition(123), "")
        self.assertEqual(self.service.get_pronunciation([]), "")
    
    @patch('vocabulary_extractor.dictionary.service.BaseDictionaryService._make_request')
    @patch('time.sleep')
    def test_batch_lookup_with_delay(self, mock_sleep, mock_request):
        """测试带延迟的批量查询"""
        # 模拟成功响应
        mock_response = Mock()
        mock_request.return_value = mock_response
        
        # 第一次调用返回释义响应，第二次返回音标响应
        mock_response.json.side_effect = [
            {"definition": "测试1"},
            {"ipa": "/test1/"},
            {"definition": "测试2"}, 
            {"ipa": "/test2/"}
        ]
        
        words = ["test1", "test2"]
        results = self.service.batch_lookup(words)
        
        # 验证结果
        self.assertEqual(len(results), 2)
        self.assertEqual(results["test1"].definition, "测试1")
        self.assertEqual(results["test1"].pronunciation, "/test1/")
        self.assertEqual(results["test2"].definition, "测试2")
        
        # 验证延迟调用（只在中间调用，不在最后）
        mock_sleep.assert_called_once_with(0.1)
    
    @patch('vocabulary_extractor.dictionary.service.BaseDictionaryService._make_request')
    def test_batch_lookup_error_handling(self, mock_request):
        """测试批量查询中的错误处理"""
        # 第一个单词成功，第二个单词失败
        side_effects = [
            Mock(json=lambda: {"definition": "成功"}),
            Mock(json=lambda: {"ipa": "/success/"}),
            HTTPClientError("API错误"),
        ]
        mock_request.side_effect = side_effects
        
        words = ["success", "failed"]
        results = self.service.batch_lookup(words)
        
        # 验证结果
        self.assertEqual(len(results), 2)
        self.assertEqual(results["success"].definition, "成功")
        self.assertEqual(results["failed"].definition, "")
        self.assertEqual(results["failed"].pronunciation, "")
    
    def test_cache_integration(self):
        """测试缓存集成"""
        # 手动设置缓存
        self.service._set_cache("def_test", "缓存的释义")
        self.service._set_cache("pron_test", "/cached/")
        
        # 应该返回缓存结果，不发起网络请求
        with patch.object(self.service, '_make_request') as mock_request:
            definition = self.service.get_definition("test")
            pronunciation = self.service.get_pronunciation("test")
            
            self.assertEqual(definition, "缓存的释义")
            self.assertEqual(pronunciation, "/cached/")
            mock_request.assert_not_called()


class TestLocalDictionaryService(unittest.TestCase):
    """测试本地词典服务"""
    
    def setUp(self):
        """测试准备"""
        self.service = LocalDictionaryService()
    
    def test_initialization(self):
        """测试初始化"""
        # 检查内置词典是否加载
        self.assertGreater(len(self.service._local_dict), 0)
        
        # 检查基础单词是否存在
        self.assertIn('hello', self.service._local_dict)
        self.assertIn('world', self.service._local_dict)
    
    def test_builtin_dictionary_content(self):
        """测试内置词典内容"""
        test_words = ['hello', 'world', 'computer', 'program', 'language']
        
        for word in test_words:
            with self.subTest(word=word):
                self.assertIn(word, self.service._local_dict)
                word_info = self.service._local_dict[word]
                self.assertIn('definition', word_info)
                self.assertIn('pronunciation', word_info)
                self.assertIsInstance(word_info['definition'], str)
                self.assertIsInstance(word_info['pronunciation'], str)
    
    def test_get_definition(self):
        """测试获取释义"""
        # 存在的单词
        definition = self.service.get_definition("hello")
        self.assertEqual(definition, "你好")
        
        # 不存在的单词
        definition = self.service.get_definition("nonexistent")
        self.assertEqual(definition, "")
        
        # 空输入
        definition = self.service.get_definition("")
        self.assertEqual(definition, "")
    
    def test_get_pronunciation(self):
        """测试获取音标"""
        # 存在的单词
        pronunciation = self.service.get_pronunciation("hello")
        self.assertEqual(pronunciation, "/həˈloʊ/")
        
        # 不存在的单词
        pronunciation = self.service.get_pronunciation("nonexistent")
        self.assertEqual(pronunciation, "")
    
    def test_batch_lookup(self):
        """测试批量查询"""
        words = ["hello", "world", "nonexistent"]
        results = self.service.batch_lookup(words)
        
        self.assertEqual(len(results), 3)
        
        # 检查存在的单词
        self.assertEqual(results["hello"].word, "hello")
        self.assertEqual(results["hello"].definition, "你好")
        self.assertEqual(results["hello"].pronunciation, "/həˈloʊ/")
        
        # 检查不存在的单词
        self.assertEqual(results["nonexistent"].word, "nonexistent")
        self.assertEqual(results["nonexistent"].definition, "")
        self.assertEqual(results["nonexistent"].pronunciation, "")
    
    def test_case_insensitive_lookup(self):
        """测试大小写不敏感查询"""
        # 大写查询
        definition = self.service.get_definition("HELLO")
        self.assertEqual(definition, "你好")
        
        # 混合大小写查询
        pronunciation = self.service.get_pronunciation("HeLLo")
        self.assertEqual(pronunciation, "/həˈloʊ/")


if __name__ == '__main__':
    unittest.main()