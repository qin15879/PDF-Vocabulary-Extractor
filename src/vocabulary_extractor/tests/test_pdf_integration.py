"""
PDF处理器集成测试

测试PDF文件信息获取、健康检查、内容预览和结构分析的集成功能
"""

import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from vocabulary_extractor.pdf.mock_processor import MockPDFProcessor


class TestPDFProcessorIntegration(unittest.TestCase):
    """PDF处理器集成测试类"""
    
    def setUp(self):
        """测试准备"""
        self.processor = MockPDFProcessor(max_file_size_mb=10)
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """测试清理"""
        # 清理临时文件
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_extended_pdf_info(self):
        """测试扩展的PDF信息获取"""
        pdf_file = os.path.join(self.temp_dir, "test_extended.pdf")
        Path(pdf_file).touch()
        
        info = self.processor.get_pdf_info(pdf_file)
        
        # 验证扩展字段
        self.assertIn('file_size_bytes', info)
        self.assertIn('estimated_english_words', info)
        self.assertIn('is_encrypted', info)
        self.assertIn('is_corrupted', info)
        self.assertIn('pages_with_text', info)
        self.assertIn('pages_with_images', info)
        self.assertIn('content_preview', info)
        self.assertIn('language_detected', info)
        
        # 验证数据类型和值
        self.assertIsInstance(info['file_size_bytes'], int)
        self.assertIsInstance(info['estimated_english_words'], int)
        self.assertIsInstance(info['is_encrypted'], bool)
        self.assertIsInstance(info['pages_with_text'], int)
        self.assertEqual(info['language_detected'], 'english')
        self.assertGreater(len(info['content_preview']), 0)
    
    def test_academic_paper_info(self):
        """测试学术论文PDF的信息获取"""
        pdf_file = os.path.join(self.temp_dir, "academic_paper.pdf")
        Path(pdf_file).touch()
        
        info = self.processor.get_pdf_info(pdf_file)
        
        # 验证学术论文特有的元数据
        self.assertEqual(info['title'], 'A Novel Approach to NLP')
        self.assertEqual(info['author'], 'Research Team')
        self.assertEqual(info['subject'], 'Natural Language Processing')
        self.assertIn('NLP', info['keywords'])
    
    def test_pdf_health_check_normal(self):
        """测试正常PDF的健康检查"""
        pdf_file = os.path.join(self.temp_dir, "normal.pdf")
        Path(pdf_file).touch()
        
        health = self.processor.check_pdf_health(pdf_file)
        
        self.assertTrue(health['is_healthy'])
        self.assertTrue(health['is_readable'])
        self.assertFalse(health['is_encrypted'])
        self.assertFalse(health['has_corrupted_pages'])
        self.assertEqual(health['total_pages'], health['readable_pages'])
        self.assertEqual(len(health['issues']), 0)
    
    def test_pdf_health_check_encrypted(self):
        """测试加密PDF的健康检查"""
        pdf_file = os.path.join(self.temp_dir, "test_encrypted.pdf")
        Path(pdf_file).touch()
        
        health = self.processor.check_pdf_health(pdf_file)
        
        self.assertTrue(health['is_encrypted'])
        self.assertIn("PDF文件已加密", health['warnings'])
    
    def test_pdf_health_check_corrupted(self):
        """测试损坏PDF的健康检查"""
        pdf_file = os.path.join(self.temp_dir, "test_corrupted.pdf")
        Path(pdf_file).touch()
        
        health = self.processor.check_pdf_health(pdf_file)
        
        self.assertTrue(health['has_corrupted_pages'])
        self.assertLess(health['readable_pages'], health['total_pages'])
        self.assertIn("损坏页面", health['warnings'][0])
    
    def test_content_preview_default(self):
        """测试默认内容预览"""
        pdf_file = os.path.join(self.temp_dir, "preview_test.pdf")
        Path(pdf_file).touch()
        
        preview = self.processor.get_content_preview(pdf_file)
        
        self.assertIn("[Page 1]", preview)
        self.assertIn("Sample PDF Content", preview)
        self.assertGreater(len(preview), 0)
    
    def test_content_preview_with_limit(self):
        """测试限制长度的内容预览"""
        pdf_file = os.path.join(self.temp_dir, "limit_test.pdf")
        Path(pdf_file).touch()
        
        preview = self.processor.get_content_preview(pdf_file, max_chars=100)
        
        # 预览长度应该接近但不超过100字符（可能有"..."添加）
        self.assertLessEqual(len(preview), 105)  # 允许一些误差
        self.assertGreater(len(preview), 0)
    
    def test_content_preview_known_content(self):
        """测试已知内容的PDF预览"""
        pdf_file = os.path.join(self.temp_dir, "sample.pdf")
        Path(pdf_file).touch()
        
        preview = self.processor.get_content_preview(pdf_file)
        
        self.assertIn("Machine Learning", preview)
        self.assertIn("[Page 1]", preview)
    
    def test_structure_analysis_basic(self):
        """测试基础结构分析"""
        pdf_file = os.path.join(self.temp_dir, "structure_test.pdf")
        Path(pdf_file).touch()
        
        structure = self.processor.analyze_pdf_structure(pdf_file)
        
        # 验证基本结构信息
        self.assertGreater(structure['total_pages'], 0)
        self.assertTrue(structure['has_text'])
        self.assertTrue(structure['has_images'])
        self.assertGreater(structure['text_density'], 0)
        self.assertGreater(structure['avg_words_per_page'], 0)
        
        # 验证页面尺寸信息
        self.assertEqual(len(structure['page_sizes']), structure['total_pages'])
        if structure['page_sizes']:
            first_page = structure['page_sizes'][0]
            self.assertIn('width', first_page)
            self.assertIn('height', first_page)
            self.assertGreater(first_page['width'], 0)
            self.assertGreater(first_page['height'], 0)
    
    def test_structure_analysis_academic_paper(self):
        """测试学术论文的结构分析"""
        pdf_file = os.path.join(self.temp_dir, "academic_structure.pdf")
        Path(pdf_file).touch()
        
        structure = self.processor.analyze_pdf_structure(pdf_file)
        
        # 学术论文应该包含表格
        self.assertTrue(structure['has_tables'])
        
        # 验证内容分布
        dist = structure['content_distribution']
        self.assertGreater(dist['mixed_pages'], 0)  # 应该有图文混合页
    
    def test_structure_analysis_content_distribution(self):
        """测试内容分布分析"""
        pdf_file = os.path.join(self.temp_dir, "distribution_test.pdf")
        Path(pdf_file).touch()
        
        structure = self.processor.analyze_pdf_structure(pdf_file)
        
        dist = structure['content_distribution']
        
        # 验证所有页面都被分类
        total_classified = (dist['text_pages'] + dist['image_pages'] + 
                          dist['mixed_pages'] + dist['empty_pages'])
        self.assertEqual(total_classified, structure['total_pages'])
        
        # 验证至少有一些文本页面
        self.assertGreater(dist['text_pages'] + dist['mixed_pages'], 0)
    
    def test_invalid_pdf_handling(self):
        """测试无效PDF文件的处理"""
        non_pdf_file = os.path.join(self.temp_dir, "test.txt")
        Path(non_pdf_file).touch()
        
        # 健康检查应该失败
        health = self.processor.check_pdf_health(non_pdf_file)
        self.assertFalse(health['is_healthy'])
        self.assertFalse(health['is_readable'])
        self.assertGreater(len(health['issues']), 0)
        
        # 内容预览应该返回错误信息
        preview = self.processor.get_content_preview(non_pdf_file)
        self.assertIn("无法读取", preview)
        
        # 结构分析应该返回空结构
        structure = self.processor.analyze_pdf_structure(non_pdf_file)
        self.assertEqual(structure['total_pages'], 0)
    
    def test_workflow_integration(self):
        """测试完整工作流程的集成"""
        pdf_file = os.path.join(self.temp_dir, "workflow_test.pdf")
        Path(pdf_file).touch()
        
        # 1. 首先进行健康检查
        health = self.processor.check_pdf_health(pdf_file)
        self.assertTrue(health['is_healthy'])
        
        # 2. 获取详细信息
        info = self.processor.get_pdf_info(pdf_file)
        self.assertEqual(info['total_pages'], health['total_pages'])
        
        # 3. 获取内容预览
        preview = self.processor.get_content_preview(pdf_file)
        self.assertGreater(len(preview), 0)
        
        # 4. 分析结构
        structure = self.processor.analyze_pdf_structure(pdf_file)
        self.assertEqual(structure['total_pages'], info['total_pages'])
        
        # 验证数据一致性
        self.assertEqual(info['has_text'], structure['has_text'])


if __name__ == '__main__':
    unittest.main()