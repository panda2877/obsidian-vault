#!/usr/bin/env python3
"""
Word 文档格式化工具 — 公文格式规范版（v2 智能标题识别）
========================================================
根据党政机关公文格式规范，自动格式化 Word 文档。

格式规范：
  • 标题：     方正小标宋_GBK 二号（22pt），居中
  • 一级标题： 黑体 三号（16pt），中文数字+"、"
  • 二级标题： 楷体_GB2312 三号（16pt），"(中文数字）"
  • 三级标题： 仿宋_GB2312 三号（16pt），阿拉伯数字+"."
  • 四级标题： 仿宋_GB2312 三号（16pt），"(阿拉伯数字）"
  • 正文：     仿宋_GB2312 三号（16pt），首行缩进2字符，行距固定28磅

层次规则：按顺序使用，可跳跃不可逆序。

v2 改进：
  - 全文预扫描识别标题（不再简单取"第一个非序号段落"）
  - 跳过 Word 自动目录
  - 层级状态机跟踪上下文

使用方法：
    format_word.exe <输入文件.docx> [输出文件.docx]

    若不指定输出文件，默认在输入文件同目录生成 "格式化_<原文件名>.docx"。
"""

import re
import os
import sys

from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


# ═══════════════════════════════════════════════════════════════════
# 配置区 — 字体文件
# ═══════════════════════════════════════════════════════════════════
# 字体文件优先使用本脚本所在目录下的文件。
# 请将以下字体文件放到本脚本同目录下：
#
#   方正小标宋_GBK → 方正小标宋_GBK.TTF
#   仿宋_GB2312    → 仿宋_GB2312.TTF
#   黑体           → 黑体_GB18030.TTF
#   楷体_GB2312    → 楷体_GB2312.TTF
#
# 若同目录下未找到对应字体文件，脚本将使用系统字体名称
# （Word 打开文档时自动匹配系统已安装字体）。

FONT_DIR = os.path.dirname(os.path.abspath(__file__))

FONT_FILES = {
    '方正小标宋_GBK': '方正小标宋_GBK.TTF',
    '仿宋_GB2312':    '仿宋_GB2312.TTF',
    '黑体':           '黑体_GB18030.TTF',
    '楷体_GB2312':    '楷体_GB2312.TTF',
}

# 字体名称（写入 docx XML，Word 根据此名称渲染）
FONT_NAMES = {
    'title': '方正小标宋_GBK',
    'h1':    '黑体',
    'h2':    '楷体_GB2312',
    'h3':    '仿宋_GB2312',
    'h4':    '仿宋_GB2312',
    'body':  '仿宋_GB2312',
}

# ═══════════════════════════════════════════════════════════════════
# 配置区 — 字号与格式参数
# ═══════════════════════════════════════════════════════════════════

# 字号（中文字号 → 磅值：二号=22pt, 三号=16pt）
FONT_SIZES = {
    'title': Pt(22),
    'h1':    Pt(16),
    'h2':    Pt(16),
    'h3':    Pt(16),
    'h4':    Pt(16),
    'body':  Pt(16),
}

# 粗体
FONT_BOLD = {
    'title': False,
    'h1':    True,
    'h2':    False,
    'h3':    False,
    'h4':    False,
    'body':  False,
}

# 对齐方式
ALIGNMENT = {
    'title': WD_ALIGN_PARAGRAPH.CENTER,
    'h1':    WD_ALIGN_PARAGRAPH.LEFT,
    'h2':    WD_ALIGN_PARAGRAPH.LEFT,
    'h3':    WD_ALIGN_PARAGRAPH.LEFT,
    'h4':    WD_ALIGN_PARAGRAPH.LEFT,
    'body':  WD_ALIGN_PARAGRAPH.JUSTIFY,
}

# 行距固定值 28 磅
LINE_SPACING_FIXED = Pt(28)

# 首行缩进 2 字符（三号字 16pt，2 字符 ≈ 32pt）
FIRST_LINE_INDENT = Pt(32)

# ═══════════════════════════════════════════════════════════════════
# 层级标题检测
# ═══════════════════════════════════════════════════════════════════

def detect_level(text):
    """
    根据段落文本检测标题层级。

    规则：
    - 标题段落不得包含句号、感叹号、问号（。！？）
    - 匹配序号模式后，若含上述标点则降为正文

    返回：
        'h1'     — 一级标题：一、 二、 三、 ……
        'h2'     — 二级标题：（一）（二）（三）……
        'h3'     — 三级标题：1. 2. 3. ……
        'h4'     — 四级标题：(1) (2) (3) ……
        'body'   — 正文
        None     — 空段落
    """
    text = text.strip()
    if not text:
        return None

    # 标题段落不得包含句号感叹号问号
    if re.search(r'[。！？]', text):
        return 'body'

    # 一级标题：中文数字 + "、"
    if re.match(r'^[一二三四五六七八九十百千]+、', text):
        return 'h1'

    # 二级标题："（" + 中文数字 + "）"
    if re.match(r'^（[一二三四五六七八九十百千]+）', text):
        return 'h2'

    # 三级标题：阿拉伯数字 + "."（后面有空格）
    if re.match(r'^\d+\.\s', text):
        return 'h3'

    # 四级标题："(" + 阿拉伯数字 + ")"
    if re.match(r'^\(\d+\)', text):
        return 'h4'

    return 'body'


# ═══════════════════════════════════════════════════════════════════
# 标题预扫描
# ═══════════════════════════════════════════════════════════════════

def _is_toc_paragraph(para):
    """判断是否为 Word 自动生成的目录段落。"""
    style = para.style
    if style and style.name and style.name.startswith('TOC'):
        return True
    # 也检查 XML 中的样式 ID
    pPr = para._element.find(qn('w:pPr'))
    if pPr is not None:
        pStyle = pPr.find(qn('w:pStyle'))
        if pStyle is not None:
            val = pStyle.get(qn('w:val'))
            if val and val.startswith('TOC'):
                return True
    return False


def find_title_paragraph(doc):
    """
    第一遍扫描：找文档标题。

    规则：第一段不含句号感叹号问号的非空文本段落即为标题。
    （跳过 Word 自动目录段落）
    """
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        if _is_toc_paragraph(para):
            continue

        # 第一段有效文本
        if not re.search(r'[。！？]', text):
            return para, text
        else:
            # 第一段就含句号 → 文档没有明确的标题
            return None, None

    return None, None


# ═══════════════════════════════════════════════════════════════════
# 字体设置
# ═══════════════════════════════════════════════════════════════════

def _set_run_font(run, font_name, font_size, bold=False):
    """设置单个 run 的字体属性（中西文分别设置）。"""
    run.font.size = font_size
    run.font.bold = bold

    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = OxmlElement('w:rFonts')
        rPr.insert(0, rFonts)

    rFonts.set(qn('w:eastAsia'), font_name)  # 中文字体
    rFonts.set(qn('w:ascii'), font_name)     # 西文字体
    rFonts.set(qn('w:hAnsi'), font_name)     # 西文字体（ANSI）


def _set_paragraph_format(paragraph, alignment, line_spacing=None, first_line_indent=None):
    """设置段落格式（对齐、行距、缩进）。"""
    paragraph.alignment = alignment
    pf = paragraph.paragraph_format

    if line_spacing is not None:
        pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
        pf.line_spacing = line_spacing

    if first_line_indent is not None:
        pf.first_line_indent = first_line_indent


def apply_style(paragraph, level):
    """
    对段落应用指定层级的完整格式。

    参数：
        paragraph — docx Paragraph 对象
        level     — 'title' | 'h1' | 'h2' | 'h3' | 'h4' | 'body'
    """
    if level not in FONT_NAMES:
        return

    font_name = FONT_NAMES[level]
    font_size = FONT_SIZES[level]
    bold = FONT_BOLD[level]
    alignment = ALIGNMENT[level]

    # 正文需要行距和缩进，标题不需要
    if level == 'body':
        _set_paragraph_format(paragraph, alignment, LINE_SPACING_FIXED, FIRST_LINE_INDENT)
    else:
        _set_paragraph_format(paragraph, alignment)

    # 遍历所有 run 设置字体
    for run in paragraph.runs:
        _set_run_font(run, font_name, font_size, bold)


# ═══════════════════════════════════════════════════════════════════
# 主流程（v2 重写）
# ═══════════════════════════════════════════════════════════════════

# 层级数值映射（用于状态机比较）
LEVEL_NUM = {
    'title': 0,
    'h1':    1,
    'h2':    2,
    'h3':    3,
    'h4':    4,
    'body':  5,
}


def format_document(doc):
    """
    两遍扫描格式化文档。

    第一遍：全文预扫描，智能识别标题。
    第二遍：逐段格式化，带层级状态机跟踪上下文。
    """
    # ── 第一遍：找标题 ──
    title_para, title_text = find_title_paragraph(doc)
    if title_para is not None:
        print(f"  识别标题：「{title_text[:40]}{'…' if len(title_text) > 40 else ''}」")

    # ── 第二遍：逐段格式化 ──
    current_level = 'body'  # 当前所处的层级上下文
    title_applied = False   # 标题是否已应用

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        # 跳过 Word 自动目录
        if _is_toc_paragraph(para):
            continue

        # ── 判断层级 ──
        # 如果这个段落是识别出的标题（通过底层 XML 元素匹配）
        if not title_applied and title_para is not None and para._element is title_para._element:
            level = 'title'
            title_applied = True
        else:
            level = detect_level(text)

        # ── 层级状态机 ──
        if level != 'body':
            # 这是一个标题段落
            level_num = LEVEL_NUM[level]
            current_num = LEVEL_NUM[current_level]

            if level_num < current_num:
                # 回到更高级别（如 h3 → h1），新章节开始，允许
                pass
            # 同级或更深，都允许

            current_level = level
        else:
            # 正文段落
            level = 'body'

        apply_style(para, level)

    if not title_applied:
        print("  未找到明确的标题段落，使用默认正文格式。")
    else:
        print("  标题格式已应用。")

    return doc


def main():
    if len(sys.argv) < 2:
        print("用法：format_word.exe <输入文件.docx> [输出文件.docx]")
        print("示例：format_word.exe 报告.docx")
        print("       format_word.exe 报告.docx 已格式化_报告.docx")
        input("\n按 Enter 键退出……")
        sys.exit(1)

    input_path = sys.argv[1]

    if not os.path.isfile(input_path):
        print(f"错误：文件不存在 — {input_path}")
        input("\n按 Enter 键退出……")
        sys.exit(1)

    if not input_path.lower().endswith('.docx'):
        print(f"错误：仅支持 .docx 格式 — {input_path}")
        input("\n按 Enter 键退出……")
        sys.exit(1)

    # 输出路径
    if len(sys.argv) >= 3:
        output_path = sys.argv[2]
    else:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_格式化{ext}"

    print(f"📖 读取：{input_path}")
    doc = Document(input_path)

    print("🔧 格式化中……")
    format_document(doc)

    print(f"💾 保存：{output_path}")
    doc.save(output_path)

    print("✅ 完成！")
    input("\n按 Enter 键退出……")


if __name__ == '__main__':
    main()