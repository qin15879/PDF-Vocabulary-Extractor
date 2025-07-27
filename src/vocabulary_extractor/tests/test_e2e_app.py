"""
端到端集成测试 - 验证整个应用程序流程
"""

import unittest
from unittest.mock import MagicMock, patch
import tempfile
import os
from pathlib import Path

from vocabulary_extractor.core.app import VocabularyExtractorApp
from vocabulary_extractor.core.models import WordInfo, ProcessingResult
from vocabulary_extractor.pdf.mock_processor import MockPDFProcessor


class TestVocabularyExtractorAppE2E(unittest.TestCase):
    """端到端集成测试"""
    
    def setUp(self):
        """测试前的准备工作"""
        self.temp_dir = tempfile.TemporaryDirectory()
        
        # 创建模拟的输入PDF文件
        self.input_file = Path(self.temp_dir.name) / "test.pdf"
        self.input_file.touch()
        
        # 模拟的PDF处理器
        self.mock_pdf_processor = MockPDFProcessor(
            is_valid=True,
            text_content="This is a test. Hello world! This is a test."
        )
        
        # 模拟的词汇提取器
        self.mock_vocabulary_extractor = MagicMock()
        self.mock_vocabulary_extractor.extract_words.return_value = ["This", "is", "a", "test", "Hello", "world", "This", "is", "a", "test"]
        self.mock_vocabulary_extractor.normalize_words.return_value = ["a", "hello", "is", "test", "this", "world"]
        
        # 模拟的词典服务
        self.mock_dictionary_service = MagicMock()
        self.mock_dictionary_service.batch_lookup.return_value = {
            "a": WordInfo(word="a", definition="一个", pronunciation="/ə/"),
            "hello": WordInfo(word="hello", definition="你好", pronunciation="/həˈloʊ/"),
            "is": WordInfo(word="is", definition="是", pronunciation="/ɪz/"),
            "test": WordInfo(word="test", definition="测试", pronunciation="/test/"),
            "this": WordInfo(word="this", definition="这个", pronunciation="/ðɪs/"),
            "world": WordInfo(word="world", definition="世界", pronunciation="/wɜːrld/"),
        }
        
        # 模拟的PDF生成器
        self.mock_pdf_generator = MagicMock()
        self.mock_pdf_generator.generate_vocabulary_pdf.return_value = True
        
        # 模拟的进度跟踪器
        self.mock_progress_tracker = MagicMock()
        
        # 初始化应用
        self.app = VocabularyExtractorApp(
            pdf_processor=self.mock_pdf_processor,
            vocabulary_extractor=self.mock_vocabulary_extractor,
            dictionary_service=self.mock_dictionary_service,
            pdf_generator=self.mock_pdf_generator,
            progress_tracker=self.mock_progress_tracker
        )
    
    def tearDown(self):
        """测试后的清理工作"""
        self.temp_dir.cleanup()
    
    def test_process_pdf_happy_path(self):
        """测试正常处理流程"""
        
        # 调用主流程
        result = self.app.process_pdf(str(self.input_file))
        
        # 验证结果
        self.assertIsInstance(result, ProcessingResult)
        self.assertEqual(result.total_words, 10)
        self.assertEqual(result.unique_words, 6)
        self.assertEqual(result.successful_definitions, 6)
        self.assertEqual(result.successful_pronunciations, 6)
        self.assertTrue(result.processing_time > 0)
        self.assertEqual(result.source_file, str(self.input_file))
        self.assertEqual(result.output_file, str(Path(self.temp_dir.name) / "test_vocabulary.pdf"))
        
        # 验证各个组件的调用
        self.mock_pdf_processor.validate_pdf.assert_called_once_with(str(self.input_file))
        self.mock_pdf_processor.extract_text.assert_called_once_with(str(self.input_file))
        self.mock_vocabulary_extractor.extract_words.assert_called_once()
        self.mock_vocabulary_extractor.normalize_words.assert_called_once()
        self.mock_dictionary_service.batch_lookup.assert_called_once()
        self.mock_pdf_generator.generate_vocabulary_pdf.assert_called_once()
        
        # 验证进度跟踪
        self.assertEqual(self.mock_progress_tracker.set_total_steps.call_count, 1)
        self.assertEqual(self.mock_progress_tracker.update_progress.call_count, 5)
        self.assertEqual(self.mock_progress_tracker.complete_step.call_count, 4)
    
    def test_process_pdf_no_text_found(self):
        """测试PDF中没有文本的情况"""
        
        # 修改模拟的PDF处理器
        self.mock_pdf_processor.text_content = "   "
        
        # 应该抛出ValueError
        with self.assertRaises(ValueError):
            self.app.process_pdf(str(self.input_file))
    
    def test_process_pdf_invalid_pdf(self):
        """测试无效PDF文件的情况"""
        
        # 修改模拟的PDF处理器
        self.mock_pdf_processor.is_valid = False
        
        # 应该抛出ValueError
        with self.assertRaises(ValueError):
            self.app.process_pdf(str(self.input_file))
    
    def test_process_pdf_file_not_found(self):
        """测试输入文件不存在的情况"""
        
        # 删除模拟的输入文件
        self.input_file.unlink()
        
        # 应该抛出FileNotFoundError
        with self.assertRaises(FileNotFoundError):
            self.app.process_pdf(str(self.input_file))
    
    def test_process_pdf_generator_failure(self):
        """测试PDF生成失败的情况"""
        
        # 修改模拟的PDF生成器
        self.mock_pdf_generator.generate_vocabulary_pdf.return_value = False
        
        # 应该抛出RuntimeError
        with self.assertRaises(RuntimeError):
            self.app.process_pdf(str(self.input_file))
    
    def test_process_pdf_custom_output_file(self):
        """测试指定输出文件路径"""
        
        output_file = str(Path(self.temp_dir.name) / "custom_output.pdf")
        
        # 调用主流程
        result = self.app.process_pdf(str(self.input_file), output_file)
        
        # 验证输出文件路径
        self.assertEqual(result.output_file, output_file)
        self.mock_pdf_generator.generate_vocabulary_pdf.assert_called_once_with(unittest.mock.ANY, output_file)


if __name__ == '__main__':
    unittest.main()