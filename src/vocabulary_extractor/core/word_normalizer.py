"""
单词标准化器 - 专注于单词的标准化和清理
"""

import re
import logging
from typing import List, Set


class WordNormalizer:
    """专注于单词标准化和清理的类"""
    
    def __init__(self, 
                 min_word_length: int = 1,
                 max_word_length: int = 50,
                 include_stop_words: bool = True):
        """初始化单词标准化器
        
        Args:
            min_word_length: 最小单词长度
            max_word_length: 最大单词长度
            include_stop_words: 是否包含停用词
        """
        self.min_word_length = min_word_length
        self.max_word_length = max_word_length
        self.include_stop_words = include_stop_words
        self.logger = logging.getLogger(__name__)
        
        # 常见的停用词
        self.COMMON_STOP_WORDS = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'were', 'will', 'with', 'the', 'this', 'but', 'they',
            'have', 'had', 'what', 'said', 'each', 'which', 'she', 'do', 'how',
            'their', 'if', 'up', 'out', 'many', 'then', 'them', 'these', 'so',
            'some', 'her', 'would', 'make', 'like', 'into', 'him', 'time',
            'two', 'more', 'go', 'no', 'way', 'could', 'my', 'than', 'first',
            'been', 'call', 'who', 'oil', 'sit', 'now', 'find', 'down', 'day',
            'did', 'get', 'come', 'made', 'may', 'part'
        }
        
        # 常见的非单词模式
        self.NON_WORD_PATTERNS = [
            re.compile(r'^(www|http|https|ftp)$', re.IGNORECASE),  # 协议前缀
            re.compile(r'^\d+$'),  # 纯数字
        ]
    
    def normalize_words(self, words: List[str]) -> List[str]:
        """标准化和去重单词列表
        
        Args:
            words: 原始单词列表
            
        Returns:
            List[str]: 标准化后的唯一单词列表（按字母顺序排序）
        """
        if not words:
            return []
        
        try:
            normalized_words = set()
            
            for word in words:
                if isinstance(word, str) and word.strip():
                    normalized_word = self._normalize_single_word(word)
                    if normalized_word and self._is_valid_normalized_word(normalized_word):
                        normalized_words.add(normalized_word)
            
            # 转换为列表并排序
            result = sorted(list(normalized_words))
            
            self.logger.info(f"标准化处理：{len(words)}个原始单词 -> {len(result)}个唯一单词")
            return result
            
        except Exception as e:
            raise ValueError(f"单词标准化失败: {str(e)}")
    
    def normalize_with_stats(self, words: List[str]) -> dict:
        """标准化单词并返回详细统计信息
        
        Args:
            words: 原始单词列表
            
        Returns:
            dict: 包含标准化结果和统计信息
        """
        if not words:
            return {
                'normalized_words': [],
                'original_count': 0,
                'unique_count': 0,
                'invalid_count': 0,
                'duplicate_count': 0,
                'processing_details': {}
            }
        
        try:
            normalized_words = set()
            invalid_words = []
            duplicate_pairs = []
            
            # 跟踪处理详情
            processing_details = {
                'case_normalized': 0,
                'punctuation_removed': 0,
                'whitespace_trimmed': 0,
                'duplicates_found': 0
            }
            
            for original_word in words:
                if not isinstance(original_word, str) or not original_word.strip():
                    invalid_words.append(original_word)
                    continue
                
                # 执行标准化
                normalized_word = self._normalize_single_word(original_word)
                
                if not normalized_word:
                    invalid_words.append(original_word)
                    continue
                
                if not self._is_valid_normalized_word(normalized_word):
                    invalid_words.append(original_word)
                    continue
                
                # 检查是否已存在（重复）
                if normalized_word in normalized_words:
                    duplicate_pairs.append((original_word, normalized_word))
                    processing_details['duplicates_found'] += 1
                else:
                    normalized_words.add(normalized_word)
                
                # 统计处理类型
                if original_word != original_word.lower():
                    processing_details['case_normalized'] += 1
                if original_word != original_word.strip():
                    processing_details['whitespace_trimmed'] += 1
            
            # 转换为排序列表
            result_list = sorted(list(normalized_words))
            
            return {
                'normalized_words': result_list,
                'original_count': len(words),
                'unique_count': len(result_list),
                'invalid_count': len(invalid_words),
                'duplicate_count': len(duplicate_pairs),
                'processing_details': processing_details,
                'invalid_words': invalid_words[:10]
            }
            
        except Exception as e:
            raise ValueError(f"单词标准化统计失败: {str(e)}")
    
    def _normalize_single_word(self, word: str) -> str:
        """标准化单个单词
        
        Args:
            word: 原始单词
            
        Returns:
            str: 标准化后的单词
        """
        if not word or not isinstance(word, str):
            return ""
        
        # 1. 去除首尾空白
        normalized = word.strip()
        
        # 2. 转换为小写
        normalized = normalized.lower()
        
        # 3. 移除非字母字符（但保留连字符用于后续处理）
        normalized = re.sub(r'[^\w\-]', '', normalized)
        
        # 4. 处理连字符分隔的单词 - 取所有有效部分
        if '-' in normalized:
            parts = normalized.split('-')
            # 选择所有有效的部分，而不是只选最长的
            valid_parts = [part for part in parts if len(part) >= self.min_word_length and part.isalpha()]
            if valid_parts:
                # 返回第一个有效部分，而不是最长的
                normalized = valid_parts[0]
            else:
                normalized = parts[0] if parts and parts[0].isalpha() else ""
        
        # 5. 最终验证：必须只包含字母
        if not normalized.isalpha():
            return ""
        
        # 6. 长度检查
        if len(normalized) < self.min_word_length or len(normalized) > self.max_word_length:
            return ""
        
        return normalized
    
    def _is_valid_normalized_word(self, word: str) -> bool:
        """验证标准化后的单词是否有效
        
        Args:
            word: 标准化后的单词
            
        Returns:
            bool: 是否为有效单词
        """
        if not word or len(word) < self.min_word_length or len(word) > self.max_word_length:
            return False
        
        if not word.isalpha():
            return False
        
        # 停用词检查
        if not self.include_stop_words and word in self.COMMON_STOP_WORDS:
            return False
        
        # 检查非单词模式
        for pattern in self.NON_WORD_PATTERNS:
            if pattern.match(word):
                return False
        
        return self._has_valid_english_structure(word)
    
    def _has_valid_english_structure(self, word: str) -> bool:
        """检查单词是否具有有效的英语结构
        
        Args:
            word: 待检查的单词
            
        Returns:
            bool: 是否具有有效结构
        """
        word_lower = word.lower()
        
        # 检查元音字母 - 英语单词通常包含至少一个元音
        vowels = 'aeiou'
        if len(word) >= 3 and not any(char in vowels for char in word_lower):
            # 对于3个字符以上的单词，通常应该包含元音
            # 但有一些例外，如"by", "my", "gym"等
            exceptions = {'gym', 'spy', 'try', 'dry', 'fly', 'sky', 'cry', 'why', 'shy'}
            if word_lower not in exceptions:
                return False
        
        # 检查重复字符 - 避免过多重复字符的无意义字符串
        if len(word) >= 4:
            # 检查是否有超过3个连续相同字符
            if re.search(r'(.)\1{3,}', word_lower):
                return False
        
        # 检查是否为常见的无意义字符组合
        meaningless_patterns = [
            r'^[bcdfghjklmnpqrstvwxyz]+$',  # 全辅音（超过2个字符）
            r'^[aeiou]+$',  # 全元音（超过2个字符）
        ]
        
        for pattern in meaningless_patterns:
            if len(word) > 2 and re.match(pattern, word_lower):
                return False
        
        return True