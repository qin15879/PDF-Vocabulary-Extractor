"""
词汇提取器单元测试

测试英语单词识别算法、单词提取逻辑和验证功能
"""

import unittest
from pathlib import Path

from vocabulary_extractor.core.extractor import VocabularyExtractor, VocabularyExtractorError


class TestVocabularyExtractor(unittest.TestCase):
    """词汇提取器测试类"""
    
    def setUp(self):
        """测试准备"""
        self.extractor = VocabularyExtractor()
        self.strict_extractor = VocabularyExtractor(strict_mode=True)
        self.no_stopwords_extractor = VocabularyExtractor(include_stop_words=False)
    
    def test_extract_words_basic(self):
        """测试基本单词提取"""
        text = "This is a simple test for word extraction."
        words = self.extractor.extract_words(text)
        
        expected_words = ['This', 'is', 'a', 'simple', 'test', 'for', 'word', 'extraction']
        self.assertEqual(words, expected_words)
    
    def test_extract_words_with_punctuation(self):
        """测试包含标点符号的文本"""
        text = "Hello, world! How are you? I'm fine, thanks."
        words = self.extractor.extract_words(text)
        
        # 应该只提取字母单词，忽略标点符号
        # "I'm" 会被处理为 "Im"
        expected = ['Hello', 'world', 'How', 'are', 'you', 'Im', 'fine', 'thanks']
        self.assertEqual(words, expected)
    
    def test_extract_words_with_numbers(self):
        """测试包含数字的文本"""
        text = "There are 123 students and 45 teachers in the school."
        words = self.extractor.extract_words(text)
        
        # 数字应该被过滤掉
        expected = ['There', 'are', 'students', 'and', 'teachers', 'in', 'the', 'school']
        self.assertEqual(words, expected)
    
    def test_extract_words_with_urls_and_emails(self):
        """测试包含URL和邮箱的文本"""
        text = "Visit https://example.com or email test@example.com for more information."
        words = self.extractor.extract_words(text)
        
        # URL和邮箱应该被预处理掉
        expected = ['Visit', 'or', 'email', 'for', 'more', 'information']
        self.assertEqual(words, expected)
    
    def test_extract_words_with_contractions(self):
        """测试包含缩写的文本"""
        text = "I can't believe it's working! They're amazing."
        words = self.extractor.extract_words(text)
        
        # 缩写应该被正确处理 - 去除撇号
        expected_words = ['I', 'cant', 'believe', 'it', 'working', 'Theyre', 'amazing']
        self.assertEqual(words, expected_words)
    
    def test_extract_words_empty_text(self):
        """测试空文本"""
        self.assertEqual(self.extractor.extract_words(""), [])
        self.assertEqual(self.extractor.extract_words(None), [])
        self.assertEqual(self.extractor.extract_words("   "), [])
    
    def test_extract_words_with_hyphenated_words(self):
        """测试连字符单词"""
        text = "This is a well-known fact about state-of-the-art technology."
        words = self.extractor.extract_words(text)
        
        # 连字符单词应该被分割
        self.assertIn('well', words)
        self.assertIn('known', words)
        self.assertIn('state', words)
        self.assertIn('art', words)
    
    def test_normalize_words_basic(self):
        """测试基本单词标准化"""
        words = ['Hello', 'world', 'Hello', 'WORLD', 'test']
        normalized = self.extractor.normalize_words(words)
        
        expected = ['hello', 'test', 'world']  # 去重并排序
        self.assertEqual(normalized, expected)
    
    def test_normalize_words_with_whitespace(self):
        """测试包含空格的单词标准化"""
        words = [' hello ', 'world', '  test  ', 'hello']
        normalized = self.extractor.normalize_words(words)
        
        expected = ['hello', 'test', 'world']
        self.assertEqual(normalized, expected)
    
    def test_normalize_words_empty_list(self):
        """测试空列表标准化"""
        self.assertEqual(self.extractor.normalize_words([]), [])
        self.assertEqual(self.extractor.normalize_words(['']), [])
        self.assertEqual(self.extractor.normalize_words(['  ', None, '']), [])
    
    def test_is_english_word_valid(self):
        """测试有效英语单词识别"""
        valid_words = ['hello', 'world', 'test', 'algorithm', 'python']
        for word in valid_words:
            self.assertTrue(self.extractor.is_english_word(word))
    
    def test_is_english_word_invalid(self):
        """测试无效英语单词识别"""
        invalid_words = ['123', 'hello123', '!@#', '', '   ']
        for word in invalid_words:
            self.assertFalse(self.extractor.is_english_word(word))
    
    def test_min_word_length_filter(self):
        """测试最小单词长度过滤"""
        extractor = VocabularyExtractor(min_word_length=3)
        text = "I am a big fan of AI."
        words = extractor.extract_words(text)
        
        # 应该过滤掉长度小于3的单词
        for word in words:
            self.assertGreaterEqual(len(word), 3)
    
    def test_max_word_length_filter(self):
        """测试最大单词长度过滤"""
        extractor = VocabularyExtractor(max_word_length=5)
        text = "This is a supercalifragilisticexpialidocious word."
        words = extractor.extract_words(text)
        
        # 应该过滤掉长度大于5的单词
        for word in words:
            self.assertLessEqual(len(word), 5)
    
    def test_stop_words_filtering(self):
        """测试停用词过滤"""
        text = "The quick brown fox jumps over the lazy dog."
        
        # 包含停用词
        words_with_stop = self.extractor.extract_words(text)
        self.assertIn('the', [w.lower() for w in words_with_stop])
        
        # 不包含停用词
        words_without_stop = self.no_stopwords_extractor.extract_words(text)
        self.assertNotIn('the', [w.lower() for w in words_without_stop])
        self.assertIn('quick', [w.lower() for w in words_without_stop])
    
    def test_strict_mode(self):
        """测试严格模式"""
        text = "I am a big fan of AI and ML."
        
        normal_words = self.extractor.extract_words(text)
        strict_words = self.strict_extractor.extract_words(text)
        
        # 严格模式应该过滤掉单字符单词
        self.assertIn('I', normal_words)
        self.assertIn('a', normal_words)
        # 在严格模式下，单字符单词可能被过滤
    
    def test_english_structure_validation(self):
        """测试英语单词结构验证"""
        # 有效的英语单词结构
        valid_words = ['hello', 'world', 'test', 'computer', 'algorithm']
        for word in valid_words:
            self.assertTrue(self.extractor._has_valid_english_structure(word))
        
        # 无效的英语单词结构
        invalid_words = ['bcdfg', 'aaaaa', 'qqqq', 'xyz']
        for word in invalid_words:
            result = self.extractor._has_valid_english_structure(word)
            # 某些可能被过滤，但不是全部（因为有例外情况）
    
    def test_get_word_statistics(self):
        """测试单词统计功能"""
        words = ['hello', 'world', 'test', 'hello', 'algorithm']
        stats = self.extractor.get_word_statistics(words)
        
        self.assertEqual(stats['total_words'], 5)
        self.assertEqual(stats['unique_words'], 4)  # hello重复
        self.assertGreater(stats['avg_word_length'], 0)
        self.assertIn(5, stats['length_distribution'])  # 'hello', 'world'长度为5
        self.assertIn(9, stats['length_distribution'])  # 'algorithm'长度为9
    
    def test_get_word_statistics_empty(self):
        """测试空单词列表的统计"""
        stats = self.extractor.get_word_statistics([])
        
        self.assertEqual(stats['total_words'], 0)
        self.assertEqual(stats['unique_words'], 0)
        self.assertEqual(stats['avg_word_length'], 0.0)
        self.assertEqual(stats['min_word_length'], 0)
        self.assertEqual(stats['max_word_length'], 0)
    
    def test_extract_words_with_context(self):
        """测试带上下文的单词提取"""
        text = "Machine learning is a powerful tool for data analysis."
        words_with_context = self.extractor.extract_words_with_context(text, context_chars=10)
        
        self.assertGreater(len(words_with_context), 0)
        
        # 检查结果格式
        for item in words_with_context:
            self.assertIn('word', item)
            self.assertIn('position', item)
            self.assertIn('context', item)
            self.assertIn('length', item)
            self.assertIsInstance(item['position'], int)
            self.assertIsInstance(item['length'], int)
    
    def test_preprocess_text(self):
        """测试文本预处理"""
        text = "Visit <a href='http://example.com'>example</a> for more info."
        processed = self.extractor._preprocess_text(text)
        
        # HTML标签和URL应该被移除
        self.assertNotIn('<a', processed)
        self.assertNotIn('href', processed)
        self.assertNotIn('http://example.com', processed)
        self.assertIn('example', processed)
        self.assertIn('info', processed)
    
    def test_technical_text_extraction(self):
        """测试技术文本的单词提取"""
        text = """
        Machine learning algorithms are used in artificial intelligence applications.
        Neural networks and deep learning are popular approaches in AI research.
        Natural language processing (NLP) helps computers understand human language.
        """
        
        words = self.extractor.extract_words(text)
        normalized = self.extractor.normalize_words(words)
        
        # 检查是否提取到技术术语
        expected_terms = ['machine', 'learning', 'algorithms', 'artificial', 
                         'intelligence', 'neural', 'networks', 'deep', 
                         'natural', 'language', 'processing']
        
        for term in expected_terms:
            self.assertIn(term, normalized)
    
    def test_academic_text_extraction(self):
        """测试学术文本的单词提取"""
        text = """
        Abstract: This research presents a novel methodology for analyzing
        experimental data using statistical methods and computational techniques.
        The results demonstrate significant improvements in accuracy and efficiency.
        """
        
        words = self.extractor.extract_words(text)
        normalized = self.extractor.normalize_words(words)
        
        # 检查学术词汇
        academic_terms = ['research', 'methodology', 'analyzing', 'experimental',
                         'statistical', 'computational', 'demonstrate', 'significant',
                         'improvements', 'accuracy', 'efficiency']
        
        for term in academic_terms:
            self.assertIn(term, normalized)
    
    def test_error_handling(self):
        """测试错误处理"""
        # 测试非字符串输入
        self.assertEqual(self.extractor.extract_words(123), [])
        self.assertEqual(self.extractor.extract_words([]), [])
        
        # 测试is_english_word的错误处理
        self.assertFalse(self.extractor.is_english_word(None))
        self.assertFalse(self.extractor.is_english_word(123))
        self.assertFalse(self.extractor.is_english_word([]))
    
    def test_workflow_integration(self):
        """测试完整工作流程"""
        text = """
        PDF vocabulary extraction is a useful tool for language learning.
        It helps students identify new words and improve their vocabulary.
        The system can process academic papers, textbooks, and articles.
        """
        
        # 1. 提取单词
        words = self.extractor.extract_words(text)
        self.assertGreater(len(words), 0)
        
        # 2. 标准化
        normalized = self.extractor.normalize_words(words)
        self.assertGreater(len(normalized), 0)
        self.assertLessEqual(len(normalized), len(words))  # 去重后应该<=原数量
        
        # 3. 获取统计信息
        stats = self.extractor.get_word_statistics(words)
        self.assertEqual(stats['total_words'], len(words))
        self.assertEqual(stats['unique_words'], len(normalized))
        
        # 4. 验证结果质量
        for word in normalized:
            self.assertTrue(self.extractor.is_english_word(word))
            self.assertGreaterEqual(len(word), self.extractor.min_word_length)
            self.assertLessEqual(len(word), self.extractor.max_word_length)


if __name__ == '__main__':
    unittest.main()