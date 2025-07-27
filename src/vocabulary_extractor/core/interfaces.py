"""
核心接口和抽象基类定义

定义了应用程序各个组件需要遵循的接口规范
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from .models import WordInfo, ProcessingResult, APIResponse


class PDFProcessorInterface(ABC):
    """PDF处理器接口"""
    
    @abstractmethod
    def validate_pdf(self, file_path: str) -> bool:
        """验证PDF文件的有效性"""
        pass
    
    @abstractmethod
    def extract_text(self, file_path: str) -> str:
        """从PDF中提取文本内容"""
        pass
    
    @abstractmethod
    def get_pdf_info(self, file_path: str) -> dict:
        """获取PDF文件信息"""
        pass


class VocabularyExtractorInterface(ABC):
    """词汇提取器接口"""
    
    @abstractmethod
    def extract_words(self, text: str) -> List[str]:
        """从文本中提取英语单词"""
        pass
    
    @abstractmethod
    def normalize_words(self, words: List[str]) -> List[str]:
        """标准化和去重单词列表"""
        pass
    
    @abstractmethod
    def is_english_word(self, word: str) -> bool:
        """判断是否为英语单词"""
        pass


class DictionaryServiceInterface(ABC):
    """词典服务接口"""
    
    @abstractmethod
    def get_definition(self, word: str) -> str:
        """获取单词的中文释义"""
        pass
    
    @abstractmethod
    def get_pronunciation(self, word: str) -> str:
        """获取单词的IPA音标"""
        pass
    
    @abstractmethod
    def batch_lookup(self, words: List[str]) -> Dict[str, WordInfo]:
        """批量查询单词信息"""
        pass


class PDFGeneratorInterface(ABC):
    """PDF生成器接口"""
    
    @abstractmethod
    def generate_vocabulary_pdf(self, vocabulary: List[WordInfo], output_path: str) -> bool:
        """生成词汇表PDF文档"""
        pass
    
    @abstractmethod
    def format_word_entry(self, word_info: WordInfo) -> str:
        """格式化单词条目"""
        pass


class ProgressTrackerInterface(ABC):
    """进度跟踪器接口"""
    
    @abstractmethod
    def update_progress(self, stage: str, progress: float, message: str = ""):
        """更新处理进度"""
        pass
    
    @abstractmethod
    def set_total_steps(self, total: int):
        """设置总步骤数"""
        pass
    
    @abstractmethod
    def complete_step(self, message: str = ""):
        """完成一个步骤"""
        pass


class ConfigManagerInterface(ABC):
    """配置管理器接口"""
    
    @abstractmethod
    def get(self, key: str, default=None):
        """获取配置值"""
        pass
    
    @abstractmethod
    def set(self, key: str, value):
        """设置配置值"""
        pass
    
    @abstractmethod
    def load_config(self, config_path: Optional[str] = None):
        """加载配置文件"""
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """验证配置的有效性"""
        pass