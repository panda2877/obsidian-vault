#!/usr/bin/env python3
"""
Word 文档格式化工具 — 公文格式规范版（v4 递归区间层级识别）
========================================================
根据党政机关公文格式规范，自动格式化 Word 文档。

格式规范：
  • 标题：     方正小标宋_GBK 二号（22pt），居中
  • 一级标题： 黑体 三号（16pt）
  • 二级标题： 楷体_GB2312 三号（16pt）
  • 三级标题： 仿宋_GB2312 三号（16pt）
  • 四级标题： 仿宋_GB2312 三号（16pt）
  • 正文：     仿宋_GB2312 三号（16pt），首行缩进2字符，行距固定28磅

v4 改进：
  - 递归区间划分：先全局找 h1，再在每个 h1 之间独立找 h2，递归类推
  - 无编号标题 = 当前递归层的格式
  - 每个同级标题之间的区间独立遍历

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
FONT_DIR = os.path.dirname(os.path.abspath(__file__))

FONT_FILES = {
    '方正小标宋_GBK': '方正小标宋_GBK.TTF',
    '仿宋_GB2312':    '仿宋_GB2312.TTF',
    '黑体':           '黑体_GB18030.TTF',
    '楷体_GB2312':    '楷体_GB2312.TTF',
}

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

FONT_SIZES = {
    'title': Pt(22),
    'h1':    Pt(16),
    'h2':    Pt(16),
    'h3':    Pt(16),
    'h4':    Pt(16),
    'body':  Pt(16),
}

FONT_BOLD = {
    'title': False,
    'h1':    False,
    'h2':    False,
    'h3':    False,
    'h4':    False,
    'body':  False,
}

ALIGNMENT = {
    'title': WD_ALIGN_PARAGRAPH.CENTER,
    'h1':    WD_ALIGN_PARAGRAPH.LEFT,
    'h2':    WD_ALIGN_PARAGRAPH.LEFT,
    'h3':    WD_ALIGN_PARAGRAPH.LEFT,
    'h4':    WD_ALIGN_PARAGRAPH.LEFT,
    'body':  WD_ALIGN_PARAGRAPH.JUSTIFY,
}

LINE_SPACING_FIXED = Pt(28)
FIRST_LINE_INDENT = Pt(32)
MAX_TITLE_LENGTH = 60

LEVEL_NAMES = ['h1', 'h2', 'h3', 'h4']


# ═══════════════════════════════════════════════════════════════════
# 编号风格分类
# ═══════════════════════════════════════════════════════════════════

def classify_numbering(text):
    """
    提取段落文本的编号风格。

    返回 (style_key, prefix_text)：
      style_key  — 用于聚类同层标题的标识
      prefix_text — 编号前缀原文
    无编号时返回 (None, None)。
    """
    # 多级编号 1.1, 2.3.1（需在 arabic_dot 之前检查）
    m = re.match(r'^(\d+\.\d+)', text)
    if m:
        return ('arabic_multi', m.group(1))

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

    # 阿拉伯数字 + ．.、)）
    m = re.match(r'^(\d+[．.、)）])', text)
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
    2. 不含 。！？
    3. 长度 ≤ MAX_TITLE_LENGTH
    4. 不以 ：结尾
    5. 不以 图/表/Fig/Table 开头（图片/表格标题）
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
    """找文档标题：第一段不含 。！？ 的文本段落。"""
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
# 标题候选收集
# ═══════════════════════════════════════════════════════════════════

class TitleCandidate:
    """标题候选，存储段落信息和分配结果。"""
    __slots__ = ('para', 'text', 'style_key', 'prefix', 'level')

    def __init__(self, para, text, style_key, prefix):
        self.para = para
        self.text = text
        self.style_key = style_key
        self.prefix = prefix
        self.level = None  # 由递归算法分配


def _get_paragraph_numbering(para):
    """
    检测段落是否有 Word 自动编号。

    返回风格标识字符串（如 'auto_3_0' = numId=3, ilvl=0），
    无自动编号时返回 None。
    """
    pPr = para._element.find(qn('w:pPr'))
    if pPr is None:
        return None
    numPr = pPr.find(qn('w:numPr'))
    if numPr is None:
        return None

    numId_el = numPr.find(qn('w:numId'))
    ilvl_el = numPr.find(qn('w:ilvl'))
    num_id = numId_el.get(qn('w:val')) if numId_el is not None else '0'
    ilvl = ilvl_el.get(qn('w:val')) if ilvl_el is not None else '0'
    return f'auto_{num_id}_{ilvl}'


def _find_image_paragraphs(doc):
    """
    找出所有包含图片的段落，返回这些段落 element 的集合。

    检测 w:drawing 和 w:pict 元素（Word 内嵌图片的两种存储方式）。
    """
    image_paras = set()
    for para in doc.paragraphs:
        drawing = para._element.findall('.//' + qn('w:drawing'))
        pict = para._element.findall('.//' + qn('w:pict'))
        if drawing or pict:
            image_paras.add(para._element)
    return image_paras


def collect_candidates(doc, title_para):
    """
    收集文档中所有标题候选（排除文档标题、TOC 和图片相邻段落）。
    """
    # 预扫描：找出所有图片段落及其前后相邻段落
    image_paras = _find_image_paragraphs(doc)
    adjacent_to_image = set()
    all_paras = list(doc.paragraphs)
    for i, para in enumerate(all_paras):
        if para._element in image_paras:
            if i > 0:
                adjacent_to_image.add(all_paras[i - 1]._element)
            if i + 1 < len(all_paras):
                adjacent_to_image.add(all_paras[i + 1]._element)

    candidates = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        if _is_toc_paragraph(para):
            continue
        if title_para is not None and para._element is title_para._element:
            continue
        # 跳过图片相邻段落（图题/表题/图示说明）
        if para._element in adjacent_to_image:
            continue
        # 跳过自身包含图片的段落
        if para._element in image_paras:
            continue
        if not is_title_candidate(text):
            continue

        style_key, prefix = classify_numbering(text)

        # 如果纯文本无编号，检查是否有 Word 自动编号
        if style_key is None:
            num_key = _get_paragraph_numbering(para)
            if num_key:
                style_key = num_key
                prefix = f'[{num_key}]'

        candidates.append(TitleCandidate(para, text, style_key, prefix))

    return candidates


# ═══════════════════════════════════════════════════════════════════
# 递归区间层级分配（v4 核心）
# ═══════════════════════════════════════════════════════════════════

def _assign_level(candidates, start, end, parent_style, level_idx):
    """
    在 [start, end) 区间内递归分配层级。

    参数：
        candidates   — 标题候选列表
        start, end   — 当前区间范围
        parent_style — 父层级的编号风格（用于排除）
        level_idx    — 当前要分配的层级索引（0=h1, 1=h2, 2=h3, 3=h4）

    逻辑：
        1. 无编号标题 → 当前层级
        2. 第一个有编号的标题 → 当前层级的风格
        3. 区间内同风格 → 同层级
        4. 在有编号的标题之间递归下一层
    """
    if start >= end:
        return

    # 超过 h4 层级 → 全部归入 h4（最深层级）
    if level_idx >= 4:
        for i in range(start, end):
            if candidates[i].level is None:
                candidates[i].level = 'h4'
        return

    # 在当前区间找第一个有编号的候选（不同父风格）
    level_style = None
    split_indices = []

    for i in range(start, end):
        c = candidates[i]
        if c.level is not None:
            continue

        if c.style_key and c.style_key != parent_style:
            level_style = c.style_key
            break

    if level_style is None:
        # 区间内没有有编号的标题 → 全部设为当前层级
        for i in range(start, end):
            if candidates[i].level is None:
                candidates[i].level = LEVEL_NAMES[level_idx]
        return

    # 遍历区间：分配当前层级
    for i in range(start, end):
        c = candidates[i]
        if c.level is not None:
            continue

        if c.style_key == level_style:
            c.level = LEVEL_NAMES[level_idx]
            split_indices.append(i)
        elif c.style_key is None:
            # 无编号标题 → 当前层级
            c.level = LEVEL_NAMES[level_idx]
        # 其他有编号风格 → 暂不处理（留给更深递归）

    # 在 split_indices 之间递归下一层
    # 同时处理第一个 split 之前的区间（可能有其他编号风格）
    prev = start
    for idx in split_indices:
        if prev < idx:
            _assign_level(candidates, prev, idx, level_style, level_idx + 1)
        prev = idx + 1
    if prev < end:
        _assign_level(candidates, prev, end, level_style, level_idx + 1)


def assign_all_levels(candidates):
    """
    对所有标题候选分配层级（h1~h4）。

    先从全局找 h1 风格，再在每个 h1 之间递归找 h2/h3/h4。
    """
    if not candidates:
        return

    # 全局找 h1：第一个有编号的候选
    h1_style = None
    h1_indices = []

    for c in candidates:
        if c.style_key:
            h1_style = c.style_key
            break

    if h1_style is None:
        # 全文档都没有有编号的标题 → 全部 h1
        for c in candidates:
            c.level = 'h1'
        return

    # 分配 h1
    for i, c in enumerate(candidates):
        if c.style_key == h1_style:
            c.level = 'h1'
            h1_indices.append(i)

    # 在每个 h1 之间递归分配 h2/h3/h4
    for j in range(len(h1_indices)):
        sub_start = h1_indices[j] + 1
        if j + 1 < len(h1_indices):
            sub_end = h1_indices[j + 1]
        else:
            sub_end = len(candidates)
        _assign_level(candidates, sub_start, sub_end, h1_style, 1)


# ═══════════════════════════════════════════════════════════════════
# 字体设置
# ═══════════════════════════════════════════════════════════════════

def _set_run_font(run, font_name, font_size, bold=False):
    """设置单个 run 的字体属性。"""
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

    # 显式移除加粗（确保覆盖原文样式）
    b_elem = rPr.find(qn('w:b'))
    if not bold:
        if b_elem is not None:
            rPr.remove(b_elem)
        # 同时移除 w:bCs（复杂脚本加粗）
        bCs = rPr.find(qn('w:bCs'))
        if bCs is not None:
            rPr.remove(bCs)
    else:
        if b_elem is None:
            b_elem = OxmlElement('w:b')
            rPr.append(b_elem)


def _set_paragraph_format(paragraph, alignment, line_spacing=None, first_line_indent=None):
    """设置段落格式。"""
    paragraph.alignment = alignment
    pf = paragraph.paragraph_format

    if line_spacing is not None:
        pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
        pf.line_spacing = line_spacing

    if first_line_indent is not None:
        pf.first_line_indent = first_line_indent


def apply_style(paragraph, level):
    """对段落应用指定层级的完整格式。"""
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
# 主流程（v4 重写）
# ═══════════════════════════════════════════════════════════════════

def format_document(doc):
    """
    三遍扫描格式化文档。

    第一遍：找文档标题。
    第二遍：收集标题候选，递归分配层级。
    第三遍：逐段应用格式。
    """
    # ── 第一遍：找标题 ──
    title_para, title_text = find_title_paragraph(doc)
    if title_para is not None:
        print(f"  识别标题：「{title_text[:40]}{'…' if len(title_text) > 40 else ''}」")

    # ── 第二遍：收集标题候选 + 递归分配层级 ──
    candidates = collect_candidates(doc, title_para)
    assign_all_levels(candidates)

    # 打印分配结果
    if candidates:
        level_counts = {}
        for c in candidates:
            level_counts[c.level] = level_counts.get(c.level, 0) + 1
        # 过滤掉 None（未分配），防止 sorted 报错
        sorted_items = sorted((lvl, cnt) for lvl, cnt in level_counts.items() if lvl is not None)
        parts = [f"    {lvl}×{cnt}" for lvl, cnt in sorted_items]
        if parts:
            print(f"  标题分配：{' '.join(parts)}")
        unassigned = [c for c in candidates if c.level is None]
        if unassigned:
            print(f"  ⚠️ 有 {len(unassigned)} 个候选未分配层级：")
            for c in unassigned:
                print(f"    「{c.text[:40]}」")
        for c in candidates:
            prefix_info = f"[{c.prefix}]" if c.prefix else "[无编号]"
            level_str = c.level if c.level else 'None'
            print(f"    {level_str:4s} {prefix_info:12s} {c.text[:40]}")

    # 构建段落→层级查找表
    para_level = {}
    for c in candidates:
        para_level[c.para._element] = c.level

    # ── 第三遍：逐段应用格式 ──
    title_applied = False

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        if _is_toc_paragraph(para):
            continue

        # 判断层级
        if not title_applied and title_para is not None and para._element is title_para._element:
            level = 'title'
            title_applied = True
        elif para._element in para_level:
            level = para_level[para._element]
        else:
            level = 'body'

        apply_style(para, level)

    if not title_applied:
        print("  未找到明确的标题段落。")
    else:
        print("  标题格式已应用。")


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
    try:
        input("\n按 Enter 键退出……")
    except EOFError:
        pass


if __name__ == '__main__':
    main()