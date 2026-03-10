import re


PAN_KEYWORDS = {
    "INCOME",
    "TAX",
    "DEPARTMENT",
    "GOVT",
    "INDIA",
    "PERMANENT",
    "ACCOUNT",
    "NUMBER",
    "SIGNATURE",
    "SAMPLE",
}

KEYWORD_FRAGMENTS = (
    "INCO",
    "TAX",
    "DEPA",
    "DEPI",
    "GOV",
    "IND",
    "PERM",
    "ACCO",
    "NUMB",
    "SIGN",
    "SAMP",
)

LETTER_FIX = {
    "0": "O",
    "1": "I",
    "2": "Z",
    "4": "A",
    "5": "S",
    "6": "G",
    "8": "B",
}

DIGIT_FIX = {
    "O": "0",
    "Q": "0",
    "D": "0",
    "I": "1",
    "L": "1",
    "Z": "2",
    "S": "5",
    "B": "8",
    "G": "6",
}


def _normalize_text(text):
    return text.upper().replace("\r", "\n")


def _sanitize_token(token):
    return re.sub(r"[^A-Z0-9]", "", token.upper())


def _normalize_pan_candidate(token):
    token = _sanitize_token(token)
    if len(token) != 10:
        return None

    chars = list(token)
    letter_positions = (0, 1, 2, 3, 4, 9)
    digit_positions = (5, 6, 7, 8)

    for idx in letter_positions:
        chars[idx] = LETTER_FIX.get(chars[idx], chars[idx])
    for idx in digit_positions:
        chars[idx] = DIGIT_FIX.get(chars[idx], chars[idx])

    candidate = "".join(chars)
    if re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", candidate):
        return candidate
    return None


def _is_pan_like_token(token):
    token = _sanitize_token(token)
    if len(token) != 10:
        return False
    if not re.fullmatch(r"[A-Z0-9]{10}", token):
        return False
    # Avoid obvious non-PAN words/noise.
    if any(k in token for k in ("INCOME", "DEPART", "GOVT", "INDIA", "SIGNAT", "SAMPLE")):
        return False
    # A PAN-like token should include both letters and digits.
    if not re.search(r"[A-Z]", token):
        return False
    if not re.search(r"[0-9]", token):
        return False
    return True


def _extract_pan_like_fallback(text):
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    keyword_idx = None
    for i, ln in enumerate(lines):
        if "PERMANENT" in ln or "ACCOUNT" in ln or "NUMBER" in ln:
            keyword_idx = i
            break

    # Prefer tokens near "Permanent Account Number" label.
    if keyword_idx is not None:
        start = max(0, keyword_idx - 1)
        end = min(len(lines), keyword_idx + 3)
        for ln in lines[start:end]:
            for token in re.findall(r"[A-Z0-9]{8,14}", ln.upper()):
                t = _sanitize_token(token)
                if _is_pan_like_token(t):
                    return t

    # Global fallback.
    for token in re.findall(r"[A-Z0-9]{8,14}", text.upper()):
        t = _sanitize_token(token)
        if _is_pan_like_token(t):
            return t

    return None


def extract_pan_number(text):
    text = _normalize_text(text)

    direct = re.search(r"[A-Z]{5}[0-9]{4}[A-Z]", text)
    if direct:
        return direct.group()

    tokens = re.findall(r"[A-Z0-9]{8,14}", text)
    for token in tokens:
        if len(token) == 10:
            candidate = _normalize_pan_candidate(token)
            if candidate:
                return candidate

    for m in re.finditer(r"(?:[A-Z0-9][^A-Z0-9]{0,2}){10}", text):
        candidate = _normalize_pan_candidate(m.group())
        if candidate:
            return candidate

    return _extract_pan_like_fallback(text)


def extract_dob(text):
    text = _normalize_text(text)

    m = re.search(r"\b(0[1-9]|[12][0-9]|3[01])[\/\-. ](0[1-9]|1[0-2])[\/\-. ]((?:19|20)\d{2})\b", text)
    if m:
        return f"{m.group(1)}/{m.group(2)}/{m.group(3)}"

    compact = re.sub(r"[^0-9]", "", text)
    for i in range(0, max(0, len(compact) - 7)):
        chunk = compact[i : i + 8]
        dd = int(chunk[0:2])
        mm = int(chunk[2:4])
        yyyy = int(chunk[4:8])
        if 1 <= dd <= 31 and 1 <= mm <= 12 and 1900 <= yyyy <= 2099:
            return f"{chunk[0:2]}/{chunk[2:4]}/{chunk[4:8]}"

    return None


def _candidate_name_chunks(lines):
    def likely_name_word(word):
        if len(word) < 3 or len(word) > 12:
            return False
        if not re.search(r"[AEIOU]", word):
            return False
        if re.search(r"[BCDFGHJKLMNPQRSTVWXYZ]{4,}", word):
            return False
        return True

    out = []
    for line in lines:
        words = re.findall(r"[A-Z]{2,}", line.upper())
        words = [w for w in words if w not in PAN_KEYWORDS]
        words = [w for w in words if not any(frag in w for frag in KEYWORD_FRAGMENTS)]
        words = [w for w in words if likely_name_word(w)]
        if len(words) < 2:
            continue

        i = 0
        while i + 1 < len(words):
            first = words[i]
            second = words[i + 1]
            if len(first) >= 3 and len(second) >= 3:
                out.append(f"{first} {second}")
                i += 2
            else:
                i += 1
    return out


def extract_names(text):
    text = _normalize_text(text)
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        return None, None

    candidates = _candidate_name_chunks(lines)
    if not candidates:
        return None, None

    dob_line_idx = None
    for i, line in enumerate(lines):
        if re.search(r"(0[1-9]|[12][0-9]|3[01])[\/\-. ](0[1-9]|1[0-2])[\/\-. ]((?:19|20)\d{2})", line):
            dob_line_idx = i
            break

    if dob_line_idx is not None:
        name_like_before_dob = []
        for i, line in enumerate(lines):
            if i >= dob_line_idx:
                break
            clean = re.sub(r"[^A-Z ]", " ", line.upper())
            clean = " ".join(clean.split())
            if clean in candidates:
                name_like_before_dob.append(clean)
        if len(name_like_before_dob) >= 2:
            return name_like_before_dob[-2], name_like_before_dob[-1]

    if len(candidates) >= 2:
        return candidates[0], candidates[1]
    return candidates[0], None
