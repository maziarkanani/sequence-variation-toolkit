import pytest
from sequence_variations import (
    repetition,
    transposition,
    retrograde,
    inversion,
    local_aux_changes,
    local_value_changes,
    fragmentation,
    extension,
)


def test_repetition_basic():
    pattern = [1, 2]
    seq = [0, 1, 2, 1, 2, 3]
    assert repetition(pattern, seq) == [1, 3]


def test_transposition_integers():
    pattern = [1, 2, 3]
    seq = [1, 2, 3, 2, 3, 4]
    res = transposition(pattern, seq)
    # Only the second occurrence is transposed by +1
    assert res == [{"position": 3, "offset": 1}]


def test_retrograde_pairs():
    pattern = [(1, "a"), (2, "b"), (3, "c")]
    # reversed both value and aux
    seq = [(3, "c"), (2, "b"), (1, "a"), (0, "x")]
    assert retrograde(pattern, seq) == [0]


def test_inversion_simple():
    # axis = 0
    pattern = [0, 1, -1]
    seq = [0, -1, 1, 0]
    assert inversion(pattern, seq) == [0]


def test_local_aux_changes():
    pattern = [(1, 1.0), (2, 1.0), (3, 1.0)]
    seq = [
        (1, 1.0),
        (2, 0.5),  # changed
        (3, 1.0),
        (1, 1.0),
    ]
    res = local_aux_changes(pattern, seq, max_changes=1)
    assert len(res) == 1
    assert res[0]["position"] == 0
    assert res[0]["changed"][0]["index"] == 1


def test_local_value_changes():
    pattern = [(1, 1.0), (2, 1.0), (3, 1.0)]
    seq = [
        (1, 1.0),
        (2, 1.0),
        (4, 1.0),  # changed primary
        (0, 1.0),
    ]
    res = local_value_changes(pattern, seq, max_changes=1)
    assert len(res) == 1
    assert res[0]["position"] == 0
    assert res[0]["changed"][0]["index"] == 2


def test_fragmentation_basic():
    pattern = [1, 2, 3, 4]
    seq = [1, 2, 4, 5]
    # can get [1,2,4] by removing index 2 (value 3)
    res = fragmentation(pattern, seq)
    assert len(res) == 1
    assert res[0]["position"] == 0
    assert res[0]["removed_indices"] == [2]


def test_extension_basic():
    pattern = [1, 2, 3]
    # insert 9 in the middle
    seq = [1, 9, 2, 3, 0]
    res = extension(pattern, seq, max_extra=2)
    assert len(res) == 1
    assert res[0]["position"] == 0
    added = res[0]["added"]
    assert len(added) == 1
    assert added[0]["index"] == 1
    assert added[0]["value"] == 9
