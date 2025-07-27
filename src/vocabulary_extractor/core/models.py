"""
核心数据模型定义

包含应用程序中使用的主要数据结构：
- WordInfo: 单词信息模型
- ProcessingResult: 处理结果模型  
- APIResponse: API响应模型
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class WordInfo:
    """单词信息数据模型
    
    存储单词及其相关信息，包括中文释义和音标
    """
    word: str
    definition: str = ""
    pronunciation: str = ""
    found_definition: bool = True
    found_pronunciation: bool = True
    
    def __post_init__(self):
        """后处理：标准化单词格式"""
        self.word = self.word.lower().strip()
    
    @property
    def has_complete_info(self) -> bool:
        """检查是否有完整的单词信息"""
        return (self.found_definition and 
                self.found_pronunciation and 
                self.definition and 
                self.pronunciation)


@dataclass
class ProcessingResult:
    """处理结果数据模型
    
    存储整个处理过程的统计信息和结果
    """
    total_words: int
    unique_words: int
    successful_definitions: int
    successful_pronunciations: int
    processing_time: float
    source_file: str
    output_file: str
    
    @property
    def success_rate_definitions(self) -> float:
        """中文释义获取成功率"""
        if self.unique_words == 0:
            return 0.0
        return self.successful_definitions / self.unique_words
    
    @property
    def success_rate_pronunciations(self) -> float:
        """音标获取成功率"""
        if self.unique_words == 0:
            return 0.0
        return self.successful_pronunciations / self.unique_words


@dataclass
class APIResponse:
    """API响应数据模型
    
    统一的API响应格式，用于处理外部API调用结果
    """
    success: bool
    data: dict
    error_message: str = ""
    rate_limited: bool = False
    status_code: Optional[int] = None
    
    @classmethod
    def success_response(cls, data: dict) -> 'APIResponse':
        """创建成功响应"""
        return cls(success=True, data=data)
    
    @classmethod
    def error_response(cls, error_message: str, status_code: Optional[int] = None) -> 'APIResponse':
        """创建错误响应"""
        return cls(success=False, data={}, error_message=error_message, status_code=status_code)
    
    @classmethod
    def rate_limit_response(cls, error_message: str = "API调用频率限制") -> 'APIResponse':
        """创建频率限制响应"""
        return cls(success=False, data={}, error_message=error_message, rate_limited=True)