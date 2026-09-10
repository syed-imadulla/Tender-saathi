"""
Module: src/extract.py
Purpose: Extract procurement requirements, classify categories, and detect explicit standard citations.

Supported categories:
- material
- product_equipment
- installation_execution
- general_specification
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
import os
import re
import csv
import pymupdf


from src.decompose import RequirementComponent, decompose_requirement


# ---------------------------------------------------------------------------
# Data Model
# ---------------------------------------------------------------------------

@dataclass
class Requirement:
    requirement_id: str
    requirement_text: str
    category: str                          # material, product_equipment, installation_execution, general_specification
    tender_id: Optional[str] = None
    page: Optional[int] = None
    section: Optional[str] = None
    explicit_standards: List[str] = field(default_factory=list)
    raw_context: Optional[str] = None
    components: List[RequirementComponent] = field(default_factory=list)
    decomposition_confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["components"] = [c.to_dict() if hasattr(c, "to_dict") else c for c in self.components]
        return d


# ---------------------------------------------------------------------------
# Patterns & Noise Filters
# ---------------------------------------------------------------------------

STANDARD_REGEX = re.compile(
    r'\b((?:IS|IS/ISO|IS/IEC|SP)\s*[:/]?\s*\d+(?:[\s\-:]+(?:Part|Sec|Section)?\s*\d+)*(?:[\s\-:]+\d{4})?)\b',
    re.IGNORECASE
)

BOILERPLATE_IGNORE_PATTERNS = [
    r'is multi currency',
    r'allow two stage bidding',
    r'general technical',
    r'evaluation allowed',
    r'itemwise technical evaluation',
    r'withdrawal allowed',
    r'should allow nda',
    r'allow preferential bidder',
    r'payment instruments',
    r'cover details',
    r'tender fee details',
    r'emd fee details',
    r'critical dates',
    r'document download',
    r'bid submission',
    r'clarification',
    r'latest corrigendum',
    r'tender inviting authority',
    r'eprocurement system',
    r'date\s*:\s*\d+',
    r'page\s*\d+\s*of\s*\d+',
    r'government of india',
    r'tender reference number',
    r'tender id\s*:',
    r'pre bid meeting',
    r'bid opening',
    r'contract type',
    r'location\s*:',
    r'pincode'
]


def normalize_standard_mention(raw: str) -> str:
    """Normalizes raw standard mentions like 'IS:1239 - 2004' into 'IS 1239 : 2004'."""
    clean = re.sub(r'\s+', ' ', raw.strip())
    clean = re.sub(r'[:/]', ' ', clean)
    clean = re.sub(r'\s*-\s*', ' : ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


def detect_explicit_standards(text: str) -> List[str]:
    """Finds all explicit IS/ISO/IEC/SP standard mentions in text."""
    if not text:
        return []
    matches = STANDARD_REGEX.findall(text)
    seen = set()
    cleaned = []
    for m in matches:
        norm = normalize_standard_mention(m)
        if norm.upper() not in seen:
            seen.add(norm.upper())
            cleaned.append(norm)
    return cleaned


def classify_category(text: str) -> str:
    """
    Classifies requirement into one of:
    - material
    - product_equipment
    - installation_execution
    - general_specification
    """
    tl = text.lower()

    # Execution / Installation indicators
    exec_keywords = [
        "laying", "erection", "civil works", "fixing", "plumbing work",
        "testing and commissioning", "cable laying", "trenching", "rewiring",
        "construction of", "installation of", "earthing work", "plastering",
        "excavation", "dismantling", "repairing work"
    ]
    # Equipment / Product indicators
    product_keywords = [
        "valve", "sluice valve", "gate valve", "check valve", "pump", "centrifugal pump",
        "submersible pump", "transformer", "chiller", "panel", "distribution board",
        "feeder pillar", "switchgear", "circuit breaker", "mcb", "mccb", "motor",
        "luminaire", "light fitting", "led light", "fitting", "outlet", "geyser",
        "air conditioner", "compressor", "generator", "dg set", "fan", "exhaust fan"
    ]
    # Material indicators
    material_keywords = [
        "pipe", "pipes", "cpvc", "pvc", "hdpe", "gi pipe", "hubless", "cast iron pipe",
        "tile", "tiles", "ceramic", "vitrified", "cement", "concrete", "cable", "cables",
        "xlpe", "pvc insulated", "conductor", "steel", "reinforcement", "insulation",
        "mineral wool", "glass wool", "flange", "gasket", "paint", "distemper",
        "sanitary fittings", "wash basin", "water closet", "urinal", "vitreous china"
    ]
    # General / Code indicators
    general_keywords = [
        "hygiene", "haccp", "food premises", "safety code", "building code",
        "national building code", "quality control", "audit", "general specification",
        "code of practice"
    ]

    # Clean token-based matching supporting singular and plural
    exec_hits = sum(1 for k in exec_keywords if re.search(r'\b' + re.escape(k) + r'(?:s|es)?\b', tl))
    prod_hits = sum(1 for k in product_keywords if re.search(r'\b' + re.escape(k) + r'(?:s|es)?\b', tl))
    mat_hits = sum(1 for k in material_keywords if re.search(r'\b' + re.escape(k) + r'(?:s|es)?\b', tl))
    gen_hits = sum(1 for k in general_keywords if re.search(r'\b' + re.escape(k) + r'(?:s|es)?\b', tl))

    # If action is strongly civil / installation execution (e.g. laying of, trenching, civil works)
    if re.search(r'\b(?:laying\s+of|civil\s+works|trenching|rewiring|earthing\s+work|plastering)\b', tl):
        return "installation_execution"

    # Precedence logic
    if prod_hits > 0 and prod_hits >= mat_hits:
        return "product_equipment"
    if mat_hits > 0 and mat_hits >= exec_hits:
        return "material"
    if exec_hits > 0:
        return "installation_execution"
    if gen_hits > 0:
        return "general_specification"

    if any(w in tl for w in ["work", "supply", "execution", "renovation"]):
        return "installation_execution"
    return "general_specification"


# ---------------------------------------------------------------------------
# Tender Metadata Helper
# ---------------------------------------------------------------------------

def _lookup_tender_id_from_file(pdf_path: str) -> str:
    base = os.path.basename(pdf_path)
    meta_path = "dataset/tender_metadata.csv"
    if os.path.exists(meta_path):
        try:
            with open(meta_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("original_filename") == base or os.path.basename(row.get("file_path", "")) == base:
                        return row.get("tender_id", "")
        except Exception:
            pass

    m = re.search(r'(\d+)\.pdf$', base)
    if m:
        return f"T{int(m.group(1)):03d}"
    return "T_UNKNOWN"


def _get_field_text(lines: List[str], start_tag: str, end_tags: List[str]) -> str:
    """Helper to collect multi-line text between start_tag and any marker in end_tags."""
    if start_tag not in lines:
        return ""
    idx = lines.index(start_tag) + 1
    content = []
    while idx < len(lines) and not any(lines[idx].startswith(et) for et in end_tags):
        content.append(lines[idx])
        idx += 1
    return " ".join(content).strip()


# ---------------------------------------------------------------------------
# Public Extraction API
# ---------------------------------------------------------------------------

def extract_from_text(
    text: str,
    requirement_id: str = "REQ-001",
    tender_id: Optional[str] = None
) -> Requirement:
    """
    Extracts a Requirement object from a plain text requirement string.
    """
    cleaned_text = re.sub(r'\s+', ' ', text.strip())
    cat = classify_category(cleaned_text)
    explicit_stds = detect_explicit_standards(cleaned_text)
    decomp = decompose_requirement(cleaned_text)
    return Requirement(
        requirement_id=requirement_id,
        requirement_text=cleaned_text,
        category=cat,
        tender_id=tender_id,
        page=1,
        section="User Input",
        explicit_standards=explicit_stds,
        raw_context=cleaned_text,
        components=decomp.components,
        decomposition_confidence=decomp.decomposition_confidence
    )


def extract_from_pdf(pdf_path: str, tender_id: Optional[str] = None) -> List[Requirement]:
    """
    Extracts candidate technical procurement requirements from a tender PDF.
    Filters out CPPP administrative boilerplates and isolates technical work statements.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file does not exist: {pdf_path}")

    t_id = tender_id or _lookup_tender_id_from_file(pdf_path)

    doc = pymupdf.open(pdf_path)
    full_text = "\n".join(doc[pno].get_text() for pno in range(len(doc)))
    lines = [l.strip() for l in full_text.splitlines() if l.strip()]

    end_markers = [
        "Work Description", "Pre Qualification", "Independent External",
        "Tender Value", "Product Category", "Sub category", "Contract Type",
        "Location", "Critical Dates", "Bid Validity", "Period Of Work",
        "Basic Details", "Tender Documents", "Payment Instruments", "Organisation Chain"
    ]

    title = _get_field_text(lines, "Title", end_markers)
    work_desc = _get_field_text(lines, "Work Description", end_markers)

    requirements: List[Requirement] = []
    seen_texts = set()
    req_counter = 1

    # Primary requirements from Title and Work Description
    for text_block, sec_name in [(title, "Tender Title / Scope"), (work_desc, "Work Description")]:
        if text_block and len(text_block) > 12:
            clean_block = re.sub(r'\s+', ' ', text_block).strip()
            if clean_block.lower() not in seen_texts:
                seen_texts.add(clean_block.lower())
                cat = classify_category(clean_block)
                explicit_stds = detect_explicit_standards(clean_block)
                decomp = decompose_requirement(clean_block)
                requirements.append(Requirement(
                    requirement_id=f"{t_id}-R{req_counter:03d}",
                    requirement_text=clean_block,
                    category=cat,
                    tender_id=t_id,
                    page=1,
                    section=sec_name,
                    explicit_standards=explicit_stds,
                    raw_context=clean_block,
                    components=decomp.components,
                    decomposition_confidence=decomp.decomposition_confidence
                ))
                req_counter += 1

    # Additional specific technical lines from document pages
    for pno in range(len(doc)):
        page_lines = [l.strip() for l in doc[pno].get_text().splitlines() if l.strip()]
        for line_str in page_lines:
            if len(line_str) < 25:
                continue
            if any(re.search(bp, line_str, re.IGNORECASE) for bp in BOILERPLATE_IGNORE_PATTERNS):
                continue

            has_std = bool(STANDARD_REGEX.search(line_str))
            has_tech_kw = any(kw in line_str.lower() for kw in [
                "replacement of", "supply and installation", "pipeline", "valve",
                "cables", "transformer", "laying of", "sanitary", "fittings",
                "food outlet", "earthing", "pumps", "ht panel", "bus trunking", "tiles"
            ])

            if has_std or has_tech_kw:
                clean_l = re.sub(r'\s+', ' ', line_str).strip()
                # Substring check against existing requirements
                if any(clean_l.lower() in existing.requirement_text.lower() for existing in requirements):
                    continue
                if clean_l.lower() in seen_texts:
                    continue

                seen_texts.add(clean_l.lower())
                cat = classify_category(clean_l)
                explicit_stds = detect_explicit_standards(clean_l)
                decomp = decompose_requirement(clean_l)

                requirements.append(Requirement(
                    requirement_id=f"{t_id}-R{req_counter:03d}",
                    requirement_text=clean_l,
                    category=cat,
                    tender_id=t_id,
                    page=pno + 1,
                    section=f"Page {pno + 1}",
                    explicit_standards=explicit_stds,
                    raw_context=clean_l,
                    components=decomp.components,
                    decomposition_confidence=decomp.decomposition_confidence
                ))
                req_counter += 1

    return requirements
