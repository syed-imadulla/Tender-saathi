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
    prefix: str                           # "IS", "IS/IEC", "IS/ISO", "SP"
    base_number: str                      # e.g. "15778", "61439", "10322"
    part: Optional[int] = None            # e.g. 1, 2, 3
    section: Optional[int] = None         # e.g. 1, 5
    year: Optional[int] = None            # e.g. 2007, 2012
    amendment: Optional[int] = None       # e.g. 1, 2
    canonical_number: str = ""            # Standardized string, e.g. "IS 15778 : 2007"
    canonical_id: str = ""                # Slug, e.g. "IS-15778-2007"
    base_standard_number: str = ""        # Standard without year, e.g. "IS 15778"


class StandardIdentifierNormalizer:
    """Normalizes and canonicalizes Indian Standard identifiers without losing technical specificity."""

    # Regex patterns
    PREFIX_PATTERN = re.compile(r'^(IS\s*/\s*IEC|IS\s*/\s*ISO|IS|SP)\b', re.IGNORECASE)
    YEAR_PATTERN = re.compile(r'\b(19\d\d|20\d\d)\b')
    PART_PATTERN = re.compile(r'\b(?:Part|Pt\.?)\s*[-/]?\s*(\d+)\b', re.IGNORECASE)
    SECTION_PATTERN = re.compile(r'\b(?:Sec\.?|Section)\s*[-/]?\s*(\d+)\b', re.IGNORECASE)
    AMENDMENT_PATTERN = re.compile(r'\b(?:Amd\.?|Amendment)\s*[-/]?\s*(\d+)\b', re.IGNORECASE)

    @classmethod
    def parse(cls, standard_str: str) -> CanonicalStandardIdentifier:
        """Parses any raw standard string into a CanonicalStandardIdentifier."""
        if not standard_str or not standard_str.strip():
            return CanonicalStandardIdentifier(
                raw_input="",
                prefix="UNKNOWN",
                base_number="",
                canonical_number="UNKNOWN",
                canonical_id="UNKNOWN",
                base_standard_number="UNKNOWN"
            )

        raw = standard_str.strip()

        # 1. Identify Prefix
        prefix_match = cls.PREFIX_PATTERN.search(raw)
        if prefix_match:
            raw_p = prefix_match.group(1).upper()
            if "IEC" in raw_p:
                prefix = "IS/IEC"
            elif "ISO" in raw_p:
                prefix = "IS/ISO"
            elif "SP" in raw_p:
                prefix = "SP"
            else:
                prefix = "IS"
            remainder = raw[prefix_match.end():].strip()
        else:
            # Check if it starts with numbers directly (assume IS)
            prefix = "IS"
            remainder = raw

        # 2. Extract Amendment if present
        amd_match = cls.AMENDMENT_PATTERN.search(remainder)
        amendment = int(amd_match.group(1)) if amd_match else None
        if amd_match:
            remainder = cls.AMENDMENT_PATTERN.sub('', remainder).strip()

        # 3. Extract Year if present (prioritize colon separator or trailing position)
        year = None
        if ":" in remainder:
            std_part, yr_part = remainder.rsplit(":", 1)
            ym = cls.YEAR_PATTERN.search(yr_part)
            if ym:
                year = int(ym.group(1))
                remainder = std_part.strip()
        else:
            end_ym = re.search(r'[-_\s](19\d\d|20\d\d)\s*$', remainder)
            if end_ym:
                year = int(end_ym.group(1))
                remainder = remainder[:end_ym.start()].strip()

        # 4. Extract Part and Section
        part_match = cls.PART_PATTERN.search(remainder)
        part = int(part_match.group(1)) if part_match else None
        if part_match:
            remainder = cls.PART_PATTERN.sub('', remainder).strip()

        sec_match = cls.SECTION_PATTERN.search(remainder)
        section = int(sec_match.group(1)) if sec_match else None
        if sec_match:
            remainder = cls.SECTION_PATTERN.sub('', remainder).strip()

        # 5. Extract Base Number (e.g. 15778, 61439, 10322, 1239, 2062)
        # Handle hyphenated parts if not caught by part pattern, e.g. 61439-3
        dash_part = re.search(r'(\d+)\s*[-]\s*(\d+)', remainder)
        if dash_part and part is None:
            base_number = dash_part.group(1)
            part = int(dash_part.group(2))
        else:
            num_match = re.search(r'(\d+)', remainder)
            base_number = num_match.group(1) if num_match else remainder.strip()

        # Clean base number
        base_number = re.sub(r'[^\d\w]', '', base_number)

        # 6. Construct canonical number and canonical slug
        slug_comp = [prefix.replace('/', '-'), base_number]

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
            base_standard_number=base_str
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
