import re
import uuid

from app.config import settings


class DocumentChunker:
    """结构感知分块器

    - Markdown 标题感知（## 分段）
    - 代码块保持完整
    - 表格保持完整
    - 长段落后滑动窗口
    """

    def __init__(self, chunk_size: int | None = None, chunk_overlap: int | None = None):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

    def chunk(self, text: str, metadata: dict = None) -> list[dict]:
        if not text or not text.strip():
            return []

        sections = self._split_sections(text.strip())
        chunks = []
        current = ""
        current_idx = 0

        for sec in sections:
            # 如果当前块+新节超限，先 flush
            if current and len(current) + len(sec) > self.chunk_size:
                chunks.append((current, current_idx))
                current_idx += 1
                current = ""

            # 如果单节就超限，语义感知切分
            if len(sec) > self.chunk_size:
                if current:
                    chunks.append((current, current_idx))
                    current_idx += 1
                    current = ""
                for segment in self._semantic_split(sec):
                    chunks.append((segment, current_idx))
                    current_idx += 1
                continue

            current = f"{current}\n\n{sec}" if current else sec

        if current:
            chunks.append((current, current_idx))

        return [
            {"content": c, "metadata": metadata or {}, "index": i}
            for i, (c, _) in enumerate(chunks)
        ]

    def _semantic_split(self, text: str) -> list[str]:
        """按段落边界切分（无 Markdown 结构时的兜底策略）"""
        paragraphs = re.split(r"\n\n+", text)
        chunks = []
        buf = ""
        for p in paragraphs:
            p = p.strip()
            if not p:
                continue
            if buf and len(buf) + len(p) > self.chunk_size:
                chunks.append(buf)
                buf = ""
            if len(p) > self.chunk_size:
                if buf:
                    chunks.append(buf)
                    buf = ""
                for i in range(0, len(p), self.chunk_size - self.chunk_overlap):
                    chunks.append(p[i : i + self.chunk_size])
            else:
                buf = f"{buf}\n\n{p}" if buf else p
        if buf:
            chunks.append(buf)
        return chunks

    def _split_sections(self, text: str) -> list[str]:
        """按 Markdown 标题 / PDF 章节标题分割"""
        # 先分离代码块（整体保留）
        code_blocks: list[tuple[int, int, str]] = []
        cleaned = text
        for m in re.finditer(r"(```[\s\S]*?```|~~~[\s\S]*?~~~)", text):
            code_blocks.append((m.start(), m.end(), m.group()))
        # 用 UUID 占位符替换代码块，避免标题分割破坏
        placeholder_map: dict[str, str] = {}
        for _, _, block in code_blocks:
            ph = f"__CB_{uuid.uuid4().hex}__"
            placeholder_map[ph] = block
            cleaned = cleaned.replace(block, ph, 1)

        # 按 markdown 标题 / PDF 章节标题分割
        sections = re.split(r"(?=\n#{1,4}\s|\n[A-Z][^。\n]{0,20}[:：]\s|^#{1,4}\s)", cleaned)
        # 还原代码块
        result = []
        for sec in sections:
            for ph, block in placeholder_map.items():
                sec = sec.replace(ph, block)
            s = sec.strip()
            if s:
                result.append(s)
        return result if result else [text]


chunker = DocumentChunker()
