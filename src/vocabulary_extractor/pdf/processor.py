"""
PDF处理器实现

使用pdfplumber库实现PDF文件的验证、文本提取和信息获取功能
"""

import os
from pathlib import Path
from typing import Dict, Optional
import logging

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

from ..core.interfaces import PDFProcessorInterface
from ..core.models import APIResponse


class PDFProcessorError(Exception):
    """PDF处理相关错误"""
    pass


class PDFProcessor(PDFProcessorInterface):
    """PDF处理器实现类"""
    
    def __init__(self, max_file_size_mb: int = 50):
        """初始化PDF处理器
        
        Args:
            max_file_size_mb: 允许的最大文件大小（MB）
        """
        if pdfplumber is None:
            raise ImportError("需要安装pdfplumber库: pip install pdfplumber")
        
        self.max_file_size_mb = max_file_size_mb
        self.logger = logging.getLogger(__name__)
    
    def validate_pdf(self, file_path: str) -> bool:
        """验证PDF文件的有效性
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            bool: 文件是否有效
        """
        try:
            # 检查文件是否存在
            if not Path(file_path).exists():
                self.logger.error(f"文件不存在: {file_path}")
                return False
            
            # 检查文件扩展名
            if not file_path.lower().endswith('.pdf'):
                self.logger.error(f"不是PDF文件: {file_path}")
                return False
            
            # 检查文件大小
            file_size_mb = Path(file_path).stat().st_size / (1024 * 1024)
            if file_size_mb > self.max_file_size_mb:
                self.logger.error(f"文件过大: {file_size_mb:.1f}MB > {self.max_file_size_mb}MB")
                return False
            
            # 尝试打开PDF文件
            with pdfplumber.open(file_path) as pdf:
                # 检查是否有页面
                if len(pdf.pages) == 0:
                    self.logger.error(f"PDF文件没有页面: {file_path}")
                    return False
                
                # 尝试读取第一页（验证文件完整性）
                first_page = pdf.pages[0]
                _ = first_page.extract_text()
            
            return True
            
        except Exception as e:
            self.logger.error(f"PDF验证失败 {file_path}: {str(e)}")
            return False
    
    def extract_text(self, file_path: str) -> str:
        """从PDF中提取文本内容
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            str: 提取的文本内容
            
        Raises:
            PDFProcessorError: PDF处理错误
            FileNotFoundError: 文件不存在
        """
        if not self.validate_pdf(file_path):
            raise PDFProcessorError(f"PDF文件验证失败: {file_path}")
        
        try:
            extracted_text = []
            
            with pdfplumber.open(file_path) as pdf:
                total_pages = len(pdf.pages)
                self.logger.info(f"开始提取PDF文本，共{total_pages}页")
                
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        # 提取页面文本
                        page_text = page.extract_text()
                        
                        if page_text:
                            # 清理文本（移除多余空白字符）
                            cleaned_text = self._clean_text(page_text)
                            extracted_text.append(cleaned_text)
                            
                        self.logger.debug(f"第{page_num}/{total_pages}页文本提取完成")
                        
                    except Exception as e:
                        self.logger.warning(f"第{page_num}页文本提取失败: {str(e)}")
                        continue
            
            full_text = "\n".join(extracted_text)
            
            if not full_text.strip():
                raise PDFProcessorError("PDF文件中未找到可提取的文本内容")
            
            self.logger.info(f"文本提取完成，共{len(full_text)}个字符")
            return full_text
            
        except pdfplumber.pdfplumber.PDFSyntaxError as e:
            raise PDFProcessorError(f"PDF文件格式错误: {str(e)}")
        except Exception as e:
            raise PDFProcessorError(f"文本提取失败: {str(e)}")
    
    def get_pdf_info(self, file_path: str) -> Dict:
        """获取PDF文件信息
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            Dict: PDF文件信息
        """
        if not self.validate_pdf(file_path):
            raise PDFProcessorError(f"PDF文件验证失败: {file_path}")
        
        try:
            file_path_obj = Path(file_path)
            
            with pdfplumber.open(file_path) as pdf:
                # 基础文件信息
                info = {
                    'file_name': file_path_obj.name,
                    'file_path': str(file_path_obj.absolute()),
                    'file_size_mb': round(file_path_obj.stat().st_size / (1024 * 1024), 2),
                    'file_size_bytes': file_path_obj.stat().st_size,
                    'total_pages': len(pdf.pages),
                    'has_text': False,
                    'estimated_words': 0,
                    'estimated_english_words': 0,
                    'created_time': None,
                    'modified_time': None,
                    'is_encrypted': False,
                    'is_corrupted': False,
                    'pages_with_text': 0,
                    'pages_with_images': 0,
                    'content_preview': "",
                    'language_detected': "unknown"
                }
                
                # 文件时间信息
                stat = file_path_obj.stat()
                info['created_time'] = stat.st_ctime
                info['modified_time'] = stat.st_mtime
                
                # 检查PDF是否加密
                try:
                    info['is_encrypted'] = hasattr(pdf, 'is_encrypted') and pdf.is_encrypted
                except:
                    info['is_encrypted'] = False
                
                # PDF元数据
                if hasattr(pdf, 'metadata') and pdf.metadata:
                    metadata = pdf.metadata
                    info.update({
                        'title': metadata.get('Title', '').strip(),
                        'author': metadata.get('Author', '').strip(),
                        'subject': metadata.get('Subject', '').strip(),
                        'creator': metadata.get('Creator', '').strip(),
                        'producer': metadata.get('Producer', '').strip(),
                        'creation_date': metadata.get('CreationDate', ''),
                        'modification_date': metadata.get('ModDate', ''),
                        'keywords': metadata.get('Keywords', '').strip()
                    })
                
                # 详细分析页面内容
                total_chars = 0
                english_word_count = 0
                pages_with_text = 0
                pages_with_images = 0
                content_samples = []
                
                # 分析前几页或所有页面（如果页数较少）
                pages_to_analyze = min(5, len(pdf.pages))
                
                for i in range(pages_to_analyze):
                    try:
                        page = pdf.pages[i]
                        page_text = page.extract_text()
                        
                        # 检查文本内容
                        if page_text and page_text.strip():
                            pages_with_text += 1
                            page_text_clean = page_text.strip()
                            total_chars += len(page_text_clean)
                            
                            # 收集内容样本（用于预览）
                            if len(content_samples) < 3:
                                # 获取页面前200个字符作为预览
                                sample = page_text_clean[:200].replace('\n', ' ')
                                content_samples.append(f"Page {i+1}: {sample}...")
                            
                            # 估算英语单词数
                            import re
                            english_words = re.findall(r'\b[A-Za-z]+\b', page_text)
                            english_word_count += len(english_words)
                        
                        # 检查图片内容
                        if hasattr(page, 'images') and page.images:
                            pages_with_images += 1
                            
                    except Exception as e:
                        self.logger.warning(f"分析第{i+1}页时出错: {str(e)}")
                        continue
                
                # 更新统计信息
                if total_chars > 0:
                    info['has_text'] = True
                    info['pages_with_text'] = pages_with_text
                    info['pages_with_images'] = pages_with_images
                    
                    # 基于分析页面估算总单词数
                    if pages_to_analyze > 0:
                        avg_chars_per_page = total_chars / pages_to_analyze
                        avg_english_words_per_page = english_word_count / pages_to_analyze
                        
                        info['estimated_words'] = int((avg_chars_per_page * len(pdf.pages)) / 5)
                        info['estimated_english_words'] = int(avg_english_words_per_page * len(pdf.pages))
                    
                    # 生成内容预览
                    info['content_preview'] = " | ".join(content_samples)
                    
                    # 简单的语言检测
                    if english_word_count > total_chars * 0.1:  # 如果英语单词占比较高
                        info['language_detected'] = "english"
                    elif any(ord(char) > 127 for char in page_text[:500]):  # 包含非ASCII字符
                        info['language_detected'] = "mixed"
                    else:
                        info['language_detected'] = "unknown"
                
                return info
                
        except Exception as e:
            raise PDFProcessorError(f"获取PDF信息失败: {str(e)}")
    
    def _clean_text(self, text: str) -> str:
        """清理提取的文本
        
        Args:
            text: 原始文本
            
        Returns:
            str: 清理后的文本
        """
        if not text:
            return ""
        
        # 移除多余的空白字符
        lines = []
        for line in text.split('\n'):
            cleaned_line = ' '.join(line.split())  # 移除多余空格
            if cleaned_line:  # 跳过空行
                lines.append(cleaned_line)
        
        return '\n'.join(lines)
    
    def extract_text_with_progress(self, file_path: str, progress_callback=None) -> str:
        """带进度回调的文本提取
        
        Args:
            file_path: PDF文件路径
            progress_callback: 进度回调函数(page_num, total_pages)
            
        Returns:
            str: 提取的文本内容
        """
        if not self.validate_pdf(file_path):
            raise PDFProcessorError(f"PDF文件验证失败: {file_path}")
        
        try:
            extracted_text = []
            
            with pdfplumber.open(file_path) as pdf:
                total_pages = len(pdf.pages)
                
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        page_text = page.extract_text()
                        
                        if page_text:
                            cleaned_text = self._clean_text(page_text)
                            extracted_text.append(cleaned_text)
                        
                        # 调用进度回调
                        if progress_callback:
                            progress_callback(page_num, total_pages)
                            
                    except Exception as e:
                        self.logger.warning(f"第{page_num}页文本提取失败: {str(e)}")
                        continue
            
            full_text = "\n".join(extracted_text)
            
            if not full_text.strip():
                raise PDFProcessorError("PDF文件中未找到可提取的文本内容")
            
            return full_text
            
        except Exception as e:
            raise PDFProcessorError(f"文本提取失败: {str(e)}")
    
    def is_text_searchable(self, file_path: str) -> bool:
        """检查PDF是否包含可搜索的文本
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            bool: 是否包含可搜索文本
        """
        try:
            with pdfplumber.open(file_path) as pdf:
                # 检查前几页
                pages_to_check = min(3, len(pdf.pages))
                
                for i in range(pages_to_check):
                    page_text = pdf.pages[i].extract_text()
                    if page_text and page_text.strip():
                        return True
                
                return False
                
        except Exception:
            return False
    
    def check_pdf_health(self, file_path: str) -> Dict:
        """检查PDF文件健康状态
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            Dict: 健康检查结果
        """
        health_info = {
            'is_healthy': True,
            'issues': [],
            'warnings': [],
            'is_readable': True,
            'is_encrypted': False,
            'has_corrupted_pages': False,
            'total_pages': 0,
            'readable_pages': 0
        }
        
        try:
            # 基本验证
            if not self.validate_pdf(file_path):
                health_info['is_healthy'] = False
                health_info['is_readable'] = False
                health_info['issues'].append("PDF文件验证失败")
                return health_info
            
            with pdfplumber.open(file_path) as pdf:
                health_info['total_pages'] = len(pdf.pages)
                
                # 检查加密状态
                try:
                    if hasattr(pdf, 'is_encrypted') and pdf.is_encrypted:
                        health_info['is_encrypted'] = True
                        health_info['warnings'].append("PDF文件已加密")
                except:
                    pass
                
                # 检查每一页的可读性
                corrupted_pages = []
                readable_pages = 0
                
                for i, page in enumerate(pdf.pages):
                    try:
                        # 尝试提取文本
                        text = page.extract_text()
                        if text is not None:
                            readable_pages += 1
                        
                        # 尝试获取页面尺寸
                        _ = page.width, page.height
                        
                    except Exception as e:
                        corrupted_pages.append(i + 1)
                        health_info['issues'].append(f"第{i + 1}页损坏: {str(e)}")
                
                health_info['readable_pages'] = readable_pages
                
                if corrupted_pages:
                    health_info['has_corrupted_pages'] = True
                    health_info['warnings'].append(f"发现{len(corrupted_pages)}个损坏页面: {corrupted_pages}")
                
                # 检查是否有可提取的内容
                if readable_pages == 0:
                    health_info['is_readable'] = False
                    health_info['issues'].append("无法从任何页面提取内容")
                elif readable_pages < len(pdf.pages) * 0.5:
                    health_info['warnings'].append("超过50%的页面无法正常读取")
                
                # 总体健康评估
                if len(health_info['issues']) > 0:
                    health_info['is_healthy'] = False
                
        except Exception as e:
            health_info['is_healthy'] = False
            health_info['is_readable'] = False
            health_info['issues'].append(f"PDF健康检查失败: {str(e)}")
        
        return health_info
    
    def get_content_preview(self, file_path: str, max_chars: int = 500) -> str:
        """获取PDF内容预览
        
        Args:
            file_path: PDF文件路径
            max_chars: 最大字符数
            
        Returns:
            str: 内容预览
        """
        try:
            if not self.validate_pdf(file_path):
                return "无法读取PDF文件"
            
            with pdfplumber.open(file_path) as pdf:
                preview_text = []
                current_chars = 0
                
                # 从前几页提取预览文本
                for i, page in enumerate(pdf.pages[:3]):
                    try:
                        page_text = page.extract_text()
                        if page_text and page_text.strip():
                            # 清理文本
                            cleaned_text = self._clean_text(page_text)
                            
                            # 添加页面标识
                            page_preview = f"[Page {i+1}] {cleaned_text}"
                            
                            # 检查是否超过最大字符数
                            if current_chars + len(page_preview) > max_chars:
                                remaining_chars = max_chars - current_chars
                                if remaining_chars > 0:
                                    preview_text.append(page_preview[:remaining_chars] + "...")
                                break
                            
                            preview_text.append(page_preview)
                            current_chars += len(page_preview)
                            
                    except Exception:
                        continue
                
                if not preview_text:
                    return "PDF文件不包含可提取的文本内容"
                
                return "\n\n".join(preview_text)
                
        except Exception as e:
            return f"获取预览失败: {str(e)}"
    
    def analyze_pdf_structure(self, file_path: str) -> Dict:
        """分析PDF文档结构
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            Dict: 结构分析结果
        """
        structure_info = {
            'total_pages': 0,
            'has_text': False,
            'has_images': False,
            'has_tables': False,
            'text_density': 0.0,  # 文本密度（字符数/页面数）
            'avg_words_per_page': 0,
            'page_sizes': [],
            'content_distribution': {
                'text_pages': 0,
                'image_pages': 0,
                'mixed_pages': 0,
                'empty_pages': 0
            }
        }
        
        try:
            if not self.validate_pdf(file_path):
                return structure_info
            
            with pdfplumber.open(file_path) as pdf:
                structure_info['total_pages'] = len(pdf.pages)
                total_text_chars = 0
                total_words = 0
                
                for i, page in enumerate(pdf.pages):
                    try:
                        # 页面尺寸
                        if hasattr(page, 'width') and hasattr(page, 'height'):
                            structure_info['page_sizes'].append({
                                'page': i + 1,
                                'width': page.width,
                                'height': page.height
                            })
                        
                        # 文本分析
                        page_text = page.extract_text()
                        has_page_text = bool(page_text and page_text.strip())
                        
                        # 图片分析
                        has_page_images = bool(hasattr(page, 'images') and page.images)
                        
                        # 表格分析（简单检测）
                        has_page_tables = False
                        if hasattr(page, 'extract_tables'):
                            try:
                                tables = page.extract_tables()
                                has_page_tables = bool(tables)
                                if has_page_tables:
                                    structure_info['has_tables'] = True
                            except:
                                pass
                        
                        # 更新全局标记
                        if has_page_text:
                            structure_info['has_text'] = True
                            total_text_chars += len(page_text.strip())
                            # 简单单词计数
                            import re
                            words = re.findall(r'\b\w+\b', page_text)
                            total_words += len(words)
                        
                        if has_page_images:
                            structure_info['has_images'] = True
                        
                        # 页面内容分类
                        if has_page_text and has_page_images:
                            structure_info['content_distribution']['mixed_pages'] += 1
                        elif has_page_text:
                            structure_info['content_distribution']['text_pages'] += 1
                        elif has_page_images:
                            structure_info['content_distribution']['image_pages'] += 1
                        else:
                            structure_info['content_distribution']['empty_pages'] += 1
                            
                    except Exception as e:
                        self.logger.warning(f"分析第{i+1}页结构时出错: {str(e)}")
                        structure_info['content_distribution']['empty_pages'] += 1
                        continue
                
                # 计算统计信息
                if structure_info['total_pages'] > 0:
                    structure_info['text_density'] = total_text_chars / structure_info['total_pages']
                    structure_info['avg_words_per_page'] = total_words / structure_info['total_pages']
                
        except Exception as e:
            self.logger.error(f"PDF结构分析失败: {str(e)}")
        
        return structure_info