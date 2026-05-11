#!/usr/bin/env python3
"""
Word 文档格式化工具
====================
根据指定格式规范，自动格式化 Word 文档的标题、层级标题和正文。

格式规范：
  • 标题：     宋体 二号（22pt），居中
  • 一级标题： 黑体 三号（16pt），中文数字+"、"
  • 二级标题： 仿宋_GB2312 三号（16pt），"(中文数字）"
  • 三级标题： 仿宋_GB2312 三号（16pt），阿拉伯数字+"."
  • 四级标题： 仿宋_GB2312 三号（16pt），"(阿拉伯数字）"
  • 正文：     仿宋_GB2312 三号（16pt），首行缩进2字符，行距固定28磅

层次规则：按顺序使用，可跳跃不可逆序。

使用方法：
    python3 format_word.py <输入文件.docx> [输出文件.docx]

    若不指定输出文件，默认在输入文件同目录生成 "格式化_<原文件名>.docx"。

依赖：python-docx（apt install python3-docx 或 pip install python-docx）
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
# 说明：字体文件优先使用脚本同文件夹下的文件。
# 请将以下字体文件下载到本脚本所在目录，并填写文件名：
#
#   FONT_FILES = {
#       '宋体': 'simsun.ttf',              # ← 请补全文件名
#       '黑体': 'simhei.ttf',              # ← 请补全文件名
#       '仿宋_GB2312': 'fangsong.ttf',     # ← 请补全文件名
#   }
#
# 留空 = 使用系统字体名称（Word 打开时自动匹配系统已安装字体）。

FONT_DIR = os.path.dirname(os.path.abspath(__file__))

FONT_FILES = {
    '宋体': None,          # TODO: 填写字体文件名
    '黑体': None,          # TODO: 填写字体文件名
    '仿宋_GB2312': None,  # TODO: 填写字体文件名
}

# 字体名称（写入 docx XML，Word 根据此名称渲染）
FONT_NAMES = {
    'title': '宋体',
    'h1':    '黑体',
    'h2':    '仿宋_GB2312',
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
    'h1':    True,     # 一级标题黑体加粗
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

    返回：
        'title'  — 文档标题（无序号的首段）
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

    # 一级标题：中文数字 + "、"
    if re.match(r'^[一二三四五六七八九十百千]+、', text):
        return 'h1'

    # 二级标题："（" + 中文数字 + "）"
    if re.match(r'^（[一二三四五六七八九十百千]+）', text):
        return 'h2'

    # 三级标题：阿拉伯数字 + "."（后面有空格或紧跟文字）
    if re.match(r'^\d+\.\s', text):
        return 'h3'

    # 四级标题："(" + 阿拉伯数字 + ")"
    if re.match(r'^\(\d+\)', text):
        return 'h4'

    return 'body'


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
# 主流程
# ═══════════════════════════════════════════════════════════════════

def format_document(doc):
    """
    遍历文档所有段落，检测层级并应用格式。

    特殊规则：
    - 第一个非空段落若未匹配任何标题模式，视为文档标题（title）
    - 空段落跳过
    """
    first_para = True

    for para in doc.paragraphs:
        text = para.text.strip()

        # 空段落跳过
        if not text:
            continue

        # 检测层级
        level = detect_level(text)

        # 第一个非空段落且未匹配标题模式 → 视为文档标题
        if first_para and level == 'body':
            level = 'title'
            first_para = False
        elif level != 'body':
            first_para = False

        apply_style(para, level)

    return doc


def main():
    if len(sys.argv) < 2:
        print("用法：python3 format_word.py <输入文件.docx> [输出文件.docx]")
        sys.exit(1)

    input_path = sys.argv[1]

    if not os.path.isfile(input_path):
        print(f"错误：文件不存在 — {input_path}")
        sys.exit(1)

    if not input_path.lower().endswith('.docx'):
        print(f"错误：仅支持 .docx 格式 — {input_path}")
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


if __name__ == '__main__':
    main()