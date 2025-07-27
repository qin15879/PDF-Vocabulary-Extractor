"""
词典服务管理器

提供统一的词典查询接口，支持多个服务源和自动降级
"""

import time
import logging
from typing import Dict, List, Optional, Any, Type
from enum import Enum

from ..core.interfaces import DictionaryServiceInterface
from ..core.models import WordInfo
from .service import EasyPronunciationService, LocalDictionaryService
from .cache import DictionaryCache


class ServicePriority(Enum):
    """服务优先级"""
    PRIMARY = 1
    SECONDARY = 2
    FALLBACK = 3


class ServiceStatus(Enum):
    """服务状态"""
    ACTIVE = "active"
    DEGRADED = "degraded"
    FAILED = "failed"
    DISABLED = "disabled"


class DictionaryServiceManager:
    """词典服务管理器
    
    管理多个词典服务，提供自动降级和负载均衡功能
    """
    
    def __init__(self, cache_enabled: bool = True):
        """初始化服务管理器
        
        Args:
            cache_enabled: 是否启用缓存
        """
        self.logger = logging.getLogger(__name__)
        self.cache_enabled = cache_enabled
        
        # 初始化缓存
        if cache_enabled:
            self.cache = DictionaryCache()
        else:
            self.cache = None
        
        # 服务注册表
        self.services: Dict[str, Dict[str, Any]] = {}
        
        # 服务统计
        self.stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'service_calls': {},
            'service_failures': {},
            'last_cleanup': time.time()
        }
        
        # 默认配置
        self.config = {
            'max_retries': 3,
            'retry_delay': 1.0,
            'service_timeout': 10.0,
            'failure_threshold': 5,  # 连续失败次数阈值
            'recovery_time': 300,    # 服务恢复检查时间（秒）
        }
    
    def register_service(self, 
                        name: str, 
                        service: DictionaryServiceInterface,
                        priority: ServicePriority = ServicePriority.SECONDARY,
                        enabled: bool = True) -> None:
        """注册词典服务
        
        Args:
            name: 服务名称
            service: 服务实例
            priority: 服务优先级
            enabled: 是否启用
        """
        self.services[name] = {
            'service': service,
            'priority': priority,
            'status': ServiceStatus.ACTIVE if enabled else ServiceStatus.DISABLED,
            'failure_count': 0,
            'last_failure': None,
            'last_success': time.time(),
            'total_calls': 0,
            'successful_calls': 0
        }
        
        # 初始化统计
        self.stats['service_calls'][name] = 0
        self.stats['service_failures'][name] = 0
        
        self.logger.info(f"注册词典服务: {name} (优先级: {priority.name})")
    
    def setup_default_services(self, easy_pronunciation_api_key: Optional[str] = None):
        """设置默认服务
        
        Args:
            easy_pronunciation_api_key: EasyPronunciation API密钥
        """
        # 注册本地词典服务（最高优先级，作为备用）
        local_service = LocalDictionaryService()
        self.register_service("local", local_service, ServicePriority.FALLBACK)
        
        # 注册EasyPronunciation服务（如果提供了API密钥）
        if easy_pronunciation_api_key:
            try:
                easy_service = EasyPronunciationService(easy_pronunciation_api_key)
                self.register_service("easypronunciation", easy_service, ServicePriority.PRIMARY)
            except Exception as e:
                self.logger.warning(f"EasyPronunciation服务初始化失败: {str(e)}")
    
    def get_definition(self, word: str) -> str:
        """获取单词释义
        
        Args:
            word: 要查询的单词
            
        Returns:
            str: 中文释义
        """
        if not word:
            return ""
        
        self.stats['total_requests'] += 1
        
        # 检查缓存
        if self.cache_enabled and self.cache:
            cached_result = self.cache.get_definition(word)
            if cached_result is not None:
                self.stats['cache_hits'] += 1
                return cached_result
        
        # 按优先级尝试服务
        for service_name in self._get_services_by_priority():
            service_info = self.services[service_name]
            
            if not self._is_service_available(service_name):
                continue
            
            try:
                result = service_info['service'].get_definition(word)
                
                # 记录成功调用
                self._record_success(service_name)
                
                # 缓存结果
                if self.cache_enabled and self.cache and result:
                    self.cache.set_definition(word, result)
                
                return result
                
            except Exception as e:
                self._record_failure(service_name, e)
                continue
        
        self.logger.warning(f"所有服务都无法获取单词'{word}'的释义")
        return ""
    
    def get_pronunciation(self, word: str) -> str:
        """获取单词音标
        
        Args:
            word: 要查询的单词
            
        Returns:
            str: IPA音标
        """
        if not word:
            return ""
        
        self.stats['total_requests'] += 1
        
        # 检查缓存
        if self.cache_enabled and self.cache:
            cached_result = self.cache.get_pronunciation(word)
            if cached_result is not None:
                self.stats['cache_hits'] += 1
                return cached_result
        
        # 按优先级尝试服务
        for service_name in self._get_services_by_priority():
            service_info = self.services[service_name]
            
            if not self._is_service_available(service_name):
                continue
            
            try:
                result = service_info['service'].get_pronunciation(word)
                
                # 记录成功调用
                self._record_success(service_name)
                
                # 缓存结果
                if self.cache_enabled and self.cache and result:
                    self.cache.set_pronunciation(word, result)
                
                return result
                
            except Exception as e:
                self._record_failure(service_name, e)
                continue
        
        self.logger.warning(f"所有服务都无法获取单词'{word}'的音标")
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
        uncached_words = []
        
        # 检查缓存
        if self.cache_enabled and self.cache:
            for word in words:
                cached_info = self.cache.get_word_info(word)
                if cached_info:
                    definition, pronunciation = cached_info
                    result[word] = WordInfo(
                        word=word,
                        definition=definition,
                        pronunciation=pronunciation
                    )
                    self.stats['cache_hits'] += 1
                else:
                    uncached_words.append(word)
        else:
            uncached_words = words
        
        # 查询未缓存的单词
        if uncached_words:
            # 尝试使用支持批量查询的服务
            for service_name in self._get_services_by_priority():
                service_info = self.services[service_name]
                
                if not self._is_service_available(service_name):
                    continue
                
                try:
                    batch_result = service_info['service'].batch_lookup(uncached_words)
                    
                    # 处理批量查询结果
                    for word, word_info in batch_result.items():
                        if word_info.definition or word_info.pronunciation:
                            result[word] = word_info
                            
                            # 缓存结果
                            if self.cache_enabled and self.cache:
                                self.cache.set_word_info(
                                    word, 
                                    word_info.definition, 
                                    word_info.pronunciation
                                )
                    
                    # 记录成功调用
                    self._record_success(service_name)
                    break
                    
                except Exception as e:
                    self._record_failure(service_name, e)
                    continue
        
        # 确保所有单词都有结果（即使是空的）
        for word in words:
            if word not in result:
                result[word] = WordInfo(
                    word=word,
                    definition="",
                    pronunciation="",
                    found_definition=False,
                    found_pronunciation=False
                )
        
        return result
    
    def _get_services_by_priority(self) -> List[str]:
        """按优先级获取服务列表"""
        # 按优先级排序服务
        sorted_services = sorted(
            self.services.items(),
            key=lambda x: x[1]['priority'].value
        )
        
        return [name for name, _ in sorted_services]
    
    def _is_service_available(self, service_name: str) -> bool:
        """检查服务是否可用"""
        if service_name not in self.services:
            return False
        
        service_info = self.services[service_name]
        status = service_info['status']
        
        # 禁用的服务不可用
        if status == ServiceStatus.DISABLED:
            return False
        
        # 失败的服务检查是否可以恢复
        if status == ServiceStatus.FAILED:
            if service_info['last_failure']:
                time_since_failure = time.time() - service_info['last_failure']
                if time_since_failure > self.config['recovery_time']:
                    # 尝试恢复服务
                    service_info['status'] = ServiceStatus.ACTIVE
                    service_info['failure_count'] = 0
                    self.logger.info(f"服务 {service_name} 尝试恢复")
                    return True
            return False
        
        return True
    
    def _record_success(self, service_name: str):
        """记录服务成功调用"""
        if service_name in self.services:
            service_info = self.services[service_name]
            service_info['successful_calls'] += 1
            service_info['total_calls'] += 1
            service_info['last_success'] = time.time()
            service_info['failure_count'] = 0  # 重置失败计数
            
            # 如果服务之前是降级状态，恢复为正常状态
            if service_info['status'] == ServiceStatus.DEGRADED:
                service_info['status'] = ServiceStatus.ACTIVE
                self.logger.info(f"服务 {service_name} 恢复正常")
        
        self.stats['service_calls'][service_name] = self.stats['service_calls'].get(service_name, 0) + 1
    
    def _record_failure(self, service_name: str, error: Exception):
        """记录服务失败"""
        if service_name in self.services:
            service_info = self.services[service_name]
            service_info['failure_count'] += 1
            service_info['total_calls'] += 1
            service_info['last_failure'] = time.time()
            
            # 根据失败次数调整服务状态
            if service_info['failure_count'] >= self.config['failure_threshold']:
                service_info['status'] = ServiceStatus.FAILED
                self.logger.warning(f"服务 {service_name} 标记为失败状态")
            elif service_info['failure_count'] >= self.config['failure_threshold'] // 2:
                service_info['status'] = ServiceStatus.DEGRADED
                self.logger.warning(f"服务 {service_name} 标记为降级状态")
        
        self.stats['service_failures'][service_name] = self.stats['service_failures'].get(service_name, 0) + 1
        self.logger.error(f"服务 {service_name} 调用失败: {str(error)}")
    
    def get_service_status(self) -> Dict[str, Any]:
        """获取所有服务状态"""
        status = {}
        for name, info in self.services.items():
            status[name] = {
                'status': info['status'].value,
                'priority': info['priority'].name,
                'failure_count': info['failure_count'],
                'total_calls': info['total_calls'],
                'successful_calls': info['successful_calls'],
                'success_rate': info['successful_calls'] / info['total_calls'] if info['total_calls'] > 0 else 0,
                'last_success': info['last_success'],
                'last_failure': info['last_failure']
            }
        
        return status
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        cache_stats = {}
        if self.cache_enabled and self.cache:
            cache_stats = self.cache.stats()
        
        return {
            'total_requests': self.stats['total_requests'],
            'cache_hits': self.stats['cache_hits'],
            'cache_hit_rate': self.stats['cache_hits'] / self.stats['total_requests'] if self.stats['total_requests'] > 0 else 0,
            'service_calls': self.stats['service_calls'],
            'service_failures': self.stats['service_failures'],
            'services': self.get_service_status(),
            'cache': cache_stats
        }
    
    def cleanup_cache(self) -> Dict[str, int]:
        """清理过期缓存"""
        if self.cache_enabled and self.cache:
            result = self.cache.cleanup_expired()
            self.stats['last_cleanup'] = time.time()
            return result
        return {'memory_cleaned': 0, 'persistent_cleaned': 0, 'total_cleaned': 0}
    
    def disable_service(self, service_name: str) -> bool:
        """禁用服务"""
        if service_name in self.services:
            self.services[service_name]['status'] = ServiceStatus.DISABLED
            self.logger.info(f"服务 {service_name} 已禁用")
            return True
        return False
    
    def enable_service(self, service_name: str) -> bool:
        """启用服务"""
        if service_name in self.services:
            self.services[service_name]['status'] = ServiceStatus.ACTIVE
            self.services[service_name]['failure_count'] = 0
            self.logger.info(f"服务 {service_name} 已启用")
            return True
        return False