"""
PDF处理器单元测试

测试PDF文件验证、文本提取和信息获取功能
"""

import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from vocabulary_extractor.pdf.processor import PDFProcessor, PDFProcessorError


class TestPDFProcessor(unittest.TestCase):
    """PDF处理器测试类"""
    
    def setUp(self):
        """测试准备"""
        self.processor = PDFProcessor(max_file_size_mb=10)
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """测试清理"""
        # 清理临时文件
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init_without_pdfplumber(self):
        """测试没有pdfplumber库的情况"""
        with patch('vocabulary_extractor.pdf.processor.pdfplumber', None):
            with self.assertRaises(ImportError):
                PDFProcessor()
    
    def test_validate_pdf_file_not_exists(self):
        """测试文件不存在的情况"""
        non_existent_file = os.path.join(self.temp_dir, "non_existent.pdf")
        result = self.processor.validate_pdf(non_existent_file)
        self.assertFalse(result)
    
    def test_validate_pdf_wrong_extension(self):
        """测试错误文件扩展名"""
        txt_file = os.path.join(self.temp_dir, "test.txt")
        Path(txt_file).touch()
        
        result = self.processor.validate_pdf(txt_file)
        self.assertFalse(result)
    
    def test_validate_pdf_file_too_large(self):
        """测试文件过大的情况"""
        large_file = os.path.join(self.temp_dir, "large.pdf")
        
        # 创建一个大文件（模拟）
        with patch('pathlib.Path.stat') as mock_stat:
            mock_stat.return_value.st_size = 15 * 1024 * 1024  # 15MB
            Path(large_file).touch()
            
            result = self.processor.validate_pdf(large_file)
            self.assertFalse(result)
    
    @patch('vocabulary_extractor.pdf.processor.pdfplumber')
    def test_validate_pdf_success(self, mock_pdfplumber):
        """测试PDF验证成功"""
        pdf_file = os.path.join(self.temp_dir, "test.pdf")
        Path(pdf_file).touch()
        
        # 模拟pdfplumber行为
        mock_pdf = MagicMock()
        mock_pdf.pages = [MagicMock()]  # 至少一页
        mock_pdf.pages[0].extract_text.return_value = "test text"
        mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
        
        result = self.processor.validate_pdf(pdf_file)
        self.assertTrue(result)
    
    @patch('vocabulary_extractor.pdf.processor.pdfplumber')
    def test_validate_pdf_no_pages(self, mock_pdfplumber):
        """测试PDF没有页面的情况"""
        pdf_file = os.path.join(self.temp_dir, "empty.pdf")
        Path(pdf_file).touch()
        
        # 模拟没有页面的PDF
        mock_pdf = MagicMock()
        mock_pdf.pages = []
        mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
        
        result = self.processor.validate_pdf(pdf_file)
        self.assertFalse(result)
    
    @patch('vocabulary_extractor.pdf.processor.pdfplumber')
    def test_extract_text_success(self, mock_pdfplumber):
        """测试文本提取成功"""
        pdf_file = os.path.join(self.temp_dir, "test.pdf")
        Path(pdf_file).touch()
        
        # 模拟PDF内容
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "This is page 1 content."
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "This is page 2 content."
        
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page1, mock_page2]
        mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
        
        # 需要模拟validate_pdf返回True
        with patch.object(self.processor, 'validate_pdf', return_value=True):
            result = self.processor.extract_text(pdf_file)
        
        expected_text = "This is page 1 content.\nThis is page 2 content."
        self.assertEqual(result, expected_text)
    
    def test_extract_text_invalid_pdf(self):
        """测试提取无效PDF文件的文本"""
        pdf_file = os.path.join(self.temp_dir, "invalid.pdf")
        Path(pdf_file).touch()
        
        with patch.object(self.processor, 'validate_pdf', return_value=False):
            with self.assertRaises(PDFProcessorError):
                self.processor.extract_text(pdf_file)
    
    @patch('vocabulary_extractor.pdf.processor.pdfplumber')
    def test_extract_text_no_content(self, mock_pdfplumber):
        """测试提取没有文本内容的PDF"""
        pdf_file = os.path.join(self.temp_dir, "no_text.pdf")
        Path(pdf_file).touch()
        
        # 模拟没有文本的PDF
        mock_page = MagicMock()
        mock_page.extract_text.return_value = ""
        
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
        
        with patch.object(self.processor, 'validate_pdf', return_value=True):
            with self.assertRaises(PDFProcessorError):
                self.processor.extract_text(pdf_file)
    
    @patch('vocabulary_extractor.pdf.processor.pdfplumber')
    def test_get_pdf_info_success(self, mock_pdfplumber):
        """测试获取PDF信息成功"""
        pdf_file = os.path.join(self.temp_dir, "info_test.pdf")
        Path(pdf_file).touch()
        
        # 模拟PDF内容和元数据
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Sample text content for testing."
        
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page, mock_page]  # 2页
        mock_pdf.metadata = {
            'Title': 'Test PDF',
            'Author': 'Test Author',
            'Creator': 'Test Creator'
        }
        mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
        
        with patch.object(self.processor, 'validate_pdf', return_value=True):
            info = self.processor.get_pdf_info(pdf_file)
        
        self.assertEqual(info['file_name'], 'info_test.pdf')
        self.assertEqual(info['total_pages'], 2)
        self.assertTrue(info['has_text'])
        self.assertEqual(info['title'], 'Test PDF')
        self.assertEqual(info['author'], 'Test Author')
        self.assertGreater(info['estimated_words'], 0)
    
    def test_clean_text(self):
        """测试文本清理功能"""
        # 测试多余空格和空行的清理
        dirty_text = "  This   is    a   test  \n\n\n  Another   line  \n\n"
        expected = "This is a test\nAnother line"
        
        result = self.processor._clean_text(dirty_text)
        self.assertEqual(result, expected)
    
    def test_clean_text_empty(self):
        """测试清理空文本"""
        result = self.processor._clean_text("")
        self.assertEqual(result, "")
        
        result = self.processor._clean_text(None)
        self.assertEqual(result, "")
    
    @patch('vocabulary_extractor.pdf.processor.pdfplumber')
    def test_extract_text_with_progress(self, mock_pdfplumber):
        """测试带进度回调的文本提取"""
        pdf_file = os.path.join(self.temp_dir, "progress_test.pdf")
        Path(pdf_file).touch()
        
        # 模拟PDF内容
        mock_pages = []
        for i in range(3):
            mock_page = MagicMock()
            mock_page.extract_text.return_value = f"Page {i+1} content"
            mock_pages.append(mock_page)
        
        mock_pdf = MagicMock()
        mock_pdf.pages = mock_pages
        mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
        
        # 进度回调函数
        progress_calls = []
        def progress_callback(page_num, total_pages):
            progress_calls.append((page_num, total_pages))
        
        with patch.object(self.processor, 'validate_pdf', return_value=True):
            result = self.processor.extract_text_with_progress(pdf_file, progress_callback)
        
        # 验证文本内容
        expected_text = "Page 1 content\nPage 2 content\nPage 3 content"
        self.assertEqual(result, expected_text)
        
        # 验证进度回调
        self.assertEqual(len(progress_calls), 3)
        self.assertEqual(progress_calls[0], (1, 3))
        self.assertEqual(progress_calls[1], (2, 3))
        self.assertEqual(progress_calls[2], (3, 3))
    
    @patch('vocabulary_extractor.pdf.processor.pdfplumber')
    def test_is_text_searchable_true(self, mock_pdfplumber):
        """测试检查PDF是否包含可搜索文本 - 包含文本"""
        pdf_file = os.path.join(self.temp_dir, "searchable.pdf")
        Path(pdf_file).touch()
        
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Searchable text content"
        
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
        
        result = self.processor.is_text_searchable(pdf_file)
        self.assertTrue(result)
    
    @patch('vocabulary_extractor.pdf.processor.pdfplumber')
    def test_is_text_searchable_false(self, mock_pdfplumber):
        """测试检查PDF是否包含可搜索文本 - 不包含文本"""
        pdf_file = os.path.join(self.temp_dir, "non_searchable.pdf")
        Path(pdf_file).touch()
        
        mock_page = MagicMock()
        mock_page.extract_text.return_value = ""
        
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
        
        result = self.processor.is_text_searchable(pdf_file)
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()