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
