import pytest
from snips.ast import _match_replacement_reference, \
    _match_conditional_replacement


@pytest.mark.parametrize("ref,expected", [
    ('', ('', 0, False)),
    ('asdf', ('', 0, False)),
    ('123', ('', 0, False)),
    ('$qwe', ('', 0, False)),
    ('$1', ('match1', 2, True)),
    ('$10', ('match10', 3, True)),
    ('$14', ('', 3, True)),
    ('$123e', ('', 4, True)),
])
def test_match_replacement_reference(ref, expected):
    groups = [None] * 11
    groups[1] = 'match1'
    groups[10] = 'match10'
    res = _match_replacement_reference(ref, 0, groups)
    assert res == expected


@pytest.mark.parametrize("data,expected", [
    ('', ('', 0, False)),
    ('asdf', ('', 0, False)),
    ('()', ('', 0, False)),
    ('(3:asdf)', ('', 0, False)),
    ('(?:sdaf)', ('', 0, False)),
    ('(?d:sadf)', ('', 0, False)),
    ('(?2d:)', ('', 0, False)),
    ('(?2:)', ('', 5, True)),
    ('(?2:', ('', 0, False)),
    ('(?2:uu)', ('uu', 7, True)),
    ('(?2:uu)ddd', ('uu', 7, True)),
    ('(?3:uu:)', ('', 8, True)),
    ('(?3:uu:ii)', ('ii', 10, True)),
    ('(?2:$0:ii)', ('match0', 10, True)),
    (r'(?3:uu:\:=)', (':=', 11, True)),
    (r'(?2:\$0:ii)', ('$0', 11, True)),
    (r'(?2:0\):ii)', ('0)', 11, True)),
    (r'(?3:$0:\t\($10\)\n$a)', ('\\t(match10)\\n$a', 21, True)),
])
def test_match_conditinal_replacement(data, expected):
    groups = [None] * 11
    groups[2] = 'match2'
    groups[0] = 'match0'
    groups[10] = 'match10'

    res = _match_conditional_replacement(data, 0, groups)
    assert res == expected
