"""
Module: src/catalogue/normalizer.py
Purpose: Canonical normalization and deduplication of Indian Standard identifiers.

Preserves critical technical distinctions:
- IS vs IS/IEC vs IS/ISO vs SP
- Part numbers (Part 1, Part 2, etc.)
- Section numbers (Sec 1, Section 2, etc.)
- Publication year
- Amendment identifiers (Amd 1, Amendment 2, etc.)

Resolves cosmetic variations:
- "IS 15778 : 2007" == "IS 15778:2007" == "IS 15778-2007" == "is 15778 : 2007"
- "IS/IEC 61439-3:2012" == "IS/IEC 61439 (Part 3) : 2012"
"""

import re
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any


@dataclass(frozen=True)
class CanonicalStandardIdentifier:
    """Structured decomposition of an Indian Standard identifier."""
    raw_input: str
    prefix: str                           # "IS", "IS/IEC", "IS/ISO", "IS/ISO/TR", "SP", etc.
    base_number: str                      # e.g. "15778", "61439", "11073-10407"
    part: Optional[int] = None            # e.g. 1, 2, 3
    section: Optional[int] = None         # e.g. 1, 5
    year: Optional[int] = None            # e.g. 2007, 2012
    amendment: Optional[int] = None       # e.g. 1, 2
    canonical_number: str = ""            # Standardized string, e.g. "IS 15778 : 2007"
    canonical_id: str = ""                # Slug, e.g. "IS-15778-2007"
    base_standard_number: str = ""        # Standard without year, e.g. "IS 15778"
    is_valid: bool = True                 # Whether parsed into a valid standard identity


class StandardIdentifierNormalizer:
    """Normalizes and canonicalizes Indian Standard identifiers without losing technical specificity."""

    # Regex patterns supporting all compound qualifiers in hierarchical order
    PREFIX_PATTERN = re.compile(
        r'^(IS\s*/\s*ISO\s*/\s*IEC\s*/\s*IEEE|'
        r'IS\s*/\s*ISO\s*/\s*IEC\s*/\s*(?:TR|TS|PAS|GUIDE)|'
        r'IS\s*/\s*ISO\s*/\s*IEC|'
        r'IS\s*/\s*ISO\s*/\s*(?:TR|TS|PAS|TTA|IEEE|GUIDE)|'
        r'IS\s*/\s*IEC\s*/\s*(?:TR|TS|PAS|IEEE|IEE|GUIDE)|'
        r'IS\s*/\s*ISO|'
        r'IS\s*/\s*IEC|'
        r'IS\s*/\s*CISPR|'
        r'IS\s*/\s*QC|'
        r'IS\s*/\s*EN|'
        r'IS\s+B\b|'
        r'ISO\s*/\s*SAE|'
        r'ISO\s*/\s*IEC|'
        r'IEC\b|'
        r'ISO\b|'
        r'SP\b|'
        r'IS\b)',
        re.IGNORECASE
    )

    YEAR_PATTERN = re.compile(r':\s*(19\d\d|20\d\d)\b|[-_\s](19\d\d|20\d\d)\s*$')
    PART_SEC_PATTERN = re.compile(r'\(\s*(?:Part|Pt\.?)\s*(\d+)\s*(?:/|\s+)\s*(?:Sec\.?|Section)\s*(\d+)\s*\)', re.IGNORECASE)
    PART_PATTERN = re.compile(r'\(\s*(?:Part|Pt\.?)\s*(\d+)\s*\)|\b(?:Part|Pt\.?)\s*[-/]?\s*(\d+)\b', re.IGNORECASE)
    SECTION_PATTERN = re.compile(r'\(\s*(?:Sec\.?|Section)\s*(\d+)\s*\)|\b(?:Sec\.?|Section)\s*[-/]?\s*(\d+)\b', re.IGNORECASE)
    AMENDMENT_PATTERN = re.compile(r'\b(?:Amd\.?|Amendment)\s*[-/]?\s*(\d+)\b', re.IGNORECASE)

    @classmethod
    def clean_html(cls, raw_str: str) -> str:
        """Strips HTML linebreaks and extracts primary standard string."""
        if not raw_str or not isinstance(raw_str, str):
            return ""
        first = re.split(r'<br\s*/?>', raw_str, flags=re.IGNORECASE)[0]
        # Remove any lingering HTML tags like <font>
        cleaned = re.sub(r'<[^>]+>', '', first)
        return cleaned.strip()

    @classmethod
    def parse(cls, standard_str: str) -> CanonicalStandardIdentifier:
        """Parses any raw standard string into a CanonicalStandardIdentifier."""
        if not standard_str or not str(standard_str).strip():
            return CanonicalStandardIdentifier(
                raw_input="",
                prefix="UNKNOWN",
                base_number="",
                canonical_number="UNKNOWN",
                canonical_id="UNKNOWN",
                base_standard_number="UNKNOWN",
                is_valid=False
            )

        raw = str(standard_str).strip()
        cleaned = cls.clean_html(raw)

        # Normalize unicode / accent typo on 'ÍS' -> 'IS'
        if cleaned.startswith('ÍS') or cleaned.startswith('Ís'):
            cleaned = 'IS' + cleaned[2:]

        # Check for recoverable bare digits: e.g. '16324 16324:2014' or '13360:2025'
        bare_match = re.match(r'^(\d+)(?:\s+\1)?(?:\s*:\s*|\s*-\s*)(19\d\d|20\d\d)', cleaned)
        if bare_match:
            base_num = bare_match.group(1)
            yr = int(bare_match.group(2))
            c_num = f"IS {base_num}:{yr}"
            c_id = f"IS-{base_num}-{yr}"
            return CanonicalStandardIdentifier(
                raw_input=raw,
                prefix="IS",
                base_number=base_num,
                year=yr,
                canonical_number=c_num,
                canonical_id=c_id,
                base_standard_number=f"IS {base_num}",
                is_valid=True
            )

        # 1. Identify Prefix
        prefix_match = cls.PREFIX_PATTERN.search(cleaned)
        if not prefix_match:
            # Check if starts with digits directly without prefix
            digits_start = re.match(r'^(\d+)', cleaned)
            if digits_start:
                prefix = "IS"
                remainder = cleaned
            else:
                return CanonicalStandardIdentifier(
                    raw_input=raw,
                    prefix="UNKNOWN",
                    base_number="",
                    canonical_number="UNKNOWN",
                    canonical_id="UNKNOWN",
                    base_standard_number="UNKNOWN",
                    is_valid=False
                )
        else:
            raw_p = prefix_match.group(1).upper()
            # Normalize internal slashes and whitespace
            prefix = re.sub(r'\s+', ' ', re.sub(r'\s*/\s*', '/', raw_p))
            if prefix == "IS/IEC/IEE":
                prefix = "IS/IEC/IEEE"
            remainder = cleaned[prefix_match.end():].strip()

        # Guard: Check for missing base number starting directly with hyphen/part
        if re.match(r'^[-/]\s*\d', remainder):
            return CanonicalStandardIdentifier(
                raw_input=raw,
                prefix=prefix,
                base_number="",
                canonical_number="UNKNOWN",
                canonical_id="UNKNOWN",
                base_standard_number="UNKNOWN",
                is_valid=False
            )
        if re.match(r'^\s*\(\s*(?:Part|Pt|Sec)', remainder, re.IGNORECASE):
            return CanonicalStandardIdentifier(
                raw_input=raw,
                prefix=prefix,
                base_number="",
                canonical_number="UNKNOWN",
                canonical_id="UNKNOWN",
                base_standard_number="UNKNOWN",
                is_valid=False
            )

        # 2. Extract Amendment if present
        amd_match = cls.AMENDMENT_PATTERN.search(remainder)
        amendment = int(amd_match.group(1)) if amd_match else None
        if amd_match:
            remainder = cls.AMENDMENT_PATTERN.sub('', remainder).strip()

        # 3. Extract Year if present
        year = None
        ym = cls.YEAR_PATTERN.search(remainder)
        if ym:
            year = int(ym.group(1) or ym.group(2))
            remainder = remainder[:ym.start()].strip()

        # 4. Extract Part and Section
        part = None
        section = None

        psm = cls.PART_SEC_PATTERN.search(remainder)
        if psm:
            part = int(psm.group(1))
            section = int(psm.group(2))
            remainder = remainder[:psm.start()] + remainder[psm.end():]
        else:
            part_match = cls.PART_PATTERN.search(remainder)
            if part_match:
                part = int(part_match.group(1) or part_match.group(2))
                remainder = remainder[:part_match.start()] + remainder[part_match.end():]

            sec_match = cls.SECTION_PATTERN.search(remainder)
            if sec_match:
                section = int(sec_match.group(1) or sec_match.group(2))
                remainder = remainder[:sec_match.start()] + remainder[sec_match.end():]

        remainder = remainder.strip()

        # 5. Extract and Validate Base Number
        # Handle hyphenated parts if not caught by part pattern, e.g. 61439-3 or 60079-30-2
        dash_part = re.search(r'^(\d+)\s*[-]\s*(\d+)(?:\s*[-]\s*(\d+))?$', remainder)
        if dash_part and part is None:
            base_number = dash_part.group(1)
            part = int(dash_part.group(2))
            if dash_part.group(3) and section is None:
                section = int(dash_part.group(3))
        else:
            base_number = re.sub(r'^[\s\-:]+|[\s\-:]+$', '', remainder)
            base_number = re.sub(r'\s*-\s*', '-', base_number)
            base_number = re.sub(r'\s+', ' ', base_number)

        # If base number has no digits at all, this record is missing a standard number!
        if not re.search(r'\d', base_number):
            return CanonicalStandardIdentifier(
                raw_input=raw,
                prefix=prefix,
                base_number="",
                year=year,
                canonical_number="UNKNOWN",
                canonical_id="UNKNOWN",
                base_standard_number="UNKNOWN",
                is_valid=False
            )

        # 6. Construct canonical number and canonical slug
        slug_comp = [prefix.replace('/', '-').replace(' ', '-'), base_number.replace(' ', '-')]
        base_str = f"{prefix} {base_number}"

        if part is not None:
            slug_comp.append(f"Part-{part}")
            base_str += f" (Part {part})"

        if section is not None:
            slug_comp.append(f"Sec-{section}")
            base_str += f" (Sec {section})"

        if amendment is not None:
            slug_comp.append(f"Amd-{amendment}")
            base_str += f" Amd {amendment}"

        if year is not None:
            canonical_number = f"{base_str} : {year}"
            slug_comp.append(str(year))
        else:
            canonical_number = base_str

        canonical_id = "-".join(slug_comp)

        return CanonicalStandardIdentifier(
            raw_input=raw,
            prefix=prefix,
            base_number=base_number,
            part=part,
            section=section,
            year=year,
            amendment=amendment,
            canonical_number=canonical_number,
            canonical_id=canonical_id,
            base_standard_number=base_str,
            is_valid=True
        )

    @classmethod
    def are_equivalent(cls, std_a: str, std_b: str, ignore_year: bool = False) -> bool:
        """Compares two standard strings for technical identity."""
        if not std_a or not std_b:
            return False
        parsed_a = cls.parse(std_a)
        parsed_b = cls.parse(std_b)

        if parsed_a.prefix != parsed_b.prefix:
            return False
        if parsed_a.base_number != parsed_b.base_number:
            return False
        if parsed_a.part != parsed_b.part:
            return False
        if parsed_a.section != parsed_b.section:
            return False

        if not ignore_year:
            # If both have years, they must match; if one is missing year, treat base match
            if parsed_a.year is not None and parsed_b.year is not None:
                return parsed_a.year == parsed_b.year

        return True

    @classmethod
    def normalize_identifier(cls, standard_str: str) -> str:
        """Returns canonical ID slug, e.g. 'IS-15778-2007'."""
        return cls.parse(standard_str).canonical_id

    @classmethod
    def to_canonical_number(cls, standard_str: str) -> str:
        """Returns canonical number string, e.g. 'IS 15778 : 2007'."""
        return cls.parse(standard_str).canonical_number

    @classmethod
    def to_base_standard_number(cls, standard_str: str) -> str:
        """Returns base standard number without year, e.g. 'IS 15778'."""
        return cls.parse(standard_str).base_standard_number
