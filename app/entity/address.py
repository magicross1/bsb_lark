from __future__ import annotations

import re

from pydantic import BaseModel


class NormalizedAddress(BaseModel):
    unit: str | None = None
    street_number: str | None = None
    street_name: str | None = None
    street_type: str | None = None
    suburb: str | None = None
    state: str | None = None
    postcode: str | None = None
    raw: str = ""


STREET_TYPE_MAP: dict[str, str] = {
    "RD": "RD",
    "ROAD": "RD",
    "ST": "ST",
    "STREET": "ST",
    "DR": "DR",
    "DRIVE": "DR",
    "AVE": "AVE",
    "AVENUE": "AVE",
    "HWY": "HWY",
    "HIGHWAY": "HWY",
    "CT": "CT",
    "COURT": "CT",
    "WAY": "WAY",
    "CRES": "CRES",
    "CRESCENT": "CRES",
    "PL": "PL",
    "PLACE": "PL",
    "BLVD": "BLVD",
    "BOULEVARD": "BLVD",
    "CL": "CL",
    "CLOSE": "CL",
    "LN": "LN",
    "LANE": "LN",
    "GR": "GR",
    "GROVE": "GR",
    "PDE": "PDE",
    "PARADE": "PDE",
    "TER": "TER",
    "TCE": "TER",
    "TERRACE": "TER",
    "CIR": "CIR",
    "CIRCUIT": "CIR",
    "CRT": "CT",
}

_POSTCODE_RE = re.compile(r"\b(\d{4})\b")
_STATE_RE = re.compile(r"\b(NSW|VIC|QLD|ACT|SA|WA|TAS|NT)\b", re.IGNORECASE)
_FULL_STATE_MAP: dict[str, str] = {
    "NEW SOUTH WALES": "NSW",
    "VICTORIA": "VIC",
    "QUEENSLAND": "QLD",
    "SOUTH AUSTRALIA": "SA",
    "WESTERN AUSTRALIA": "WA",
    "TASMANIA": "TAS",
    "NORTHERN TERRITORY": "NT",
    "AUSTRALIAN CAPITAL TERRITORY": "ACT",
}
_FULL_STATE_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in _FULL_STATE_MAP) + r")\b",
    re.IGNORECASE,
)
_COUNTRY_RE = re.compile(r"\bAUSTRALIA\b", re.IGNORECASE)
_STREET_TYPES_PATTERN = "|".join(re.escape(k) for k in sorted(STREET_TYPE_MAP.keys(), key=len, reverse=True))
_STREET_TYPE_RE = re.compile(rf"\b({_STREET_TYPES_PATTERN})\b", re.IGNORECASE)
_UNIT_WORD_RE = re.compile(r"^(?:Unit\s+|UNIT\s+)", re.IGNORECASE)
_UNIT_SLASH_RE = re.compile(r"^([A-Za-z]?\d*[A-Za-z]?)\s*/\s*", re.IGNORECASE)
_RANGE_SLASH_RE = re.compile(r"^(\d+-\d+)/(\d+[A-Za-z]?)\s*", re.IGNORECASE)
_NOISE_PREFIX_RE = re.compile(r"^(?:The\s+first\s+time,?\s*|W\d+,?\s*|B\d+/?)\s*", re.IGNORECASE)
_DASH_NORMALIZE_RE = re.compile(r"\s*[–—\-]\s*")


def normalize_address(raw: str) -> NormalizedAddress:
    raw = raw.strip()
    s = raw

    s = _NOISE_PREFIX_RE.sub("", s)

    s = _DASH_NORMALIZE_RE.sub("-", s)

    s = _COUNTRY_RE.sub("", s)

    full_state_match = _FULL_STATE_RE.search(s)
    if full_state_match:
        state = _FULL_STATE_MAP[full_state_match.group(1).upper()]
        s = s[: full_state_match.start()] + s[full_state_match.end() :]
    else:
        state_match = _STATE_RE.search(s)
        state = state_match.group(1).upper() if state_match else None
        if state_match:
            s = s[: state_match.start()] + s[state_match.end() :]

    postcode_match = _POSTCODE_RE.search(s)
    postcode = postcode_match.group(1) if postcode_match else None
    if postcode_match:
        s = s[: postcode_match.start()] + s[postcode_match.end() :]

    s = s.strip().rstrip(",").strip()
    s = re.sub(r"\s{2,}", " ", s)

    unit = None

    unit_word_match = _UNIT_WORD_RE.match(s)
    if unit_word_match:
        s = s[unit_word_match.end() :]

    range_slash_match = _RANGE_SLASH_RE.match(s)
    if range_slash_match:
        unit = range_slash_match.group(1).upper()
        s = range_slash_match.group(2) + " " + s[range_slash_match.end() :]
    else:
        unit_slash_match = _UNIT_SLASH_RE.match(s)
        if unit_slash_match:
            candidate = unit_slash_match.group(1)
            if candidate:
                digit_core = re.sub(r"^[a-zA-Z]+", "", candidate)
                unit = digit_core if digit_core else candidate.upper()
            s = s[unit_slash_match.end() :]
        elif unit_word_match:
            num_after = re.match(r"^(\d+[A-Za-z]?)[,\s]+", s)
            if num_after:
                unit = num_after.group(1)
                s = s[num_after.end() :]

    s = re.sub(r"^[/\s,]+", "", s)

    parts = [p.strip() for p in s.split(",") if p.strip()]

    street_part = parts[0] if parts else ""
    suburb = None

    if len(parts) >= 2:
        suburb_candidates = [p.strip().upper() for p in parts[1:]]
        suburb = " ".join(suburb_candidates)
    elif len(parts) == 1 and state:
        street_type_match = _STREET_TYPE_RE.search(street_part)
        if street_type_match:
            after_type = street_part[street_type_match.end() :].strip()
            if after_type:
                suburb = after_type.upper()
                street_part = street_part[: street_type_match.end()]

    street_type = None
    street_type_match = _STREET_TYPE_RE.search(street_part)
    if street_type_match:
        street_type = STREET_TYPE_MAP.get(street_type_match.group(1).upper(), street_type_match.group(1).upper())
        street_part = street_part[: street_type_match.start()] + street_part[street_type_match.end() :]

    street_part = street_part.strip().rstrip(",").strip()

    street_number = None
    num_match = re.match(r"^(\d+[A-Za-z]?-\d+[A-Za-z]?|\d+[A-Za-z]?)\s*", street_part)
    if num_match:
        street_number = num_match.group(1).upper()
        street_part = street_part[num_match.end() :]

    street_name = re.sub(r"\s+", " ", street_part).strip().upper()
    if not street_name:
        street_name = None

    if suburb:
        suburb = re.sub(r"\s+", " ", suburb).strip()
        if not suburb:
            suburb = None

    return NormalizedAddress(
        unit=unit,
        street_number=street_number,
        street_name=street_name,
        street_type=street_type,
        suburb=suburb,
        state=state,
        postcode=postcode,
        raw=raw,
    )


def address_match_score(parsed: NormalizedAddress, candidate: NormalizedAddress) -> float:
    score = 0.0
    max_score = 0.0

    if parsed.postcode and candidate.postcode:
        max_score += 30
        if parsed.postcode == candidate.postcode:
            score += 30

    if parsed.street_name and candidate.street_name:
        max_score += 25
        if parsed.street_name == candidate.street_name:
            score += 25
        elif parsed.street_name in candidate.street_name or candidate.street_name in parsed.street_name:
            score += 15

    if parsed.street_type and candidate.street_type:
        max_score += 10
        if parsed.street_type == candidate.street_type:
            score += 10

    if parsed.street_number and candidate.street_number:
        max_score += 20
        if parsed.street_number == candidate.street_number:
            score += 20
        elif _number_ranges_overlap(parsed.street_number, candidate.street_number):
            score += 15

    if parsed.unit and candidate.unit:
        max_score += 10
        if parsed.unit == candidate.unit:
            score += 10

    if parsed.suburb and candidate.suburb:
        max_score += 5
        if parsed.suburb == candidate.suburb:
            score += 5

    return score / max_score if max_score > 0 else 0.0


def _number_ranges_overlap(a: str, b: str) -> bool:
    def parse_range(s: str) -> range:
        s = re.sub(r"[A-Za-z]", "", s)
        if "-" in s:
            parts = s.split("-")
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                start, end = int(parts[0]), int(parts[1])
                return range(start, end + 1)
        if s.isdigit():
            n = int(s)
            return range(n, n + 1)
        return range(0)

    ra, rb = parse_range(a), parse_range(b)
    if not ra or not rb:
        return False
    latest_start = max(ra.start, rb.start)
    earliest_end = min(ra.stop, rb.stop)
    return latest_start < earliest_end
