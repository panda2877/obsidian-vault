def _group_runs_by_line(para):
    """
    将段落中的 runs 按行分组。

    返回 [(line_text, [run_index, ...]), ...]
    每个 tuple 对应一行：文本内容 + 该行包含的 run 索引列表。
    """
    lines = []
    current_runs = []
    current_text = []

    for i, run in enumerate(para.runs):
        has_br = run._element.find(qn('w:br')) is not None
        # 如果 run 的内容包含换行符，或 run 本身是换行符
        if has_br:
            # 如果有累积文本，结束当前行
            if current_text:
                lines.append((''.join(current_text), current_runs))
            current_runs = []
            current_text = []
            continue

        text = run.text
        # 检查文本内是否有换行符（可能出现在 run.text 中）
        while '\n' in text:
            idx = text.index('\n')
            current_text.append(text[:idx])
            current_runs.append(i)
            lines.append((''.join(current_text), current_runs))
            current_runs = []
            current_text = []
            text = text[idx + 1:]

        if text:
            current_text.append(text)
            current_runs.append(i)

    # 最后一行
    if current_text:
        lines.append((''.join(current_text), current_runs))

    return lines


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
    收集文档中所有标题候选（按行检测，排除 TOC 和图片题注）。
    """
    # 预扫描：找出所有图片段落
    image_paras = _find_image_paragraphs(doc)
    all_paras = list(doc.paragraphs)

    # 找出需要排除的图片题注段落：
    # 单行 + 无自动编号 + 与图片段落相邻
    caption_paras = set()
    for i, para in enumerate(all_paras):
        if para._element in image_paras:
            # 检查前一段
            if i > 0:
                prev = all_paras[i - 1]
                text = prev.text.strip()
                if text:
                    lines = text.split('\n')
                    is_single_line = len(lines) == 1
                    has_auto = _get_paragraph_numbering(prev) is not None
                    if is_single_line and not has_auto:
                        caption_paras.add(prev._element)
            # 检查后一段
            if i + 1 < len(all_paras):
                nxt = all_paras[i + 1]
                text = nxt.text.strip()
                if text:
                    lines = text.split('\n')
                    is_single_line = len(lines) == 1
                    has_auto = _get_paragraph_numbering(nxt) is not None
                    if is_single_line and not has_auto:
                        caption_paras.add(nxt._element)

    candidates = []
    for para in doc.paragraphs:
        full_text = para.text.strip()
        if not full_text:
            continue
        if _is_toc_paragraph(para):
            continue
        if title_para is not None and para._element is title_para._element:
            continue

        # 按行分组
        line_groups = _group_runs_by_line(para)

        for line_idx, (line_text, run_idxs) in enumerate(line_groups):
            text = line_text.strip()
            if not text:
                continue

            # 跳过图片题注
            if para._element in caption_paras and len(line_groups) == 1:
                continue

            if not is_title_candidate(text):
                continue

            style_key, prefix = classify_numbering(text)

            # 如果纯文本无编号，检查段落是否有 Word 自动编号
            if style_key is None:
                num_key = _get_paragraph_numbering(para)
                if num_key:
                    style_key = num_key
                    prefix = f'[{num_key}]'

            candidates.append(TitleCandidate(
                para, text, style_key, prefix,
                line_idx=line_idx, run_indices=run_idxs
            ))

    return candidates