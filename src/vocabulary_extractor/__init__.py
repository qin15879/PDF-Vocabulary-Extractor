"""
PDF词汇提取器 - 从PDF文档中提取英语单词并生成带有中文释义和音标的词汇表

这个包提供了从PDF文档中自动提取英语单词，获取中文释义和IPA音标，
并生成格式化的PDF词汇表的完整功能。
"""

__version__ = "1.0.0"
__author__ = "PDF Vocabulary Extractor Team"

from .core.models import WordInfo, ProcessingResult, APIResponse
from .core.app import VocabularyExtractorApp

__all__ = [
    "WordInfo", 
    "ProcessingResult", 
    "APIResponse",
    "VocabularyExtractorApp"
]