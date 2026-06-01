"""知识库 RAG 配置校验与归一化"""

from app.models.knowledge_base import DEFAULT_RAG_CONFIG


def normalize_rag_config(raw: dict | None) -> dict:
    """归一化 RAG 配置，非法值抛出 ValueError"""
    if not raw:
        return dict(DEFAULT_RAG_CONFIG)

    cfg = dict(DEFAULT_RAG_CONFIG)
    cfg.update(raw)

    # top_k: 1~20
    top_k = cfg.get("top_k", 5)
    if not isinstance(top_k, int) or top_k < 1 or top_k > 20:
        raise ValueError("top_k 必须是 1~20 的整数")
    cfg["top_k"] = top_k

    # score_threshold: 0~1
    st = cfg.get("score_threshold", 0.0)
    if not isinstance(st, (int, float)) or st < 0 or st > 1:
        raise ValueError("score_threshold 必须是 0~1 的数值")
    cfg["score_threshold"] = float(st)

    # chunk_size: 300~3000
    cs = cfg.get("chunk_size", 1000)
    if not isinstance(cs, int) or cs < 300 or cs > 3000:
        raise ValueError("chunk_size 必须是 300~3000 的整数")
    cfg["chunk_size"] = cs

    # chunk_overlap: 0~500 且 < chunk_size
    co = cfg.get("chunk_overlap", 150)
    if not isinstance(co, int) or co < 0 or co > 500:
        raise ValueError("chunk_overlap 必须是 0~500 的整数")
    if co >= cs:
        raise ValueError("chunk_overlap 必须小于 chunk_size")
    cfg["chunk_overlap"] = co

    # no_evidence_policy
    nep = cfg.get("no_evidence_policy", "strict")
    if nep not in ("strict", "balanced"):
        raise ValueError("no_evidence_policy 必须是 strict 或 balanced")
    cfg["no_evidence_policy"] = nep

    return cfg


def get_effective_rag_config(kb_rag_config: dict | None) -> dict:
    """获取生效的 RAG 配置，兼容旧知识库（无 rag_config）"""
    if not kb_rag_config:
        return dict(DEFAULT_RAG_CONFIG)
    try:
        return normalize_rag_config(kb_rag_config)
    except ValueError:
        return dict(DEFAULT_RAG_CONFIG)
