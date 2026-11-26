"""Indian plate format correction (no ML needed).

Standard plate = SS DD L{1,3} DDDD  (state letters, district digits, series letters, 4-digit number),
e.g. MP07SA1908. OCR confuses look-alikes (O/0, I/1, S/5, B/8, Z/2 ...). Because we KNOW which
positions must be letters and which must be digits, most of those slips can be fixed safely.
"""

TO_DIGIT = {"O": "0", "Q": "0", "D": "0", "I": "1", "L": "1", "Z": "2", "S": "5", "B": "8", "G": "6", "T": "7"}
TO_LETTER = {"0": "O", "1": "I", "2": "Z", "5": "S", "8": "B", "6": "G", "7": "T", "4": "A"}
STATES = set("AN AP AR AS BR CG CH DD DL DN GA GJ HP HR JH JK KA KL LA LD MH ML MN MP MZ NL OD OR PB PY RJ SK TN TR TS UK UP WB".split())


def fix_indian_plate(text):
    t = "".join(ch for ch in (text or "").upper() if ch.isalnum())
    k = len(t) - 8
    if not 1 <= k <= 3:
        return t  # not a standard-length plate (e.g. BH series, partial read) - leave untouched
    chars = list(t)
    letter_pos = [0, 1] + list(range(4, 4 + k))
    digit_pos = [2, 3] + list(range(4 + k, len(t)))
    for i in letter_pos:
        chars[i] = TO_LETTER.get(chars[i], chars[i])
    for i in digit_pos:
        chars[i] = TO_DIGIT.get(chars[i], chars[i])
    return "".join(chars)


def is_valid_format(text):
    t = fix_indian_plate(text)
    k = len(t) - 8
    return 1 <= k <= 3 and t[:2] in STATES and t[:2].isalpha() and t[2:4].isdigit() and t[4:4 + k].isalpha() and t[4 + k:].isdigit()


# ---------------------------------------------------------------------------
# Partial reads: OCR often returns only one half of a plate (head "MP07" or tail "SA1908").
# ---------------------------------------------------------------------------
import re

_HEAD = re.compile(r"^[A-Z]{2}[0-9OQDILZSBGT]{2}$")
_TAIL = re.compile(r"^[A-Z]{1,3}[0-9OQDILZSBGT]{4}$")


def plate_score(t):
    """How plate-like a string is (used to prefer full, valid plates over fragments)."""
    if is_valid_format(t):
        return 3.0
    if 9 <= len(t) <= 11:
        return 1.5
    if len(t) >= 6:
        return 0.7
    return 0.4


def _fix_head(t):
    return "".join(TO_LETTER.get(c, c) for c in t[:2]) + "".join(TO_DIGIT.get(c, c) for c in t[2:])


def _fix_tail(t):
    return "".join(TO_LETTER.get(c, c) for c in t[:-4]) + "".join(TO_DIGIT.get(c, c) for c in t[-4:])


def merge_head_tail(items):
    """items = [(text, conf)]. If some frames read the head (MP07) and others the tail (SA1908),
    join the most confident of each. Returns (plate, conf) or None."""
    heads = [(_fix_head(t), c) for t, c in items if _HEAD.match(t)]
    tails = [(_fix_tail(t), c) for t, c in items if _TAIL.match(t)]
    if not heads or not tails:
        return None
    h, hc = max(heads, key=lambda x: x[1])
    t, tc = max(tails, key=lambda x: x[1])
    plate = h + t
    return (plate, (hc + tc) / 2) if is_valid_format(plate) else None


# ---------------------------------------------------------------------------
# Fragment assembly. EasyOCR returns pieces like ('MPO7', .9) ('S441908', .5) in ANY order, with the
# printed dot ("MP.07", "SA.1908") often misread as a letter/digit. Instead of gluing text by position,
# look for the two pieces a plate is made of: HEAD = state+district (MP07), TAIL = series+number (SA1908).
# ---------------------------------------------------------------------------
from itertools import permutations


def split_pieces(frags):
    """frags = [(raw_text, conf)] -> pieces split at dots/spaces/dashes: 'SA.1908' -> 'SA', '1908'."""
    out = []
    for t, c in frags:
        for p in re.split(r"[^A-Z0-9]+", (t or "").upper()):
            if p:
                out.append((p, float(c)))
    return out


def _digits(s):
    f = "".join(TO_DIGIT.get(ch, ch) for ch in s)
    return f if f and f.isdigit() else None


def _letters(s):
    f = "".join(TO_LETTER.get(ch, ch) for ch in s)
    return f if f and f.isalpha() else None


def head_candidates(pieces):
    out = []
    for s, c in pieces:
        if len(s) >= 4:
            st, d = _letters(s[:2]), _digits(s[2:4])
            if st in STATES and d:
                out.append((st + d, c if len(s) == 4 else c * 0.6))
    for (a, ca), (b, cb) in permutations(pieces, 2):
        if len(a) == 2 and len(b) == 2:
            st, d = _letters(a), _digits(b)
            if st in STATES and d:
                out.append((st + d, min(ca, cb)))
    return out


def tail_candidates(pieces):
    out = []
    for s, c in pieces:
        if len(s) >= 5:
            dg, pre = _digits(s[-4:]), s[:-4]
            if dg is None:
                continue
            if len(pre) == 3 and not pre[-1].isalpha():
                pre = pre[:2]            # the printed dot was read as a digit: 'S44' -> 'S4' -> 'SA'
            if len(pre) > 3 or not any(ch.isalpha() for ch in pre):
                continue                 # long strings are full plates; a bare '41908' has no real series letter
            let = _letters(pre)
            if let and 1 <= len(let) <= 3:
                out.append((let + dg, c))
    for (a, ca), (b, cb) in permutations(pieces, 2):
        if 1 <= len(a) <= 3 and len(b) == 4 and any(ch.isalpha() for ch in a):
            let, dg = _letters(a), _digits(b)
            if let and dg:
                out.append((let + dg, min(ca, cb)))
    return out


def assemble_plate(frags):
    """-> {"full": (plate, conf)|None, "head": (h, c)|None, "tail": (t, c)|None}"""
    pieces = split_pieces(frags)
    heads, tails = head_candidates(pieces), tail_candidates(pieces)
    head = max(heads, key=lambda x: x[1]) if heads else None
    tail = max(tails, key=lambda x: x[1]) if tails else None
    full = None
    if head and tail and is_valid_format(head[0] + tail[0]):
        full = (head[0] + tail[0], (head[1] + tail[1]) / 2)
    return {"full": full, "head": head, "tail": tail}
