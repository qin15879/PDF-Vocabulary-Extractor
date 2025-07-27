"""
词典服务实现

提供基础的词典查询功能，包括HTTP客户端、API认证和错误处理
"""

import time
import logging
import requests
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
import json
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..core.interfaces import DictionaryServiceInterface
from ..core.models import WordInfo, APIResponse


class DictionaryServiceError(Exception):
    """词典服务相关错误"""
    pass


class HTTPClientError(DictionaryServiceError):
    """HTTP客户端错误"""
    pass


class APIAuthenticationError(DictionaryServiceError):
    """API认证错误"""
    pass


class RateLimitError(DictionaryServiceError):
    """API速率限制错误"""
    pass


class BaseDictionaryService(DictionaryServiceInterface):
    """词典服务基类
    
    提供通用的HTTP客户端功能、错误处理和重试机制
    """
    
    def __init__(self, 
                 base_url: str,
                 api_key: Optional[str] = None,
                 timeout: int = 10,
                 max_retries: int = 3,
                 retry_delay: float = 1.0,
                 max_workers: int = 5):
        """初始化词典服务
        
        Args:
            base_url: API基础URL
            api_key: API密钥
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            max_workers: 并发请求的最大线程数
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.max_workers = max_workers
        self.logger = logging.getLogger(__name__)
        
        # 创建会话对象
        self.session = requests.Session()
        self._setup_session()
        
        # 缓存
        self._cache = {}
        self._cache_enabled = True
        
    def _setup_session(self):
        """设置HTTP会话"""
        # 设置默认请求头
        self.session.headers.update({
            'User-Agent': 'VocabularyExtractor/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        # 设置API认证
        if self.api_key:
            self._setup_authentication()
    
    def _setup_authentication(self):
        """设置API认证"""
        # 默认使用Header认证，子类可以重写
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}'
        })
    
    def _make_request(self, 
                     method: str, 
                     endpoint: str, 
                     params: Optional[Dict] = None,
                     data: Optional[Dict] = None,
                     **kwargs) -> requests.Response:
        """发送HTTP请求
        
        Args:
            method: HTTP方法
            endpoint: API端点
            params: URL参数
            data: 请求数据
            **kwargs: 其他请求参数
            
        Returns:
            requests.Response: 响应对象
            
        Raises:
            HTTPClientError: HTTP请求错误
            APIAuthenticationError: 认证错误
            RateLimitError: 速率限制错误
        """
        url = urljoin(self.base_url + '/', endpoint.lstrip('/'))
        
        for attempt in range(self.max_retries + 1):
            try:
                self.logger.debug(f"发送{method}请求到{url}，尝试{attempt + 1}/{self.max_retries + 1}")
                
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data,
                    timeout=self.timeout,
                    **kwargs
                )
                
                # 检查响应状态
                if response.status_code == 401:
                    raise APIAuthenticationError("API认证失败，请检查API密钥")
                elif response.status_code == 429:
                    raise RateLimitError("API请求频率过高，请稍后重试")
                elif response.status_code >= 400:
                    raise HTTPClientError(f"HTTP请求失败: {response.status_code} - {response.text}")
                
                return response
                
            except (requests.exceptions.RequestException, HTTPClientError) as e:
                if attempt == self.max_retries:
                    raise HTTPClientError(f"HTTP请求失败（已重试{self.max_retries}次）: {str(e)}")
                
                # 等待后重试
                time.sleep(self.retry_delay * (attempt + 1))
                self.logger.warning(f"请求失败，{self.retry_delay * (attempt + 1)}秒后重试: {str(e)}")
    
    def _parse_response(self, response: requests.Response) -> Dict[str, Any]:
        """解析API响应
        
        Args:
            response: HTTP响应对象
            
        Returns:
            Dict[str, Any]: 解析后的响应数据
            
        Raises:
            DictionaryServiceError: 响应解析错误
        """
        try:
            return response.json()
        except json.JSONDecodeError as e:
            raise DictionaryServiceError(f"响应JSON解析失败: {str(e)}")
    
    def _get_from_cache(self, key: str) -> Optional[Any]:
        """从缓存获取数据"""
        if not self._cache_enabled:
            return None
        return self._cache.get(key)
    
    def _set_cache(self, key: str, value: Any):
        """设置缓存数据"""
        if self._cache_enabled:
            self._cache[key] = value
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
    
    def enable_cache(self, enabled: bool = True):
        """启用或禁用缓存"""
        self._cache_enabled = enabled
        if not enabled:
            self.clear_cache()
    
    # 抽象方法的默认实现，子类需要重写
    def get_definition(self, word: str) -> str:
        """获取单词的中文释义"""
        raise NotImplementedError("子类必须实现get_definition方法")
    
    def get_pronunciation(self, word: str) -> str:
        """获取单词的IPA音标"""
        raise NotImplementedError("子类必须实现get_pronunciation方法")
    
    def batch_lookup(self, words: List[str]) -> Dict[str, WordInfo]:
        """批量查询单词信息"""
        result = {}
        for word in words:
            try:
                definition = self.get_definition(word)
                pronunciation = self.get_pronunciation(word)
                
                result[word] = WordInfo(
                    word=word,
                    definition=definition,
                    pronunciation=pronunciation
                )
            except Exception as e:
                self.logger.warning(f"查询单词'{word}'失败: {str(e)}")
                # 创建空的WordInfo对象
                result[word] = WordInfo(
                    word=word,
                    definition="",
                    pronunciation=""
                )
        
        return result


class EasyPronunciationService(BaseDictionaryService):
    """EasyPronunciation API服务实现"""
    
    DEFAULT_BASE_URL = "https://api.easypronunciation.com"
    
    def __init__(self, api_key: str, **kwargs):
        """初始化EasyPronunciation服务
        
        Args:
            api_key: EasyPronunciation API密钥
            **kwargs: 其他配置参数
        """
        # 提取base_url以避免重复传递
        base_url = kwargs.pop('base_url', self.DEFAULT_BASE_URL)
        
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            **kwargs
        )
    
    def _setup_authentication(self):
        """设置EasyPronunciation API认证"""
        # EasyPronunciation可能使用不同的认证方式
        self.session.headers.update({
            'X-API-Key': self.api_key
        })
    
    def get_definition(self, word: str) -> str:
        """获取单词的中文释义
        
        Args:
            word: 要查询的单词
            
        Returns:
            str: 中文释义
        """
        if not word or not isinstance(word, str):
            return ""
        
        word = word.strip().lower()
        
        # 检查缓存
        cache_key = f"def_{word}"
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result
        
        try:
            response = self._make_request(
                method='GET',
                endpoint='/v1/definition',
                params={
                    'word': word,
                    'language': 'zh-CN'  # 中文释义
                }
            )
            
            data = self._parse_response(response)
            definition = self._extract_definition(data)
            
            # 缓存结果
            self._set_cache(cache_key, definition)
            
            return definition
            
        except Exception as e:
            self.logger.error(f"获取单词'{word}'释义失败: {str(e)}")
            return ""
    
    def get_pronunciation(self, word: str) -> str:
        """获取单词的IPA音标
        
        Args:
            word: 要查询的单词
            
        Returns:
            str: IPA音标
        """
        if not word or not isinstance(word, str):
            return ""
        
        word = word.strip().lower()
        
        # 检查缓存
        cache_key = f"pron_{word}"
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result
        
        try:
            response = self._make_request(
                method='GET',
                endpoint='/v1/pronunciation',
                params={
                    'word': word,
                    'format': 'ipa'  # IPA音标格式
                }
            )
            
            data = self._parse_response(response)
            pronunciation = self._extract_pronunciation(data)
            
            # 缓存结果
            self._set_cache(cache_key, pronunciation)
            
            return pronunciation
            
        except Exception as e:
            self.logger.error(f"获取单词'{word}'音标失败: {str(e)}")
            return ""
    
    def _extract_definition(self, data: Dict[str, Any]) -> str:
        """从API响应中提取释义"""
        # 根据EasyPronunciation API的实际响应格式调整
        if 'definition' in data:
            return data['definition']
        elif 'definitions' in data and data['definitions']:
            # 如果有多个释义，取第一个
            return data['definitions'][0]
        elif 'meaning' in data:
            return data['meaning']
        else:
            return ""
    
    def _extract_pronunciation(self, data: Dict[str, Any]) -> str:
        """从API响应中提取音标"""
        # 根据EasyPronunciation API的实际响应格式调整
        if 'ipa' in data:
            return data['ipa']
        elif 'pronunciation' in data:
            return data['pronunciation']
        elif 'phonetic' in data:
            return data['phonetic']
        else:
            return ""
    
    def batch_lookup(self, words: List[str]) -> Dict[str, WordInfo]:
        """批量查询单词信息
        
        Args:
            words: 要查询的单词列表
            
        Returns:
            Dict[str, WordInfo]: 单词信息字典
        """
        if not words:
            return {}
        
        result = {}
        
        # 检查是否支持批量查询API
        if hasattr(self, '_batch_lookup_api'):
            return self._batch_lookup_api(words)
        
        # 使用并发查询优化性能
        return self._concurrent_batch_lookup(words)
    
    def _concurrent_batch_lookup(self, words: List[str]) -> Dict[str, WordInfo]:
        """使用并发查询优化批量查询性能
        
        Args:
            words: 要查询的单词列表
            
        Returns:
            Dict[str, WordInfo]: 单词信息字典
        """
        if not words:
            return {}
        
        result = {}
        
        # 使用线程池并发查询
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有查询任务
            future_to_word = {}
            for word in words:
                # 检查缓存
                cache_key = f"batch_{word}"
                cached_result = self._get_from_cache(cache_key)
                if cached_result is not None:
                    result[word] = cached_result
                else:
                    # 提交并发任务
                    future = executor.submit(self._lookup_single_word, word)
                    future_to_word[future] = word
            
            # 收集结果
            for future in as_completed(future_to_word):
                word = future_to_word[future]
                try:
                    word_info = future.result()
                    result[word] = word_info
                    
                    # 缓存结果
                    cache_key = f"batch_{word}"
                    self._set_cache(cache_key, word_info)
                    
                except Exception as e:
                    self.logger.warning(f"查询单词'{word}'失败: {str(e)}")
                    result[word] = WordInfo(
                        word=word,
                        definition="",
                        pronunciation=""
                    )
        
        return result
    
    def _lookup_single_word(self, word: str) -> WordInfo:
        """查询单个单词的信息
        
        Args:
            word: 要查询的单词
            
        Returns:
            WordInfo: 单词信息
        """
        try:
            definition = self.get_definition(word)
            pronunciation = self.get_pronunciation(word)
            
            return WordInfo(
                word=word,
                definition=definition,
                pronunciation=pronunciation
            )
        except Exception as e:
            self.logger.warning(f"查询单词'{word}'失败: {str(e)}")
            return WordInfo(
                word=word,
                definition="",
                pronunciation=""
            )


class LocalDictionaryService(BaseDictionaryService):
    """本地词典服务（备用数据源）"""
    
    def __init__(self, dictionary_file: Optional[str] = None):
        """初始化本地词典服务
        
        Args:
            dictionary_file: 本地词典文件路径
        """
        # 不需要网络请求，所以不调用父类初始化
        self.dictionary_file = dictionary_file
        self.logger = logging.getLogger(__name__)
        self._local_dict = {}
        self._load_local_dictionary()
    
    def _load_local_dictionary(self):
        """加载本地词典数据"""
        if self.dictionary_file:
            try:
                with open(self.dictionary_file, 'r', encoding='utf-8') as f:
                    self._local_dict = json.load(f)
                self.logger.info(f"加载本地词典: {len(self._local_dict)}个词条")
            except Exception as e:
                self.logger.warning(f"加载本地词典失败: {str(e)}")
        
        # 如果没有本地词典文件，使用内置的基础词典
        if not self._local_dict:
            self._load_builtin_dictionary()
    
    def _load_builtin_dictionary(self):
        """加载内置基础词典"""
        # 这里可以添加一些常用单词的基础释义
        self._local_dict = {
            'hello': {'definition': '你好', 'pronunciation': '/həˈloʊ/'},
            'world': {'definition': '世界', 'pronunciation': '/wɜːrld/'},
            'computer': {'definition': '计算机', 'pronunciation': '/kəmˈpjuːtər/'},
            'program': {'definition': '程序', 'pronunciation': '/ˈproʊɡræm/'},
            'language': {'definition': '语言', 'pronunciation': '/ˈlæŋɡwɪdʒ/'},
            # 可以继续添加更多基础词汇
        }
        self.logger.info(f"使用内置词典: {len(self._local_dict)}个词条")
    
    def get_definition(self, word: str) -> str:
        """获取单词的中文释义"""
        if not word:
            return ""
        
        word = word.strip().lower()
        word_info = self._local_dict.get(word, {})
        return word_info.get('definition', '')
    
    def get_pronunciation(self, word: str) -> str:
        """获取单词的IPA音标"""
        if not word:
            return ""
        
        word = word.strip().lower()
        word_info = self._local_dict.get(word, {})
        return word_info.get('pronunciation', '')
    
    def batch_lookup(self, words: List[str]) -> Dict[str, WordInfo]:
        """批量查询单词信息"""
        result = {}
        for word in words:
            definition = self.get_definition(word)
            pronunciation = self.get_pronunciation(word)
            
            result[word] = WordInfo(
                word=word,
                definition=definition,
                pronunciation=pronunciation
            )
        
        return result