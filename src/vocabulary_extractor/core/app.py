"""
主应用程序控制器

协调整个PDF词汇提取流程的核心控制器
"""

from typing import Optional
from pathlib import Path
import time

from ..core.interfaces import (
    PDFProcessorInterface,
    VocabularyExtractorInterface, 
    DictionaryServiceInterface,
    PDFGeneratorInterface,
    ProgressTrackerInterface
)
from ..core.models import ProcessingResult, WordInfo
from ..config.manager import ConfigManager


class VocabularyExtractorApp:
    """PDF词汇提取器主应用程序"""
    
    def __init__(
        self,
        pdf_processor: PDFProcessorInterface,
        vocabulary_extractor: VocabularyExtractorInterface,
        dictionary_service: DictionaryServiceInterface,
        pdf_generator: PDFGeneratorInterface,
        progress_tracker: Optional[ProgressTrackerInterface] = None,
        config_manager: Optional[ConfigManager] = None
    ):
        """初始化应用程序
        
        Args:
            pdf_processor: PDF处理器
            vocabulary_extractor: 词汇提取器
            dictionary_service: 词典服务
            pdf_generator: PDF生成器
            progress_tracker: 进度跟踪器（可选）
            config_manager: 配置管理器（可选）
        """
        self.pdf_processor = pdf_processor
        self.vocabulary_extractor = vocabulary_extractor
        self.dictionary_service = dictionary_service
        self.pdf_generator = pdf_generator
        self.progress_tracker = progress_tracker
        self.config_manager = config_manager or ConfigManager()
        
    def process_pdf(self, input_file: str, output_file: Optional[str] = None) -> ProcessingResult:
        """处理PDF文件的主流程
        
        Args:
            input_file: 输入PDF文件路径
            output_file: 输出PDF文件路径，如果为None则自动生成
            
        Returns:
            ProcessingResult: 处理结果
            
        Raises:
            FileNotFoundError: 输入文件不存在
            ValueError: 文件格式无效
            RuntimeError: 处理过程出错
        """
        start_time = time.time()
        
        # 验证输入文件
        if not Path(input_file).exists():
            raise FileNotFoundError(f"输入文件不存在: {input_file}")
        
        # 设置进度跟踪
        if self.progress_tracker:
            self.progress_tracker.set_total_steps(5)
            self.progress_tracker.update_progress("初始化", 0.0, "开始处理PDF文件")
        
        try:
            # 步骤1: 验证和提取PDF文本
            if self.progress_tracker:
                self.progress_tracker.update_progress("PDF处理", 0.2, "验证PDF文件")
            
            if not self.pdf_processor.validate_pdf(input_file):
                raise ValueError(f"无效的PDF文件: {input_file}")
            
            text = self.pdf_processor.extract_text(input_file)
            if not text.strip():
                raise ValueError("PDF文件中没有找到文本内容")
            
            if self.progress_tracker:
                self.progress_tracker.complete_step("PDF文本提取完成")
            
            # 步骤2: 提取和处理词汇
            if self.progress_tracker:
                self.progress_tracker.update_progress("词汇提取", 0.4, "识别英语单词")
            
            words = self.vocabulary_extractor.extract_words(text)
            unique_words = self.vocabulary_extractor.normalize_words(words)
            
            if self.progress_tracker:
                self.progress_tracker.complete_step(f"提取到{len(unique_words)}个唯一单词")
            
            # 步骤3: 查询词典信息
            if self.progress_tracker:
                self.progress_tracker.update_progress("词典查询", 0.6, "获取单词释义和音标")
            
            word_info_dict = self.dictionary_service.batch_lookup(unique_words)
            vocabulary = list(word_info_dict.values())
            
            # 统计成功获取信息的单词数量
            successful_definitions = sum(1 for w in vocabulary if w.found_definition)
            successful_pronunciations = sum(1 for w in vocabulary if w.found_pronunciation)
            
            if self.progress_tracker:
                self.progress_tracker.complete_step(
                    f"获取释义: {successful_definitions}/{len(vocabulary)}, "
                    f"获取音标: {successful_pronunciations}/{len(vocabulary)}"
                )
            
            # 步骤4: 生成输出PDF
            if self.progress_tracker:
                self.progress_tracker.update_progress("PDF生成", 0.8, "生成词汇表PDF")
            
            if output_file is None:
                output_file = self._generate_output_filename(input_file)
            
            # 按字母顺序排序词汇
            vocabulary.sort(key=lambda w: w.word)
            
            success = self.pdf_generator.generate_vocabulary_pdf(vocabulary, output_file)
            if not success:
                raise RuntimeError("PDF生成失败")
            
            if self.progress_tracker:
                self.progress_tracker.complete_step(f"PDF已生成: {output_file}")
            
            # 步骤5: 完成处理
            processing_time = time.time() - start_time
            
            result = ProcessingResult(
                total_words=len(words),
                unique_words=len(unique_words),
                successful_definitions=successful_definitions,
                successful_pronunciations=successful_pronunciations,
                processing_time=processing_time,
                source_file=input_file,
                output_file=output_file
            )
            
            if self.progress_tracker:
                self.progress_tracker.update_progress("完成", 1.0, "处理完成")
            
            return result
            
        except Exception as e:
            if self.progress_tracker:
                self.progress_tracker.update_progress("错误", 0.0, f"处理失败: {str(e)}")
            raise
    
    def _generate_output_filename(self, input_file: str) -> str:
        """生成输出文件名
        
        Args:
            input_file: 输入文件路径
            
        Returns:
            生成的输出文件路径
        """
        input_path = Path(input_file)
        output_name = f"{input_path.stem}_vocabulary.pdf"
        return str(input_path.parent / output_name)
    
    def get_supported_formats(self) -> list:
        """获取支持的文件格式列表"""
        return ['.pdf']
    
    def validate_input_file(self, file_path: str) -> tuple[bool, str]:
        """验证输入文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            (is_valid, error_message): 验证结果和错误消息
        """
        try:
            path = Path(file_path)
            
            # 检查文件是否存在
            if not path.exists():
                return False, "文件不存在"
            
            # 检查文件扩展名
            if path.suffix.lower() not in self.get_supported_formats():
                return False, f"不支持的文件格式: {path.suffix}"
            
            # 检查文件大小
            max_size_mb = self.config_manager.get('processing.max_file_size_mb', 50)
            file_size_mb = path.stat().st_size / (1024 * 1024)
            if file_size_mb > max_size_mb:
                return False, f"文件过大: {file_size_mb:.1f}MB (最大: {max_size_mb}MB)"
            
            # 验证PDF文件
            if not self.pdf_processor.validate_pdf(file_path):
                return False, "PDF文件格式无效或已损坏"
            
            return True, ""
            
        except Exception as e:
            return False, f"文件验证错误: {str(e)}"