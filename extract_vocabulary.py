#!/usr/bin/env python3
"""
PDF词汇提取器 - 简化版本
从PDF中提取英文单词，查询释义和音标，生成词汇表
"""

import re
import sys
import argparse
from dataclasses import dataclass
from typing import List, Dict, Tuple
import os
import time

import pdfplumber
import requests
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors


@dataclass
class WordInfo:
    """单词信息数据类"""
    word: str
    definition: str
    pronunciation: str


class PDFVocabularyExtractor:
    """PDF词汇提取器主类"""
    
    def __init__(self):
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'can', 'must', 'shall'
        }
        self.cache = {}
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """从PDF提取文本"""
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"文件不存在: {pdf_path}")
        
        try:
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
            return text
        except Exception as e:
            raise ValueError(f"无法读取PDF文件: {e}")
    
    def extract_english_words(self, text: str) -> List[str]:
        """提取英文单词"""
        # 使用正则表达式提取单词
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        
        # 过滤停用词和短词
        words = [word for word in words if len(word) > 2 and word not in self.stop_words]
        
        # 去重并保持顺序
        seen = set()
        unique_words = []
        for word in words:
            if word not in seen:
                seen.add(word)
                unique_words.append(word)
        
        return unique_words
    
    def query_word_info(self, word: str) -> Tuple[str, str]:
        """查询单词释义和音标"""
        if word in self.cache:
            return self.cache[word]
        
        try:
            # 使用Free Dictionary API
            url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()[0]
                
                # 获取音标
                pronunciation = ""
                if 'phonetics' in data and data['phonetics']:
                    for phonetic in data['phonetics']:
                        if 'text' in phonetic and phonetic['text']:
                            pronunciation = phonetic['text']
                            break
                
                # 获取释义
                definition = ""
                if 'meanings' in data and data['meanings']:
                    for meaning in data['meanings']:
                        if 'definitions' in meaning and meaning['definitions']:
                            definition = meaning['definitions'][0].get('definition', '')
                            break
                
                # 简化为中文释义（实际API返回英文，这里做简化处理）
                if definition:
                    definition = definition[:100]  # 限制长度
                else:
                    definition = "释义未找到"
                
                if not pronunciation:
                    pronunciation = "音标未找到"
                
                result = (definition, pronunciation)
            else:
                result = ("释义未找到", "音标未找到")
                
        except Exception:
            result = ("释义未找到", "音标未找到")
        
        self.cache[word] = result
        return result
    
    def generate_vocabulary_pdf(self, words_info: List[WordInfo], output_path: str):
        """生成词汇PDF"""
        doc = SimpleDocTemplate(output_path, pagesize=A4)
        story = []
        
        # 标题
        styles = getSampleStyleSheet()
        title = Paragraph("PDF词汇表", styles['Title'])
        story.append(title)
        
        # 创建表格数据
        data = [['单词', '音标', '释义']]
        for word_info in sorted(words_info, key=lambda x: x.word.lower()):
            data.append([
                word_info.word,
                word_info.pronunciation,
                word_info.definition
            ])
        
        # 创建表格
        table = Table(data, colWidths=[100, 150, 300])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        
        story.append(table)
        doc.build(story)
    
    def process_pdf(self, input_path: str, output_path: str):
        """处理PDF文件"""
        print(f"正在处理: {input_path}")
        
        # 1. 提取文本
        print("正在提取文本...")
        text = self.extract_text_from_pdf(input_path)
        
        # 2. 提取单词
        print("正在提取单词...")
        words = self.extract_english_words(text)
        print(f"找到 {len(words)} 个唯一单词")
        
        # 3. 查询词典
        print("正在查询词典...")
        words_info = []
        for i, word in enumerate(words):
            if i % 10 == 0:
                print(f"进度: {i}/{len(words)}")
            
            definition, pronunciation = self.query_word_info(word)
            words_info.append(WordInfo(word, definition, pronunciation))
        
        # 4. 生成PDF
        print("正在生成PDF...")
        self.generate_vocabulary_pdf(words_info, output_path)
        
        print(f"完成！词汇表已保存到: {output_path}")
        print(f"总计处理了 {len(words_info)} 个单词")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='PDF词汇提取器')
    parser.add_argument('input', help='输入PDF文件路径')
    parser.add_argument('output', help='输出PDF文件路径')
    
    args = parser.parse_args()
    
    try:
        extractor = PDFVocabularyExtractor()
        extractor.process_pdf(args.input, args.output)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()