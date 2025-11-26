from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional, Sequence, TypeVar

T = TypeVar("T")

# ----------------------------
# Internal helper functions
# ----------------------------

def _default_primary(x: Any) -> Any:
    """Default extractor for the primary value of an item.

    - If the item is a tuple, returns the first element.
    - Otherwise, returns the item itself.

    This is convenient for common cases like (value, aux) pairs, but the
    library works with any custom extractor you pass in.
    """
    if isinstance(x, tuple) and len(x) >= 1:
        return x[0]
    return x


def _default_aux(x: Any) -> Any:
    """Default extractor for an auxiliary value of an item.

    - If the item is a tuple of length >= 2, returns the second element.
    - Otherwise, returns None.

    Typical use: the aux component might represent duration, weight, etc.
    """
    if isinstance(x, tuple) and len(x) >= 2:
        return x[1]
    return None


# ----------------------------
# Core variation detectors
# ----------------------------

def repetition(
    pattern: Sequence[T],
    sequence: Sequence[T],
) -> List[int]:
    """Find all exact repetitions of *pattern* in *sequence*.

    Parameters
    ----------
    pattern:
        Subsequence to search for.
    sequence:
        Full sequence in which to search.

    Returns
    -------
    list of int
        Starting indices where `sequence[i:i+len(pattern)] == pattern`.
    """
    matches: List[int] = []
    L = len(pattern)
    N = len(sequence)
    if L == 0:
        return matches

    for i in range(N - L + 1):
        if list(sequence[i : i + L]) == list(pattern):
            matches.append(i)

    return matches


def transposition(
    pattern: Sequence[T],
    sequence: Sequence[T],
    value_fn: Callable[[T], float] = _default_primary,
    aux_fn: Callable[[T], Any] = _default_aux,
    require_same_aux: bool = True,
) -> List[Dict[str, Any]]:
    """Detect transposed occurrences of *pattern* in *sequence*.

    A transposed match is a contiguous subsequence where:

    - The auxiliary component (if `require_same_aux=True`) matches exactly;
    - The primary value differs from the pattern by a constant offset
      (the transposition amount) for every element.

    This is domain-agnostic: the *primary* component can be any numeric
    value (e.g. pitch, integer code, measurement); the *aux* component
    might be duration, weight, label, etc.

    Returns a list of dictionaries of the form::

        {
            "position": int,   # starting index in the sequence
            "offset": float,   # constant additive offset
        }
    """
    results: List[Dict[str, Any]] = []
    L = len(pattern)
    N = len(sequence)
    if L == 0:
        return results

    for i in range(N - L + 1):
        segment = sequence[i : i + L]

        # 1) Optional aux equality check
        if require_same_aux:
            if not all(aux_fn(segment[j]) == aux_fn(pattern[j]) for j in range(L)):
                continue

        # 2) Compute candidate offset from first element
        base_offset = value_fn(segment[0]) - value_fn(pattern[0])

        # skip trivial exact repetition (offset == 0)
        if base_offset == 0:
            continue

        # 3) Check consistent offset for all elements
        ok = True
        for j in range(L):
            if value_fn(segment[j]) - value_fn(pattern[j]) != base_offset:
                ok = False
                break

        if ok:
            results.append({"position": i, "offset": base_offset})

    return results


def retrograde(
    pattern: Sequence[T],
    sequence: Sequence[T],
    primary_fn: Callable[[T], Any] = _default_primary,
    aux_fn: Callable[[T], Any] = _default_aux,
    require_same_aux: bool = True,
) -> List[int]:
    """Detect retrograde (reversed) occurrences of *pattern*.

    A retrograde match is a contiguous subsequence equal to the reversed
    pattern, with optional equality on the auxiliary component.

    Returns
    -------
    list of int
        Starting indices of matches in `sequence`.
    """
    matches: List[int] = []
    L = len(pattern)
    N = len(sequence)
    if L == 0:
        return matches

    for i in range(N - L + 1):
        segment = sequence[i : i + L]
        ok = True
        for j in range(L):
            p = pattern[L - 1 - j]
            s = segment[j]
            if primary_fn(s) != primary_fn(p):
                ok = False
                break
            if require_same_aux and aux_fn(s) != aux_fn(p):
                ok = False
                break
        if ok:
            matches.append(i)

    return matches


def inversion(
    pattern: Sequence[T],
    sequence: Sequence[T],
    value_fn: Callable[[T], float] = _default_primary,
    aux_fn: Callable[[T], Any] = _default_aux,
    require_same_aux: bool = True,
) -> List[int]:
    """Detect inverted occurrences of *pattern* in *sequence*.

    Inversion is defined with respect to an *axis*:

    - The axis is the primary value of the first item of the pattern.
    - For each item with value `v`, its inversion is `axis - (v - axis)`.

    A match is a contiguous subsequence where:

    - The first primary value equals the axis;
    - The auxiliary component (if `require_same_aux`) matches exactly;
    - Every primary value equals the inversion of the corresponding
      pattern value around the axis.

    This is the standard notion of inversion used for many symbolic
    sequences (e.g. musical pitch inversion, mirrored measurements, etc.).
    """
    matches: List[int] = []
    L = len(pattern)
    N = len(sequence)
    if L == 0:
        return matches

    axis = value_fn(pattern[0])

    for i in range(N - L + 1):
        segment = sequence[i : i + L]

        # 1) First element must lie on the same axis
        if value_fn(segment[0]) != axis:
            continue

        # 2) Optional aux equality
        if require_same_aux:
            if not all(aux_fn(segment[j]) == aux_fn(pattern[j]) for j in range(L)):
                continue

        # 3) Check mirrored values
        ok = True
        for j in range(L):
            v = value_fn(pattern[j])
            expected = axis - (v - axis)
            if value_fn(segment[j]) != expected:
                ok = False
                break

        if ok:
            matches.append(i)

    return matches


def local_aux_changes(
    pattern: Sequence[T],
    sequence: Sequence[T],
    primary_fn: Callable[[T], Any] = _default_primary,
    aux_fn: Callable[[T], Any] = _default_aux,
    max_changes: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Detect local changes in the auxiliary component with fixed primary pattern.

    A match is a contiguous subsequence where:

    - The primary component is identical to that of `pattern`;
    - The auxiliary component may differ on up to `max_changes` positions;
    - At least one auxiliary value differs.

    Typical examples: same discrete values with slightly changed
    durations, weights, or other auxiliary fields.

    Returns a list of dicts of the form::

        {
            "position": int,            # starting index in the sequence
            "changed": [                # list of changed indices
                {"index": j, "new_aux": ...},
                ...
            ]
        }
    """
    results: List[Dict[str, Any]] = []
    L = len(pattern)
    N = len(sequence)
    if L == 0:
        return results

    if max_changes is None:
        max_changes = max(1, L // 4)

    for i in range(N - L + 1):
        segment = sequence[i : i + L]

        # 1) primary pattern must match exactly
        if not all(primary_fn(segment[j]) == primary_fn(pattern[j]) for j in range(L)):
            continue

        # 2) record aux changes
        changed = [
            {"index": j, "new_aux": aux_fn(segment[j])}
            for j in range(L)
            if aux_fn(segment[j]) != aux_fn(pattern[j])
        ]

        if 0 < len(changed) <= max_changes:
            results.append({"position": i, "changed": changed})

    return results


def local_value_changes(
    pattern: Sequence[T],
    sequence: Sequence[T],
    primary_fn: Callable[[T], Any] = _default_primary,
    aux_fn: Callable[[T], Any] = _default_aux,
    max_changes: Optional[int] = None,
    require_same_aux: bool = True,
) -> List[Dict[str, Any]]:
    """Detect local changes in the primary component with fixed auxiliary pattern.

    A match is a contiguous subsequence where:

    - The auxiliary component (if `require_same_aux`) matches exactly;
    - The primary component differs from the pattern on at least one
      position but at most `max_changes` positions.

    Returns a list of dicts of the form::

        {
            "position": int,
            "changed": [
                {"index": j, "new_value": ...},
                ...
            ]
        }
    """
    results: List[Dict[str, Any]] = []
    L = len(pattern)
    N = len(sequence)
    if L == 0:
        return results

    if max_changes is None:
        max_changes = max(1, L // 4)

    for i in range(N - L + 1):
        segment = sequence[i : i + L]

        if require_same_aux:
            if not all(aux_fn(segment[j]) == aux_fn(pattern[j]) for j in range(L)):
                continue

        changed = [
            {"index": j, "new_value": primary_fn(segment[j])}
            for j in range(L)
            if primary_fn(segment[j]) != primary_fn(pattern[j])
        ]

        if 0 < len(changed) <= max_changes:
            results.append({"position": i, "changed": changed})

    return results


# ----------------------------
# Fragmentation & extension
# ----------------------------

def _removed_positions_for_fragment(
    pattern: Sequence[T],
    fragment: Sequence[T],
) -> Optional[List[int]]:
    """Return indices removed from pattern to obtain fragment as a subsequence.

    If `fragment` is not a subsequence of `pattern` in order, returns None.
    Otherwise returns a list of indices in `pattern` that were skipped.
    """
    i = 0
    j = 0
    removed: List[int] = []
    Lp = len(pattern)
    Lf = len(fragment)

    while i < Lp and j < Lf:
        if pattern[i] == fragment[j]:
            i += 1
            j += 1
        else:
            removed.append(i)
            i += 1

    # anything left in pattern after fragment is matched is also removed
    while i < Lp:
        removed.append(i)
        i += 1

    return removed if j == Lf else None


def fragmentation(
    pattern: Sequence[T],
    sequence: Sequence[T],
    min_len: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Detect *fragmentations* of a pattern inside a sequence.

    A fragmentation is a contiguous subsequence of the sequence that can be
    obtained from the full pattern by deleting some positions (while keeping
    order). Exact, undeleted matches of the full pattern are not reported.

    Parameters
    ----------
    pattern:
        Reference pattern.
    sequence:
        Sequence in which to search.
    min_len:
        Minimum allowed length of the fragment. If None, defaults to
        `len(pattern) - floor(len(pattern)/4)`.

    Returns
    -------
    list of dict
        Each dict has the form::

            {
                "position": int,         # start index in sequence
                "removed_indices": [...] # indices removed from pattern
            }

    Overlapping fragmentations are suppressed: for each overlapping region,
    only the earliest starting match is kept.
    """
    L = len(pattern)
    N = len(sequence)
    if L == 0 or N == 0:
        return []

    if min_len is None:
        min_len = L - (L // 4)

    # Pre-compute spans of exact full-pattern matches to exclude them
    exact_spans = [
        (s, s + L - 1)
        for s in range(N - L + 1)
        if list(sequence[s : s + L]) == list(pattern)
    ]

    def inside_exact_span(start: int, end: int) -> bool:
        return any(a <= start and end <= b for a, b in exact_spans)

    best_by_pos: Dict[int, List[int]] = {}

    for frag_len in range(min_len, L):
        for start in range(N - frag_len + 1):
            end = start + frag_len - 1
            if inside_exact_span(start, end):
                continue

            fragment = sequence[start : start + frag_len]
            removed = _removed_positions_for_fragment(pattern, fragment)
            if removed is None:
                continue

            existing = best_by_pos.get(start)
            if existing is None or len(removed) < len(existing):
                best_by_pos[start] = removed

    # Convert to sorted list
    results = [
        {"position": pos, "removed_indices": removed}
        for pos, removed in sorted(best_by_pos.items())
    ]

    # Remove overlaps: keep earliest non-overlapping matches
    filtered: List[Dict[str, Any]] = []
    last_end = -1
    for r in results:
        start = r["position"]
        frag_len = L - len(r["removed_indices"])
        end = start + frag_len - 1
        if start > last_end:
            filtered.append(r)
            last_end = end

    return filtered


def _added_positions_for_fragment(
    pattern: Sequence[T],
    fragment: Sequence[T],
) -> Optional[List[Dict[str, Any]]]:
    """Return description of items added to a fragment that contains pattern.

    If `pattern` is not a subsequence of `fragment` in order, returns None.
    Otherwise returns a list of dicts, each of the form::

        { "index": j, "value": fragment[j] }

    describing items in the fragment that do not belong to the pattern.
    """
    i = 0
    j = 0
    Lp = len(pattern)
    Lf = len(fragment)
    added: List[Dict[str, Any]] = []

    while j < Lf and i < Lp:
        if fragment[j] == pattern[i]:
            i += 1
            j += 1
        else:
            added.append({"index": j, "value": fragment[j]})
            j += 1

    # remaining fragment elements after pattern is fully matched
    while j < Lf:
        added.append({"index": j, "value": fragment[j]})
        j += 1

    if i != Lp or not added:
        return None

    # reject if all additions are at very start or very end
    first = added[0]["index"]
    last = added[-1]["index"]
    if first == 0 or last == Lf - 1:
        return None

    return added


def extension(
    pattern: Sequence[T],
    sequence: Sequence[T],
    max_extra: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Detect *extensions* of a pattern inside a sequence.

    An extension is a contiguous subsequence that contains the full pattern
    as an ordered subsequence, plus some extra items *inside* (not only at
    the very beginning or end).

    Parameters
    ----------
    pattern:
        Reference pattern.
    sequence:
        Sequence in which to search.
    max_extra:
        Maximum allowed number of extra items inside the fragment. If None,
        defaults to `len(pattern)//4`.

    Returns
    -------
    list of dict
        Each dict has the form::

            {
                "position": int,      # start index in sequence
                "added": [            # description of added items
                    {"index": j, "value": ...},
                    ...
                ]
            }

        For each `position`, only the longest valid extension is kept.
    """
    L = len(pattern)
    N = len(sequence)
    if L == 0 or N == 0:
        return []

    if max_extra is None:
        max_extra = max(1, L // 4)

    results: List[Dict[str, Any]] = []

    for start in range(N - L + 1):
        best: Optional[Dict[str, Any]] = None

        for frag_len in range(L + 1, L + max_extra + 1):
            end = start + frag_len
            if end > N:
                break
            fragment = sequence[start:end]
            added = _added_positions_for_fragment(pattern, fragment)
            if not added:
                continue

            # keep only the longest valid fragment for this start
            best = {"position": start, "added": added}

        if best is not None:
            results.append(best)

    return results
