# Sequence Variation Toolkit

A small, domain-agnostic toolkit for detecting **structured variations of a pattern inside a sequence**.

It operates on arbitrary sequences (lists, tuples, etc.) and provides detectors for:

- Exact repetition
- Transposition (constant offset in a numeric value)
- Retrograde (reversal)
- Inversion (reflection around an axis)
- Local auxiliary changes (same primary pattern, small changes in a secondary attribute)
- Local primary changes (same secondary attribute, small changes in primary value)
- Fragmentation (pattern with deletions)
- Extension (pattern with internal insertions)

The library is independent of any particular domain, but it is especially
convenient for symbolic time-series such as:

- Symbolic music (e.g. pitch–duration pairs, rhythmic patterns)
- Encoded event streams
- Discretised signals
- Any other token sequence where you care about structured variation

## Installation

Copy `sequence_variations.py` into your project or install it as part of
your own package. It has no third‑party dependencies.

## Quick examples

### 1. Plain integer sequences

```python
from sequence_variations import repetition, transposition

pattern = [1, 2, 3]
seq = [0, 1, 2, 3, 4, 2, 3, 4]

print(repetition(pattern, seq))
# -> [1]

# Integers are used directly as primary values, so this finds offsets:
print(transposition(pattern, seq))
# -> [{'position': 4, 'offset': 1}]
```

### 2. Pairs: (value, aux)

A common pattern is to represent each item as `(value, aux)` — for example:

- `(pitch, duration)` for symbolic music
- `(level, timestamp)` for events
- `(code, weight)` for labelled symbols

By default, the toolkit interprets the **first element** as the primary
value and the **second element** as the auxiliary attribute, but you can
override this with custom extractors.

```python
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

# (value, duration)
pattern = [(60, 1.0), (62, 0.5), (64, 0.5)]
seq = [
    (60, 1.0), (62, 0.5), (64, 0.5),
    (62, 1.0), (64, 0.5), (66, 0.5),
    (60, 1.0), (62, 0.25), (64, 0.5),
]

print(repetition(pattern, seq))
# exact matches of the full pattern

print(transposition(pattern, seq))
# same durations, constant offset in the first element

print(retrograde(pattern, seq))
print(inversion(pattern, seq))

print(local_aux_changes(pattern, seq))
print(local_value_changes(pattern, seq))

print(fragmentation(pattern, seq))
print(extension(pattern, seq))
```

For symbolic music, `value` might be pitch and `aux` duration, but the same
machinery works for any other type of labelled sequence.

## Testing

The repository includes a small `tests/test_sequence_variations.py` file
with `pytest`-style tests that demonstrate usage. To run them:

```bash
pip install pytest
pytest
```

## License

MIT (or adjust to your preference).
