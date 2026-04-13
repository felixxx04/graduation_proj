# 毕业设计说明书格式规范

> 本规范整合了参考文档格式、毕设模板格式和用户要求，每次修改毕设时必须遵循。

## 一、文档结构

### 1.1 整体结构

```
1. 空白首页
2. 中文摘要
3. 英文摘要 (Abstract)
4. 目次
5. 正文（第1-6章）
6. 结论
7. 致谢
8. 参考文献
```

### 1.2 章节结构示例

```
第1章 绪论
  1.1 研究背景与意义
  1.2 国内外研究现状
    1.2.1 国内研究进展
    1.2.2 国际研究现状
    1.2.3 现有研究不足
  1.3 研究内容与论文结构
  1.4 本章小结

第2章 相关技术与理论基础
  2.1 xxx技术
    2.1.1 xxx定义
    2.1.2 xxx实现
  2.2 xxx技术
  ...
  2.x 本章小结

第3章 系统需求分析与设计
第4章 核心算法设计与实现
第5章 系统实现
第6章 系统测试与分析

结论
致谢
参考文献
```

**重要：每章末尾必须有"本章小结"**

---

## 二、页面设置

| 设置项 | 值 |
|--------|-----|
| 纸张大小 | A4 (21×29.7cm) |
| 上边距 | 2.54cm |
| 下边距 | 2.08cm |
| 左边距 | 2.0cm |
| 右边距 | 0.75cm |
| 页脚距离 | 1.74cm |
| 页码 | 页脚居中，阿拉伯数字 |

---

## 三、字体规范

### 3.1 标题字体

| 元素 | 中文字体 | 英文字体 | 字号 | 加粗 | 对齐 |
|------|---------|---------|------|------|------|
| 章标题（1 绪论） | 黑体 | Times New Roman | 小三号(15pt) | 是 | 左对齐 |
| 节标题（1.1 xxx） | 黑体 | Times New Roman | 四号(14pt) | 是 | 左对齐 |
| 条标题（1.1.1 xxx） | 黑体 | Times New Roman | 小四号(12pt) | 是 | 左对齐 |

### 3.2 特殊标题字体

| 元素 | 中文字体 | 英文字体 | 字号 | 加粗 | 对齐 |
|------|---------|---------|------|------|------|
| 摘要标题 | 黑体 | Times New Roman | 小三号(15pt) | 是 | 居中 |
| 目次标题 | 黑体 | Times New Roman | 小三号(15pt) | 是 | 居中 |
| 结论标题 | 黑体 | Times New Roman | 小三号(15pt) | 是 | 居中 |
| 致谢标题 | 黑体 | Times New Roman | 小三号(15pt) | 是 | 居中 |
| 参考文献标题 | 黑体 | Times New Roman | 小三号(15pt) | 是 | 居中 |

### 3.3 正文字体

| 元素 | 中文字体 | 英文字体 | 字号 | 对齐 |
|------|---------|---------|------|------|
| 正文 | 宋体 | Times New Roman | 小四号(12pt) | 两端对齐 |
| 参考文献 | 宋体 | Times New Roman | 五号(10.5pt) | 左对齐 |
| 目录内容 | 宋体 | Times New Roman | 小四号(12pt) | 左对齐 |

### 3.4 字号与磅值对照

| 中文字号 | 磅值 |
|---------|------|
| 小三号 | 15pt |
| 四号 | 14pt |
| 小四号 | 12pt |
| 五号 | 10.5pt |

---

## 四、段落格式

### 4.1 标准设置

| 元素 | 段前 | 段后 | 行距 | 首行缩进 |
|------|------|------|------|----------|
| 章标题 | 0 | 0 | 1.5倍 | 无 |
| 节标题 | 0 | 0 | 1.5倍 | 无 |
| 条标题 | 0 | 0 | 1.5倍 | 无 |
| 正文 | 0 | 0 | 1.5倍 | 2字符(约0.85cm) |
| 参考文献 | 0 | 0 | 1.5倍 | 无 |

**重要：段前段后间距统一为0，行距统一为1.5倍**

### 4.2 特殊段落

- 摘要正文：首行缩进2字符
- 关键词：首行缩进2字符，格式为"关键词：xxx；xxx；xxx"
- 目录条目：无缩进，使用"............"连接页码

---

## 五、内容规范

### 5.1 摘要要求

- **中文摘要**：约400字
- **英文摘要**：约300词
- **结构**：研究背景 → 技术方案 → 主要成果 → 结论意义
- **关键词**：3-5个，用分号分隔

### 5.2 字数要求

| 项目 | 要求 |
|------|------|
| 总字数 | 8000-15000字（推荐15000-20000字） |
| 参考文献 | ≥15篇（≥2篇外文） |

### 5.3 各章节字数建议

| 章节 | 建议字数 | 占比 |
|------|---------|------|
| 第1章 绪论 | 2000-2500字 | ~15% |
| 第2章 相关技术与理论基础 | 2500-3000字 | ~18% |
| 第3章 系统需求分析与设计 | 2500-3000字 | ~18% |
| 第4章 核心算法设计与实现 | 3000-3500字 | ~22% |
| 第5章 系统实现 | 2000-2500字 | ~15% |
| 第6章 系统测试与分析 | 1500-2000字 | ~12% |

### 5.4 参考文献格式

```
期刊类: [序号] 作者. 论文题目[J]. 期刊名, 年, 卷(期): 起止页码
图书类: [序号] 作者. 书名. 出版地: 出版社, 年, 页码
外文类: [序号] Author. Title[J]. Journal, Year, Vol(Issue): Pages
```

---

## 六、写作规范

### 6.1 文献引用格式

- 使用 `作者[编号]` 格式，如"张三[1]在2024年提出..."
- 或 `文献[编号]` 格式，如"根据文献[2]的研究..."

### 6.2 语言风格

- 使用正式学术语言，避免口语化表达
- 多用"本文"、"本研究"、"本文提出"等表述
- 引用文献时使用"xxx等人"、"xxx等"格式

### 6.3 章节开头

每章开头应有引导段落（约100-200字），概述本章内容和目的。

### 6.4 章节结尾

每章末尾必须有"本章小结"小节，总结本章主要内容（约300-500字）。

---

## 七、Python实现参考

```python
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

def set_font(run, chinese_font, english_font, size_pt, bold=False):
    """设置字体"""
    run.font.name = english_font
    run._element.rPr.rFonts.set(qn('w:eastAsia'), chinese_font)
    run.font.size = Pt(size_pt)
    run.font.bold = bold

def add_paragraph(doc, text, style='body'):
    """添加段落"""
    para = doc.add_paragraph()
    run = para.add_run(text)

    # 统一设置：段前段后0，行距1.5倍
    para.paragraph_format.space_before = Pt(0)
    para.paragraph_format.space_after = Pt(0)
    para.paragraph_format.line_spacing = 1.5

    if style == 'chapter':
        set_font(run, '黑体', 'Times New Roman', 15, True)
        para.paragraph_format.first_line_indent = Cm(0)
    elif style == 'section':
        set_font(run, '黑体', 'Times New Roman', 14, True)
        para.paragraph_format.first_line_indent = Cm(0)
    elif style == 'subsection':
        set_font(run, '黑体', 'Times New Roman', 12, True)
        para.paragraph_format.first_line_indent = Cm(0)
    elif style == 'center':
        set_font(run, '黑体', 'Times New Roman', 15, True)
        para.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        para.paragraph_format.first_line_indent = Cm(0)
    else:  # body
        set_font(run, '宋体', 'Times New Roman', 12, False)
        para.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        para.paragraph_format.first_line_indent = Cm(0.85)

    return para

def add_page_number(section):
    """添加页码"""
    footer = section.footer
    footer.is_linked_to_previous = False
    for para in footer.paragraphs:
        para.clear()
    para = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = para.add_run()

    # 创建页码域
    fldChar1 = OxmlElement('w:fldChar')
    fldChar1.set(qn('w:fldCharType'), 'begin')
    instrText = OxmlElement('w:instrText')
    instrText.text = 'PAGE'
    fldChar2 = OxmlElement('w:fldChar')
    fldChar2.set(qn('w:fldCharType'), 'end')

    run._r.append(fldChar1)
    run._r.append(instrText)
    run._r.append(fldChar2)
    run.font.name = 'Times New Roman'
    run.font.size = Pt(10.5)

def setup_document(doc):
    """设置文档页面"""
    section = doc.sections[0]
    section.page_height = Cm(29.7)
    section.page_width = Cm(21.0)
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.08)
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(0.75)
    section.footer_distance = Cm(1.74)
```

---

## 八、检查清单

每次修改毕设后，确认以下事项：

- [ ] 空白首页是否存在
- [ ] 段前段后间距是否为0
- [ ] 行距是否为1.5倍
- [ ] 字体是否正确（标题黑体，正文宋体）
- [ ] 字号是否正确（章小三，节四号，正文小四）
- [ ] 每章是否有"本章小结"
- [ ] 首行缩进是否正确（正文2字符，标题无缩进）
- [ ] 页码是否添加且居中
- [ ] 参考文献格式是否规范
- [ ] 字数是否达标（8000-15000字）
