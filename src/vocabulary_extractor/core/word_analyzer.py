"""
单词分析器 - 专注于单词统计和分析
"""

import re
import logging
from typing import List, Dict, Any


class WordAnalyzer:
    """专注于单词统计和分析的类"""
    
    def __init__(self):
        """初始化单词分析器"""
        self.logger = logging.getLogger(__name__)
    
    def analyze_frequency(self, words: List[str]) -> Dict[str, Any]:
        """分析单词频率
        
        Args:
            words: 原始单词列表
            
        Returns:
            dict: 包含频率统计信息
        """
        if not words:
            return {
                'words': [],
                'frequencies': {},
                'total_unique': 0,
                'most_common': [],
                'original_forms': {}
            }
        
        try:
            word_frequencies = {}
            normalized_to_original = {}
            
            for original_word in words:
                if not isinstance(original_word, str) or not original_word.strip():
                    continue
                
                normalized = original_word.lower().strip()
                if not normalized:
                    continue
                
                # 统计频率
                if normalized in word_frequencies:
                    word_frequencies[normalized] += 1
                else:
                    word_frequencies[normalized] = 1
                    # 保存第一次出现的原始形式
                    if normalized not in normalized_to_original:
                        normalized_to_original[normalized] = original_word
            
            # 按频率排序
            sorted_by_frequency = sorted(word_frequencies.items(), key=lambda x: x[1], reverse=True)
            unique_words = [word for word, freq in sorted_by_frequency]
            
            return {
                'words': unique_words,
                'frequencies': word_frequencies,
                'total_unique': len(unique_words),
                'most_common': sorted_by_frequency[:10],
                'original_forms': normalized_to_original
            }
            
        except Exception as e:
            raise ValueError(f"频率分析失败: {str(e)}")
    
    def group_by_characteristics(self, words: List[str]) -> Dict[str, Any]:
        """按特征分组单词
        
        Args:
            words: 单词列表
            
        Returns:
            dict: 按不同特征分组的单词
        """
        if not words:
            return {
                'by_length': {},
                'by_first_letter': {},
                'by_pattern': {'simple': [], 'compound': [], 'technical': []},
                'statistics': {}
            }
        
        try:
            # 标准化单词
            normalized_words = list(set(w.lower().strip() for w in words if w))
            normalized_words = [w for w in normalized_words if w]
            
            # 按长度分组
            by_length = {}
            for word in normalized_words:
                length = len(word)
                if length not in by_length:
                    by_length[length] = []
                by_length[length].append(word)
            
            # 按首字母分组
            by_first_letter = {}
            for word in normalized_words:
                if word:  # 确保单词不为空
                    first_letter = word[0].upper()
                    if first_letter not in by_first_letter:
                        by_first_letter[first_letter] = []
                    by_first_letter[first_letter].append(word)
            
            # 按模式分组
            simple_words = []
            compound_words = []
            technical_words = []
            
            for word in normalized_words:
                if self._is_technical_word(word):
                    technical_words.append(word)
                elif self._is_compound_word(word):
                    compound_words.append(word)
                else:
                    simple_words.append(word)
            
            # 统计信息
            statistics = {
                'total_words': len(normalized_words),
                'avg_length': sum(len(w) for w in normalized_words) / len(normalized_words) if normalized_words else 0,
                'length_distribution': {str(k): len(v) for k, v in by_length.items()},
                'alphabetical_distribution': {k: len(v) for k, v in by_first_letter.items()}
            }
            
            return {
                'by_length': by_length,
                'by_first_letter': by_first_letter,
                'by_pattern': {
                    'simple': sorted(simple_words),
                    'compound': sorted(compound_words),
                    'technical': sorted(technical_words)
                },
                'statistics': statistics
            }
            
        except Exception as e:
            raise ValueError(f"单词分组失败: {str(e)}")
    
    def get_statistics(self, words: List[str]) -> Dict[str, Any]:
        """获取单词统计信息
        
        Args:
            words: 单词列表
            
        Returns:
            dict: 统计信息
        """
        if not words:
            return {
                'total_words': 0,
                'unique_words': 0,
                'avg_word_length': 0.0,
                'min_word_length': 0,
                'max_word_length': 0,
                'length_distribution': {}
            }
        
        unique_words = list(set(word.lower().strip() for word in words if word))
        word_lengths = [len(word) for word in unique_words]
        
        # 长度分布统计
        length_distribution = {}
        for length in word_lengths:
            length_distribution[length] = length_distribution.get(length, 0) + 1
        
        return {
            'total_words': len(words),
            'unique_words': len(unique_words),
            'avg_word_length': sum(word_lengths) / len(word_lengths) if word_lengths else 0.0,
            'min_word_length': min(word_lengths) if word_lengths else 0,
            'max_word_length': max(word_lengths) if word_lengths else 0,
            'length_distribution': length_distribution
        }
    
    def _is_technical_word(self, word: str) -> bool:
        """判断是否为技术词汇"""
        technical_patterns = [
            r'.*tion$',  # -tion结尾
            r'.*ment$',  # -ment结尾
            r'.*ology$', # -ology结尾
            r'.*ical$',  # -ical结尾
            r'.*ize$',   # -ize结尾
            r'.*algorithm.*', # 包含algorithm
            r'.*compute.*',   # 包含compute
            r'.*system.*',    # 包含system
            r'.*process.*',   # 包含process
        ]
        
        word_lower = word.lower()
        return any(re.match(pattern, word_lower) for pattern in technical_patterns)
    
    def _is_compound_word(self, word: str) -> bool:
        """判断是否为复合词"""
        # 简单判断：长度较长且包含常见复合词模式
        if len(word) < 8:
            return False
        
        compound_patterns = [
            r'.*work.*',    # 包含work
            r'.*time.*',    # 包含time
            r'.*way.*',     # 包含way
            r'.*thing.*',   # 包含thing
            r'.*self.*',    # 包含self
            r'.*over.*',    # 包含over
            r'.*under.*',   # 包含under
        ]
        
        word_lower = word.lower()
        return any(re.search(pattern, word_lower) for pattern in compound_patterns)