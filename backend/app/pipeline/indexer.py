import logging
import re

import jieba

logger = logging.getLogger(__name__)


def _build_tsvector(content: str) -> str | None:
    """jieba 分词后构建 tsvector 字符串（空格分隔），保留中文单字"""
    import re

    import jieba

    words = jieba.cut_for_search(content)
    tokens = []
    for w in words:
        w = w.strip()
        if not w:
            continue
        # 短于2的英文/数字过滤，但中文单字保留（如人名"赵六"→"赵""六"）
        if len(w) < 2 and not re.search(r"[一-鿿]", w):
            continue
        tokens.append(w)
    return " ".join(tokens) if tokens else None
