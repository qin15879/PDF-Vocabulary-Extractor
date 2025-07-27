#!/usr/bin/env python3
"""
PDF词汇提取器的基础测试
"""

import unittest
import tempfile
import os
from unittest.mock import patch, MagicMock
from extract_vocabulary import (
    extract_text_from_pdf, 
    extract_english_words, 
    query_word_info, 
    WordInfo
)


class TestPDFVocabularyExtractor(unittest.TestCase):
    
    def setUp(self):
        """测试前的准备工作"""
        self.test_text = "This is a simple test document with some English words."
        self.expected_words = ['document', 'english', 'simple', 'test', 'this', 'words']
    
    def test_extract_english_words(self):
        """测试英文词汇提取功能"""
        words = extract_english_words(self.test_text)
        
        # 检查是否提取了预期的词汇
        self.assertIsInstance(words, list)
        self.assertTrue(len(words) > 0)
        
        # 检查所有词汇都是小写
        for word in words:
            self.assertEqual(word, word.lower())
        
        # 检查停用词被过滤
        stop_words = ['the', 'a', 'is', 'with']
        for stop_word in stop_words:
            self.assertNotIn(stop_word, words)
    
    def test_extract_english_words_empty_text(self):
        """测试空文本处理"""
        words = extract_english_words("")
        self.assertEqual(words, [])
    
    def test_extract_english_words_no_english(self):
        """测试无英文词汇的情况"""
        words = extract_english_words("这是一个中文文本123 !@#")
        self.assertEqual(words, [])
    
    def test_word_info_creation(self):
        """测试WordInfo数据类创建"""
        word_info = WordInfo("test", "/test/", "A procedure for testing")
        self.assertEqual(word_info.word, "test")
        self.assertEqual(word_info.ipa, "/test/")
        self.assertEqual(word_info.definition, "A procedure for testing")
    
    def test_word_info_defaults(self):
        """测试WordInfo默认值"""
        word_info = WordInfo("test")
        self.assertEqual(word_info.word, "test")
        self.assertEqual(word_info.ipa, "")
        self.assertEqual(word_info.definition, "")


if __name__ == '__main__':
    unittest.main()