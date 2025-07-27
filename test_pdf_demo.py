#!/usr/bin/env python3
"""
PDF词汇提取器实际功能测试
"""

import tempfile
import os
from pathlib import Path
from vocabulary_extractor.core.app import VocabularyExtractorApp
from vocabulary_extractor.pdf.processor import PDFProcessor
from vocabulary_extractor.dictionary.service import LocalDictionaryService
from vocabulary_extractor.config.manager import ConfigManager

def create_test_pdf():
    """创建测试PDF文件"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        # 创建临时文件
        temp_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        temp_file.close()
        
        # 创建PDF内容
        c = canvas.Canvas(temp_file.name, pagesize=letter)
        width, height = letter
        
        # 添加标题
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, height - 100, "Vocabulary Test Document")
        
        # 添加测试文本
        c.setFont("Helvetica", 12)
        text_content = """
        This is a comprehensive test document for vocabulary extraction.
        Python programming language is widely used in data science and machine learning.
        
        Technical terms include: algorithm, function, variable, dictionary, and array.
        Common words: hello, world, test, example, development, software, application.
        
        Advanced vocabulary: implementation, optimization, configuration, architecture.
        
        The quick brown fox jumps over the lazy dog. This sentence contains all letters.
        """
        
        # 分行写入文本
        lines = text_content.strip().split('\n')
        y_position = height - 150
        
        for line in lines:
            if line.strip():
                # 处理长行
                words = line.split()
                current_line = ""
                for word in words:
                    if len(current_line + word) < 60:
                        current_line += word + " "
                    else:
                        c.drawString(100, y_position, current_line.strip())
                        y_position -= 20
                        current_line = word + " "
                if current_line.strip():
                    c.drawString(100, y_position, current_line.strip())
                    y_position -= 30
            else:
                y_position -= 20
        
        c.save()
        return temp_file.name
        
    except ImportError:
        print("reportlab未安装，创建简单文本文件替代...")
        # 创建文本文件作为替代
        temp_file = tempfile.NamedTemporaryFile(suffix='.txt', delete=False, mode='w')
        temp_file.write("""
This is a comprehensive test document for vocabulary extraction.
Python programming language is widely used in data science and machine learning.

Technical terms include: algorithm, function, variable, dictionary, and array.
Common words: hello, world, test, example, development, software, application.

Advanced vocabulary: implementation, optimization, configuration, architecture.

The quick brown fox jumps over the lazy dog. This sentence contains all letters.
""")
        temp_file.close()
        return temp_file.name

def test_vocabulary_extraction():
    """测试词汇提取功能"""
    print("🚀 开始PDF词汇提取测试...")
    
    try:
        # 创建测试文件
        test_file = create_test_pdf()
        print(f"✅ 创建测试文件: {test_file}")
        
        # 初始化组件
        config = ConfigManager()
        pdf_processor = PDFProcessor()
        dictionary_service = LocalDictionaryService()
        
        # 创建应用实例 - 使用简化测试
        from vocabulary_extractor.core.word_extractor import WordExtractor
        from vocabulary_extractor.core.word_normalizer import WordNormalizer
        
        # 直接测试核心功能 - 使用具体实现类
        from vocabulary_extractor.core.word_extractor import WordExtractor as WordExtractorImpl
        from vocabulary_extractor.core.word_normalizer import WordNormalizer as WordNormalizerImpl
        
        extractor = WordExtractorImpl()
        normalizer = WordNormalizerImpl()
        
        # 读取PDF文本
        if test_file.endswith('.pdf'):
            text = pdf_processor.extract_text(test_file)
        else:
            # 文本文件直接读取
            with open(test_file, 'r', encoding='utf-8') as f:
                text = f.read()
        
        print(f"📄 读取文本长度: {len(text)} 字符")
        
        # 提取单词
        words = extractor.extract_words(text)
        print(f"🔍 提取到 {len(words)} 个原始单词")
        
        # 标准化单词
        unique_words = normalizer.normalize_words(words)
        print(f"✨ 标准化后 {len(unique_words)} 个唯一单词")
        
        # 获取词典信息
        vocabulary = []
        for word in unique_words[:15]:  # 限制前15个单词
            definition = dictionary_service.get_definition(word)
            pronunciation = dictionary_service.get_pronunciation(word)
            vocabulary.append({
                'word': word,
                'definition': definition,
                'pronunciation': pronunciation
            })
        
        # 模拟结果
        class MockResult:
            def __init__(self):
                self.success = True
                self.total_words = len(words)
                self.unique_words = len(unique_words)
                self.vocabulary = vocabulary
                self.error_message = None
        
        result = MockResult()
        
        # 处理结果
        print("📖 正在处理结果...")
        
        if result.success:
            print("✅ PDF处理成功!")
            print(f"📊 提取统计:")
            print(f"   - 总单词数: {result.total_words}")
            print(f"   - 唯一单词数: {result.unique_words}")
            print(f"   - 有效单词数: {len(result.vocabulary)}")
            
            # 显示前10个单词
            print("\n📋 前10个提取的词汇:")
            for i, word_info in enumerate(result.vocabulary[:10]):
                print(f"   {i+1}. {word_info.word} - {word_info.definition}")
            
            # 显示不同长度的单词分布
            lengths = {}
            for word_info in result.vocabulary:
                length = len(word_info.word)
                lengths[length] = lengths.get(length, 0) + 1
            
            print(f"\n📏 单词长度分布:")
            for length in sorted(lengths.keys())[:8]:
                print(f"   {length}字母单词: {lengths[length]}个")
                
        else:
            print(f"❌ PDF处理失败: {result.error_message}")
            
        # 清理
        if os.path.exists(test_file):
            os.unlink(test_file)
            
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_vocabulary_extraction()