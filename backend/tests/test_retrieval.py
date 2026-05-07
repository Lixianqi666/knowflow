from app.services.retrieval import _tokenize


def test_tokenize_chinese():
    tokens = _tokenize("请假流程是什么")
    assert "请假" in tokens
    assert "流程" in tokens
    # 停用词被过滤
    assert "什么" not in tokens


def test_tokenize_english():
    tokens = _tokenize("how to upload documents")
    assert "upload" in tokens
    assert "documents" in tokens
    assert "how" not in tokens
    assert "to" not in tokens


def test_tokenize_mixed():
    tokens = _tokenize("报销reimbursement流程")
    assert len(tokens) >= 1


def test_tokenize_short():
    tokens = _tokenize("ab")
    # 短于2字符的词被过滤
    assert len(tokens) == 0 or all(len(t) >= 2 for t in tokens)
