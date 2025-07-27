"""
单词提取器 - 专注于从文本中提取英语单词
"""

import re
import logging
from typing import List

from vocabulary_extractor.core.interfaces import VocabularyExtractorInterface


class WordExtractor(VocabularyExtractorInterface):
    """专注于从文本中提取英语单词的类"""
    
    # 英语单词模式 - 匹配由字母组成的单词
    ENGLISH_WORD_PATTERN = re.compile(r'\b[A-Za-z]+\b')
    
    # 更严格的英语单词模式 - 至少2个字符，不含数字
    STRICT_ENGLISH_PATTERN = re.compile(r'\b[A-Za-z]{2,}\b')
    
    def __init__(self, strict_mode: bool = False):
        """初始化单词提取器
        
        Args:
            strict_mode: 是否使用严格模式（更严格的单词识别）
        """
        self.strict_mode = strict_mode
        self.logger = logging.getLogger(__name__)
        
        # 选择单词模式
        self.word_pattern = self.STRICT_ENGLISH_PATTERN if strict_mode else self.ENGLISH_WORD_PATTERN
    
    def extract_words(self, text: str) -> List[str]:
        """从文本中提取英语单词
        
        Args:
            text: 输入文本
            
        Returns:
            List[str]: 提取的单词列表（保持原顺序）
        """
        if not text or not isinstance(text, str):
            return []
        
        try:
            # 预处理文本
            cleaned_text = self._preprocess_text(text)
            
            # 使用正则表达式提取单词
            words = self.word_pattern.findall(cleaned_text)
            
            self.logger.info(f"从{len(text)}字符的文本中提取到{len(words)}个单词")
            return words
            
        except Exception as e:
            raise ValueError(f"单词提取失败: {str(e)}")
    
    def extract_words_with_context(self, text: str, context_chars: int = 50) -> List[dict]:
        """提取单词并包含上下文信息
        
        Args:
            text: 输入文本
            context_chars: 上下文字符数
            
        Returns:
            List[dict]: 包含单词和上下文的字典列表
        """
        if not text:
            return []
        
        try:
            words_with_context = []
            
            # 找到所有匹配的单词及其位置
            for match in self.word_pattern.finditer(text):
                word = match.group()
                start_pos = match.start()
                end_pos = match.end()
                
                # 获取上下文
                context_start = max(0, start_pos - context_chars)
                context_end = min(len(text), end_pos + context_chars)
                context = text[context_start:context_end]
                
                words_with_context.append({
                    'word': word,
                    'position': start_pos,
                    'context': context.strip(),
                    'length': len(word)
                })
            
            return words_with_context
            
        except Exception as e:
            raise ValueError(f"带上下文的单词提取失败: {str(e)}")
    
    def _preprocess_text(self, text: str) -> str:
        """预处理文本
        
        Args:
            text: 原始文本
            
        Returns:
            str: 预处理后的文本
        """
        # 移除HTML标签（简单处理）
        text = re.sub(r'<[^>]+>', ' ', text)
        
        # 移除常见的非文本内容
        text = re.sub(r'http[s]?://\S+', ' ', text)  # URL
        text = re.sub(r'www\.\S+', ' ', text)  # www链接
        text = re.sub(r'\S+@\S+\.\S+', ' ', text)  # 邮箱
        
        # 处理特殊字符 - 保留字母、数字、空格和基本标点
        text = re.sub(r'[^\w\s\-\']', ' ', text)
        
        # 处理连字符分隔的单词
        text = re.sub(r'\b(\w+)-(\w+)\b', r'\1 \2', text)
        
        # 处理所有格（如 word's -> word s）
        text = re.sub(r"(\w+)'s\b", r'\1', text)
        text = re.sub(r"(\w+)'\b", r'\1', text)
        
        # 标准化空白字符
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()