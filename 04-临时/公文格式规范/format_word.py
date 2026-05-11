#!/usr/bin/env python3
"""
Word 文档格式化工具 — 公文格式规范版（v3 动态层级识别）
========================================================
根据党政机关公文格式规范，自动格式化 Word 文档。

格式规范：
  • 标题：     方正小标宋_GBK 二号（22pt），居中
  • 一级标题： 黑体 三号（16pt），加粗
  • 二级标题： 楷体_GB2312 三号（16pt）
  • 三级标题： 仿宋_GB2312 三号（16pt）
  • 四级标题： 仿宋_GB2312 三号（16pt）
  • 正文：     仿宋_GB2312 三号（16pt），首行缩进2字符，行距固定28磅

v3 改进：
  - 不再硬编码编号格式，而是动态分析文档中的编号风格
  - 同风格编号 = 同层级，不同风格 = 不同层级
  - 无编号标题 = 最深编号层级 + 1
  - 标题候选条件：不含 。！？、长度 ≤ 60、不以 ：结尾

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

# 标题候选最大长度
MAX_TITLE_LENGTH = 60


# ═══════════════════════════════════════════════════════════════════
# 编号风格分类
# ═══════════════════════════════════════════════════════════════════

def classify_numbering(text):
    """
    提取段落文本的编号风格。

    返回 (style_key, prefix_text)：
      style_key  — 用于聚类同层标题的标识
      prefix_text — 编号前缀原文（如 "一、" "（一）" "1."）
    无编号时返回 (None, None)。
    """
    # 中文数字 + 、．.
    m = re.match(r'^([一二三四五六七八九十百千]+[、．.])', text)
    if m:
        return ('chinese_dot', m.group(1))

    # 全角括号 + 中文数字
    m = re.match(r'^（([一二三四五六七八九十百千]+)）', text)
    if m:
        return ('chinese_bracket_full', f'（{m.group(1)}）')

    # 半角括号 + 中文数字
    m = re.match(r'^\(([一二三四五六七八九十百千]+)\)', text)
    if m:
        return ('chinese_bracket_half', f'({m.group(1)})')

    # 第X章/条/节/项/款
    m = re.match(r'^(第[一二三四五六七八九十百千\d]+[章条节项款])', text)
    if m:
        return ('chapter', m.group(1))

    # 多级编号 1.1, 2.3.1（需在 arabic_dot 之前检查）
    m = re.match(r'^(\d+\.\d+)', text)
    if m:
        return ('arabic_multi', m.group(1))

    # 阿拉伯数字 + ．.、)
    m = re.match(r'^(\d+[．.、)])', text)
    if m:
        return ('arabic_dot', m.group(1))

    # 全角括号 + 阿拉伯数字
    m = re.match(r'^（(\d+)）', text)
    if m:
        return ('arabic_bracket_full', f'（{m.group(1)}）')

    # 半角括号 + 阿拉伯数字
    m = re.match(r'^\((\d+)\)', text)
    if m:
        return ('arabic_bracket_half', f'({m.group(1)})')

    return (None, None)


# ═══════════════════════════════════════════════════════════════════
# 标题候选判断
# ═══════════════════════════════════════════════════════════════════

def is_title_candidate(text):
    """
    判断一段文本是否为标题候选。

    条件：
    1. 非空
    2. 不含句号、感叹号、问号（。！？）
    3. 长度 ≤ MAX_TITLE_LENGTH
    4. 不以冒号结尾（"通知如下："这类过渡句排除）
    """
    text = text.strip()
    if not text:
        return False
    if re.search(r'[。！？]', text):
        return False
    if len(text) > MAX_TITLE_LENGTH:
        return False
    if text.endswith('：'):
        return False
    return True


# ═══════════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════════

def _is_toc_paragraph(para):
    """判断是否为 Word 自动生成的目录段落。"""
    style = para.style
    if style and style.name and style.name.startswith('TOC'):
        return True
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
    找文档标题。

    规则：第一段不含句号感叹号问号的非空文本段落即为标题。
    （跳过 Word 自动目录段落）
    """
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        if _is_toc_paragraph(para):
            continue
        if not re.search(r'[。！？]', text):
            return para, text
        else:
            return None, None
    return None, None


# ═══════════════════════════════════════════════════════════════════
# 层级映射构建（v3 核心）
# ═══════════════════════════════════════════════════════════════════

def build_level_map(doc, title_para):
    """
    扫描全文，构建编号风格 → 层级映射。

    规则：
    - 按首次出现顺序分配 h1/h2/h3/h4
    - 同风格编号 = 同层级
    - 不同风格 = 不同层级

    返回：
        level_map: {style_key: level_name}
        unnumbered_level: 无编号标题的默认层级
    """
    style_order = []
    seen_styles = set()

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        if _is_toc_paragraph(para):
            continue
        # 跳过文档标题段落
        if title_para is not None and para._element is title_para._element:
            continue
        if not is_title_candidate(text):
            continue

        style_key, _ = classify_numbering(text)
        if style_key and style_key not in seen_styles:
            seen_styles.add(style_key)
            style_order.append(style_key)

    # 分配层级
    level_names = ['h1', 'h2', 'h3', 'h4']
    level_map = {}
    for i, style_key in enumerate(style_order):
        if i < 4:
            level_map[style_key] = level_names[i]

    # 无编号标题的默认层级 = 最深编号层级 + 1
    num_levels = len(style_order)
    if num_levels == 0:
        unnumbered_level = 'h1'
    elif num_levels >= 4:
        unnumbered_level = 'h4'
    else:
        unnumbered_level = level_names[num_levels]

    return level_map, unnumbered_level


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

    rFonts.set(qn('w:eastAsia'), font_name)
    rFonts.set(qn('w:ascii'), font_name)
    rFonts.set(qn('w:hAnsi'), font_name)


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

    if level == 'body':
        _set_paragraph_format(paragraph, alignment, LINE_SPACING_FIXED, FIRST_LINE_INDENT)
    else:
        _set_paragraph_format(paragraph, alignment)

    for run in paragraph.runs:
        _set_run_font(run, font_name, font_size, bold)


# ═══════════════════════════════════════════════════════════════════
# 主流程（v3 重写）
# ═══════════════════════════════════════════════════════════════════

def format_document(doc):
    """
    两遍扫描格式化文档。

    第一遍：找文档标题 + 构建编号风格→层级映射。
    第二遍：逐段格式化。
    """
    # ── 第一遍：找标题 ──
    title_para, title_text = find_title_paragraph(doc)
    if title_para is not None:
        print(f"  识别标题：「{title_text[:40]}{'…' if len(title_text) > 40 else ''}」")

    # ── 第一遍：构建层级映射 ──
    level_map, unnumbered_level = build_level_map(doc, title_para)
    if level_map:
        print(f"  识别到 {len(level_map)} 种编号风格：")
        for style_key, level in level_map.items():
            print(f"    {style_key} → {level}")
        print(f"  无编号标题 → {unnumbered_level}")
    else:
        print("  未识别到编号标题，所有标题候选视为 h1")

    # ── 第二遍：逐段格式化 ──
    title_applied = False

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        # 跳过 Word 自动目录
        if _is_toc_paragraph(para):
            continue

        # ── 判断层级 ──
        if not title_applied and title_para is not None and para._element is title_para._element:
            level = 'title'
            title_applied = True
        elif is_title_candidate(text):
            style_key, _ = classify_numbering(text)
            if style_key and style_key in level_map:
                level = level_map[style_key]
            else:
                level = unnumbered_level
        else:
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