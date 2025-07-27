# PDF词汇提取器

一个简单易用的Python工具，从PDF文档中提取英文单词，查询释义和音标，生成词汇学习表。

## 功能特点

- 📖 从PDF提取英文文本
- 🔍 自动识别和提取英文单词
- 📚 查询单词释义和音标
- 📄 生成格式化的PDF词汇表
- ⚡ 简单易用，一键处理

## 安装

```bash
# 克隆项目
git clone [项目地址]
cd pdf-vocabulary-extractor

# 安装依赖
pip install -r requirements.txt
```

## 使用方法

### 基本使用

```bash
# 处理单个PDF文件
python extract_vocabulary.py input.pdf output.pdf

# 使用示例
python extract_vocabulary.py document.pdf vocabulary_list.pdf
```

### 创建测试文件

```bash
# 创建测试PDF
python test_sample.py

# 测试功能
python extract_vocabulary.py test_input.pdf vocabulary_output.pdf
```

## 输出格式

生成的PDF词汇表包含：
- **单词**：提取的英文单词
- **音标**：国际音标(IPA)
- **释义**：单词的中文释义

按字母顺序排序，便于查阅和学习。

## 技术说明

### 依赖库
- `pdfplumber` - PDF文本提取
- `reportlab` - PDF生成
- `requests` - 网络API调用

### 使用的API
- Free Dictionary API (https://dictionaryapi.dev/)
- 提供英文释义和音标信息

## 注意事项

- 需要网络连接以查询单词信息
- 处理大文件可能需要较长时间
- 建议使用稳定的网络环境

## 示例输出

处理完成后会显示：
```
正在处理: input.pdf
正在提取文本...
正在提取单词...
找到 45 个唯一单词
正在查询词典...
进度: 10/45
...
正在生成PDF...
完成！词汇表已保存到: output.pdf
总计处理了 45 个单词
```