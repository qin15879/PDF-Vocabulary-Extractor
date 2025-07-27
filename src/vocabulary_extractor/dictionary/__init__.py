"""
词典服务模块

提供词典查询、缓存管理和服务降级功能
"""

from .service import (
    BaseDictionaryService,
    EasyPronunciationService, 
    LocalDictionaryService,
    DictionaryServiceError,
    HTTPClientError,
    APIAuthenticationError,
    RateLimitError
)

from .cache import (
    DictionaryCache,
    MemoryCache,
    PersistentCache,
    CacheEntry
)

from .manager import (
    DictionaryServiceManager,
    ServicePriority,
    ServiceStatus
)

__all__ = [
    # Service classes
    'BaseDictionaryService',
    'EasyPronunciationService',
    'LocalDictionaryService',
    
    # Exception classes
    'DictionaryServiceError',
    'HTTPClientError', 
    'APIAuthenticationError',
    'RateLimitError',
    
    # Cache classes
    'DictionaryCache',
    'MemoryCache',
    'PersistentCache',
    'CacheEntry',
    
    # Manager classes
    'DictionaryServiceManager',
    'ServicePriority',
    'ServiceStatus'
]