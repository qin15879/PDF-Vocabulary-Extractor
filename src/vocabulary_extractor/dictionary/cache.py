"""
词典缓存管理系统

提供内存缓存和持久化缓存功能，优化API查询性能
"""

import json
import time
import pickle
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import logging
from threading import Lock


class CacheEntry:
    """缓存条目"""
    
    def __init__(self, data: Any, timestamp: float, ttl: Optional[float] = None):
        self.data = data
        self.timestamp = timestamp
        self.ttl = ttl  # Time to live in seconds
    
    def is_expired(self) -> bool:
        """检查缓存是否过期"""
        if self.ttl is None:
            return False
        return time.time() - self.timestamp > self.ttl
    
    def age(self) -> float:
        """获取缓存年龄（秒）"""
        return time.time() - self.timestamp


class MemoryCache:
    """内存缓存管理器"""
    
    def __init__(self, max_size: int = 10000, default_ttl: Optional[float] = 3600):
        """初始化内存缓存
        
        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认过期时间（秒），None表示永不过期
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: Dict[str, float] = {}  # LRU tracking
        self._lock = Lock()
        self.logger = logging.getLogger(__name__)
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存数据"""
        with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            
            # 检查是否过期
            if entry.is_expired():
                del self._cache[key]
                if key in self._access_order:
                    del self._access_order[key]
                return None
            
            # 更新访问时间
            self._access_order[key] = time.time()
            return entry.data
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """设置缓存数据"""
        with self._lock:
            # 使用默认TTL如果没有指定
            if ttl is None:
                ttl = self.default_ttl
            
            # 检查缓存大小限制
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_lru()
            
            # 添加新条目
            self._cache[key] = CacheEntry(value, time.time(), ttl)
            self._access_order[key] = time.time()
    
    def delete(self, key: str) -> bool:
        """删除缓存条目"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                if key in self._access_order:
                    del self._access_order[key]
                return True
            return False
    
    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
    
    def _evict_lru(self) -> None:
        """移除最近最少使用的条目"""
        if not self._access_order:
            return
        
        # 找到最旧的访问时间
        oldest_key = min(self._access_order.keys(), key=lambda k: self._access_order[k])
        
        # 删除最旧的条目
        if oldest_key in self._cache:
            del self._cache[oldest_key]
        del self._access_order[oldest_key]
    
    def cleanup_expired(self) -> int:
        """清理过期条目"""
        with self._lock:
            expired_keys = []
            for key, entry in self._cache.items():
                if entry.is_expired():
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
                if key in self._access_order:
                    del self._access_order[key]
            
            return len(expired_keys)
    
    def stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._lock:
            total_entries = len(self._cache)
            expired_count = sum(1 for entry in self._cache.values() if entry.is_expired())
            
            return {
                'total_entries': total_entries,
                'expired_entries': expired_count,
                'active_entries': total_entries - expired_count,
                'max_size': self.max_size,
                'usage_ratio': total_entries / self.max_size if self.max_size > 0 else 0
            }


class PersistentCache:
    """持久化缓存管理器"""
    
    def __init__(self, cache_dir: str = ".cache", cache_file: str = "dictionary_cache.pkl"):
        """初始化持久化缓存
        
        Args:
            cache_dir: 缓存目录
            cache_file: 缓存文件名
        """
        self.cache_dir = Path(cache_dir)
        self.cache_file = self.cache_dir / cache_file
        self.logger = logging.getLogger(__name__)
        
        # 确保缓存目录存在
        self.cache_dir.mkdir(exist_ok=True)
        
        # 加载现有缓存
        self._cache: Dict[str, CacheEntry] = {}
        self._load_cache()
    
    def _load_cache(self) -> None:
        """从文件加载缓存"""
        if not self.cache_file.exists():
            return
        
        try:
            with open(self.cache_file, 'rb') as f:
                self._cache = pickle.load(f)
            self.logger.info(f"加载持久化缓存: {len(self._cache)}个条目")
        except Exception as e:
            self.logger.warning(f"加载缓存文件失败: {str(e)}")
            self._cache = {}
    
    def _save_cache(self) -> None:
        """保存缓存到文件"""
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self._cache, f)
        except Exception as e:
            self.logger.error(f"保存缓存文件失败: {str(e)}")
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存数据"""
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        if entry.is_expired():
            del self._cache[key]
            return None
        
        return entry.data
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """设置缓存数据"""
        self._cache[key] = CacheEntry(value, time.time(), ttl)
        self._save_cache()
    
    def delete(self, key: str) -> bool:
        """删除缓存条目"""
        if key in self._cache:
            del self._cache[key]
            self._save_cache()
            return True
        return False
    
    def clear(self) -> None:
        """清空所有缓存"""
        self._cache.clear()
        self._save_cache()
    
    def cleanup_expired(self) -> int:
        """清理过期条目"""
        expired_keys = []
        for key, entry in self._cache.items():
            if entry.is_expired():
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            self._save_cache()
        
        return len(expired_keys)


class DictionaryCache:
    """词典缓存管理器
    
    结合内存缓存和持久化缓存，提供多层缓存策略
    """
    
    def __init__(self, 
                 memory_cache_size: int = 5000,
                 memory_ttl: float = 3600,  # 1小时
                 persistent_ttl: float = 86400 * 7,  # 7天
                 cache_dir: str = ".cache"):
        """初始化词典缓存
        
        Args:
            memory_cache_size: 内存缓存大小
            memory_ttl: 内存缓存过期时间
            persistent_ttl: 持久化缓存过期时间
            cache_dir: 缓存目录
        """
        self.memory_cache = MemoryCache(memory_cache_size, memory_ttl)
        self.persistent_cache = PersistentCache(cache_dir)
        self.persistent_ttl = persistent_ttl
        self.logger = logging.getLogger(__name__)
    
    def _make_key(self, word: str, query_type: str) -> str:
        """生成缓存键"""
        # 使用hash确保键的一致性和长度限制
        key_str = f"{query_type}:{word.lower().strip()}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get_definition(self, word: str) -> Optional[str]:
        """获取单词释义缓存"""
        key = self._make_key(word, "definition")
        
        # 先检查内存缓存
        result = self.memory_cache.get(key)
        if result is not None:
            return result
        
        # 再检查持久化缓存
        result = self.persistent_cache.get(key)
        if result is not None:
            # 将结果放入内存缓存
            self.memory_cache.set(key, result)
            return result
        
        return None
    
    def set_definition(self, word: str, definition: str) -> None:
        """设置单词释义缓存"""
        key = self._make_key(word, "definition")
        
        # 同时设置内存和持久化缓存
        self.memory_cache.set(key, definition)
        self.persistent_cache.set(key, definition, self.persistent_ttl)
    
    def get_pronunciation(self, word: str) -> Optional[str]:
        """获取单词音标缓存"""
        key = self._make_key(word, "pronunciation")
        
        # 先检查内存缓存
        result = self.memory_cache.get(key)
        if result is not None:
            return result
        
        # 再检查持久化缓存
        result = self.persistent_cache.get(key)
        if result is not None:
            # 将结果放入内存缓存
            self.memory_cache.set(key, result)
            return result
        
        return None
    
    def set_pronunciation(self, word: str, pronunciation: str) -> None:
        """设置单词音标缓存"""
        key = self._make_key(word, "pronunciation")
        
        # 同时设置内存和持久化缓存
        self.memory_cache.set(key, pronunciation)
        self.persistent_cache.set(key, pronunciation, self.persistent_ttl)
    
    def get_word_info(self, word: str) -> Optional[Tuple[str, str]]:
        """获取完整单词信息缓存"""
        definition = self.get_definition(word)
        pronunciation = self.get_pronunciation(word)
        
        if definition is not None and pronunciation is not None:
            return definition, pronunciation
        
        return None
    
    def set_word_info(self, word: str, definition: str, pronunciation: str) -> None:
        """设置完整单词信息缓存"""
        self.set_definition(word, definition)
        self.set_pronunciation(word, pronunciation)
    
    def clear_all(self) -> None:
        """清空所有缓存"""
        self.memory_cache.clear()
        self.persistent_cache.clear()
    
    def cleanup_expired(self) -> Dict[str, int]:
        """清理过期缓存"""
        memory_cleaned = self.memory_cache.cleanup_expired()
        persistent_cleaned = self.persistent_cache.cleanup_expired()
        
        return {
            'memory_cleaned': memory_cleaned,
            'persistent_cleaned': persistent_cleaned,
            'total_cleaned': memory_cleaned + persistent_cleaned
        }
    
    def stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        memory_stats = self.memory_cache.stats()
        
        return {
            'memory_cache': memory_stats,
            'persistent_cache': {
                'total_entries': len(self.persistent_cache._cache),
                'cache_file': str(self.persistent_cache.cache_file)
            }
        }