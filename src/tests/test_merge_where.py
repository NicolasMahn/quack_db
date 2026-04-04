from api.chroma_access import merge_where


def test_merge_none():
    assert merge_where(None, None) is None


def test_merge_single():
    assert merge_where({"a": 1}, None) == {"a": 1}


def test_merge_and():
    assert merge_where({"a": 1}, {"b": 2}) == {"$and": [{"a": 1}, {"b": 2}]}
