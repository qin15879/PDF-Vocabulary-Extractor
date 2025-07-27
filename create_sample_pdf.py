#!/usr/bin/env python3
"""
创建示例PDF文件用于测试
"""

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

def create_sample_pdf(filename="sample.pdf"):
    """创建包含英文文本的示例PDF文件"""
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    # 设置字体
    c.setFont("Helvetica", 12)
    
    # 添加标题
    c.setFont("Helvetica-Bold", 16)
    c.drawString(1*inch, height - 1*inch, "Sample Document for Vocabulary Extraction")
    
    # 添加正文内容
    text = """
    This is a sample document containing various English words for testing 
    the vocabulary extraction functionality. The document includes common 
    words as well as some more complex vocabulary.
    
    Technology plays an important role in modern education. Students use 
    computers and smartphones to access information and complete assignments. 
    Communication has become easier with email and instant messaging.
    
    Learning new vocabulary helps improve language skills and comprehension. 
    Practice and repetition are essential for mastering any language.
    """
    
    # 分行写入文本
    lines = text.strip().split('\n')
    y_position = height - 2*inch
    
    for line in lines:
        if line.strip():
            c.setFont("Helvetica", 12)
            # 处理长行
            words = line.split()
            current_line = ""
            for word in words:
                test_line = current_line + word + " "
                if c.stringWidth(test_line) > width - 2*inch:
                    if current_line:
                        c.drawString(1*inch, y_position, current_line.strip())
                        y_position -= 0.2*inch
                        current_line = word + " "
                else:
                    current_line = test_line
            
            if current_line:
                c.drawString(1*inch, y_position, current_line.strip())
                y_position -= 0.3*inch
        else:
            y_position -= 0.2*inch
    
    c.save()
    print(f"示例PDF已创建: {filename}")

if __name__ == "__main__":
    create_sample_pdf()