"""RAG 评测判定逻辑"""


def evaluate_rag_answer(
    answer: str,
    citations: list[dict],
    expected_answer: str | None = None,
    expected_citation_doc_ids: list[str] | None = None,
) -> tuple[bool, float, str | None]:
    """判定 RAG 回答是否符合预期。

    返回 (passed, score, failure_reason)
    """
    has_expected_answer = bool(expected_answer and expected_answer.strip())
    has_expected_citations = bool(expected_citation_doc_ids)

    # 两者都为空，无法评测
    if not has_expected_answer and not has_expected_citations:
        return False, 0.0, "评测用例缺少 expected_answer 或 expected_citation_doc_ids"

    answer_ok = False
    citation_ok = False

    # 检查 answer
    if has_expected_answer:
        # 简单包含判断：expected_answer 的关键片段出现在 answer 中
        keywords = [k.strip() for k in expected_answer.split() if len(k.strip()) >= 2]
        if keywords:
            matched = sum(1 for k in keywords if k in answer)
            answer_ok = matched / len(keywords) >= 0.5
        else:
            answer_ok = expected_answer.strip() in answer

    # 检查 citations
    if has_expected_citations:
        cited_doc_ids = {c.get("document_id") for c in citations if c.get("document_id")}
        expected_set = set(expected_citation_doc_ids)
        citation_ok = bool(cited_doc_ids & expected_set)

    # 判定
    if has_expected_answer and has_expected_citations:
        if answer_ok and citation_ok:
            return True, 1.0, None
        reasons = []
        if not answer_ok:
            reasons.append("回答未包含预期关键内容")
        if not citation_ok:
            reasons.append("未引用预期文档")
        return False, 0.0, "；".join(reasons)

    if has_expected_answer:
        if answer_ok:
            return True, 1.0, None
        return False, 0.0, "回答未包含预期关键内容"

    # has_expected_citations
    if citation_ok:
        return True, 1.0, None
    return False, 0.0, "未引用预期文档"
