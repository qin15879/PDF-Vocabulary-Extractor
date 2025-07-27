"""
词汇提取器 - 外观类

提供统一的接口，协调各个专门的单词处理组件
"""

from typing import List
import logging

from vocabulary_extractor.core.interfaces import VocabularyExtractorInterface
from vocabulary_extractor.core.word_extractor import WordExtractor
from vocabulary_extractor.core.word_normalizer import WordNormalizer
from vocabulary_extractor.core.word_analyzer import WordAnalyzer


class VocabularyExtractorError(Exception):
    """词汇提取相关错误"""
    pass


class VocabularyExtractor(VocabularyExtractorInterface):
    """词汇提取器外观类
    
    协调各个专门的单词处理组件，提供统一的接口
    """
    
    def __init__(self, 
                 min_word_length: int = 1,
                 max_word_length: int = 50,
                 include_stop_words: bool = True,
                 strict_mode: bool = False):
        """初始化词汇提取器
        
        Args:
            min_word_length: 最小单词长度
            max_word_length: 最大单词长度
            include_stop_words: 是否包含停用词
            strict_mode: 是否使用严格模式（更严格的单词识别）
        """
        self.min_word_length = min_word_length
        self.max_word_length = max_word_length
        self.include_stop_words = include_stop_words
        self.strict_mode = strict_mode
        self.logger = logging.getLogger(__name__)
        
        # 初始化专门的组件
        self.word_extractor = WordExtractor(strict_mode=strict_mode)
        self.word_normalizer = WordNormalizer(
            min_word_length=min_word_length,
            max_word_length=max_word_length,
            include_stop_words=include_stop_words
        )
        self.word_analyzer = WordAnalyzer()
    
    def extract_words(self, text: str) -> List[str]:
        """从文本中提取英语单词
        
        Args:
            text: 输入文本
            
        Returns:
            List[str]: 提取的单词列表（保持原顺序）
            
        Raises:
            VocabularyExtractorError: 提取过程出错
        """
        try:
            return self.word_extractor.extract_words(text)
        except Exception as e:
            raise VocabularyExtractorError(f"单词提取失败: {str(e)}")
    
    def normalize_words(self, words: List[str]) -> List[str]:
        """标准化和去重单词列表
        
        Args:
            words: 原始单词列表
            
        Returns:
            List[str]: 标准化后的唯一单词列表（按字母顺序排序）
        """
        try:
            return self.word_normalizer.normalize_words(words)
        except Exception as e:
            raise VocabularyExtractorError(f"单词标准化失败: {str(e)}")
    
    def normalize_words_with_stats(self, words: List[str]) -> dict:
        """标准化单词并返回详细统计信息
        
        Args:
            words: 原始单词列表
            
        Returns:
            dict: 包含标准化结果和统计信息
        """
        try:
            return self.word_normalizer.normalize_with_stats(words)
        except Exception as e:
            raise VocabularyExtractorError(f"单词标准化统计失败: {str(e)}")
    
    
    def get_word_statistics(self, words: List[str]) -> dict:
        """获取单词统计信息
        
        Args:
            words: 单词列表
            
        Returns:
            dict: 统计信息
        """
        try:
            return self.word_analyzer.get_statistics(words)
        except Exception as e:
            raise VocabularyExtractorError(f"获取统计信息失败: {str(e)}")
    
    def extract_words_with_context(self, text: str, context_chars: int = 50) -> List[dict]:
        """提取单词并包含上下文信息
        
        Args:
            text: 输入文本
            context_chars: 上下文字符数
            
        Returns:
            List[dict]: 包含单词和上下文的字典列表
        """
        try:
            return self.word_extractor.extract_words_with_context(text, context_chars)
        except Exception as e:
            raise VocabularyExtractorError(f"带上下文的单词提取失败: {str(e)}")