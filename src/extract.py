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
    # Phase 27: Multi-Package & Technical Domain fields:
    package_id: Optional[str] = "PKG-01"
    package_name: Optional[str] = "Main Scope"
    domain: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["components"] = [c.to_dict() if hasattr(c, "to_dict") else c for c in self.components]
        return d


# ---------------------------------------------------------------------------
# Patterns & Noise Filters
# ---------------------------------------------------------------------------

STANDARD_REGEX = re.compile(
    r'\b((?:IS\s*/\s*ISO|IS\s*/\s*IEC|IS|SP)\s*[:/]?\s*\d+(?:[\s\-:]*(?:\(\s*)?(?:Part|Sec|Section|Pt\.?)?\s*[-/]?\s*\d+\s*\)?)*(?:[\s\-:]+\d{4})?)(?!\w)',
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
    """Normalizes raw standard mentions like 'IS:1239 - 2004' into canonical 'IS 1239 : 2004' while preserving prefixes and parts."""
    from src.catalogue.normalizer import StandardIdentifierNormalizer
    parsed = StandardIdentifierNormalizer.parse(raw)
    if parsed.is_valid and parsed.canonical_number and parsed.canonical_number != "UNKNOWN":
        return parsed.canonical_number
    clean = re.sub(r'\s+', ' ', raw.strip())
    clean = re.sub(r'[:/]', ' ', clean)
    clean = re.sub(r'\s*-\s*', ' : ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


def sanitize_untrusted_text(text: str) -> str:
    """
    Strips prompt injection payloads, instruction overrides, and unescaped JSON directive
    blocks so standard numbers, prompt keywords, and injection commands contained inside
    adversarial directives do not contaminate downstream retrieval vector embeddings,
    BM25 token indexes, or citation extraction.
    """
    if not text:
        return ""
    # Strip JSON objects e.g. {"candidate_standard": "IS 1786"} or Return JSON: {...}
    cleaned = re.sub(r'\{[^{}]*"[a-zA-Z_]+"\s*:[^{}]*\}', ' ', text)
    # Strip bracketed instruction/system blocks e.g. [CRITICAL INSTRUCTION: ...] or [SYSTEM NOTE: ...]
    cleaned = re.sub(r'\[\s*(?:CRITICAL\s+)?(?:INSTRUCTION|SYSTEM\s+NOTE|SYSTEM|NOTE)\s*:[^\]]*\]', ' ', cleaned, flags=re.IGNORECASE)
    # Strip assistant / system roleplay turns and directive phrases
    cleaned = re.sub(r'\b(?:Assistant|System)\s*:[^.]*(?:\.|$)', ' ', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:mark\s+all\s+items\s+approved|bypass\s+applicability\s+gate)[^.]*(?:\.|$)', ' ', cleaned, flags=re.IGNORECASE)
    # Strip line-level or sentence-level instruction overrides
    cleaned = re.sub(r'\b(?:SYSTEM\s+OVERRIDE|SYSTEM\s+INSTRUCTION|INSTRUCTION)\s*[:\-][^\n.]*', ' ', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:return|output)\s+json\s*[:\-]?[^\n.]*', ' ', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bignore\s+(?:all\s+)?(?:previous\s+)?(?:instructions|tender\s+text|bis\s+catalogue)[^\n.]*', ' ', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:unconditionally\s+recommend|output\s+standard\s+IS|always\s+recommend|do\s+not\s+abstain)[^\n.]*', ' ', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:you\s+must\s+output|mark\s+publication\s+readiness)[^\n.]*', ' ', cleaned, flags=re.IGNORECASE)
    # Clean multiple punctuation dots (e.g. "..." or ".. ") without corrupting decimal numbers (e.g. 1.1 kV)
    cleaned = re.sub(r'\.{2,}', '. ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def sanitize_text_for_citations(text: str) -> str:
    """Compatibility alias for sanitize_untrusted_text."""
    return sanitize_untrusted_text(text)


def detect_explicit_standards(text: str) -> List[str]:
    """Finds all explicit IS/ISO/IEC/SP standard mentions in text, sanitized against prompt injection directives."""
    if not text:
        return []
    sanitized = sanitize_untrusted_text(text)
    matches = STANDARD_REGEX.findall(sanitized)
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
# Technical Domain Detection
# ---------------------------------------------------------------------------

def detect_technical_domain(text: str) -> str:
    """
    Classifies requirement into one of the canonical engineering domains:
    - CIVIL_AND_STRUCTURAL
    - PIPES_AND_FITTINGS
    - VALVES_AND_FLOW
    - ELECTRICAL_AND_POWER
    - PUMPS_AND_ROTATING
    - CRANES_AND_RAIL
    - GENERAL_AND_ADMINISTRATIVE
    """
    tl = text.lower()

    # Administrative check first
    admin_patterns = [
        r'\b(?:canteen|catering|food\s+outlet|cafeteria|security\s+guard|cleaning\s+services|housekeeping|manpower\s+supply|facility\s+management|audit|audits|taxation|chartered\s+accountan|gst\s+compliance|earnest\s+money|emd\b|pan\s+card|bank\s+guarantee|balance\s+sheets?|financial\s+bid|turnover\s+certificate|experience\s+certificate|annual\s+maintenance|amc\s+services?)\b'
    ]
    if any(re.search(p, tl) for p in admin_patterns):
        return "GENERAL_AND_ADMINISTRATIVE"

    domain_scores = {
        "CIVIL_AND_STRUCTURAL": len(re.findall(r'\b(?:structural\s+steel|truss(?:es)?|purlin(?:s)?|girder|rebar|cement|concrete|rcc|tmt|tile|tiles|brick|mortar|masonry|shuttering|pavement|asphalt)\b', tl)),
        "VALVES_AND_FLOW": len(re.findall(r'\b(?:valve|valves|gate\s+valve|sluice\s+valve|globe\s+valve|check\s+valve|ball\s+valve|butterfly\s+valve|plug\s+valve|flow\s+control|flanged\s+valve)\b', tl)),
        "PIPES_AND_FITTINGS": len(re.findall(r'\b(?:pipe|pipes|piping|fitting|fittings|tube|tubes|cpvc|upvc|hdpe|ductile\s+iron|cast\s+iron\s+pipe|gi\s+pipe|plumbing|water\s+supply|potable\s+water|sewerage\s+pipe)\b', tl)),
        "ELECTRICAL_AND_POWER": len(re.findall(r'\b(?:cable|cables|conductor|conductors|wire|wires|transformer|switchgear|vfd|motor|electrical|substation|circuit\s+breaker|panel|voltage|1\.1\s*kv|11\s*kv|33\s*kv|earthing)\b', tl)),
        "PUMPS_AND_ROTATING": len(re.findall(r'\b(?:pump|pumps|pumping|submersible|centrifugal|impeller|sump\s+pump|dewatering)\b', tl)),
        "MECHANICAL_AND_MACHINERY": len(re.findall(r'\b(?:engine|engines|diesel|propulsion|compressor|compressors|turbine|turbines|generator|boiler|gear|gears|machinery|bearing|bearings|shaft)\b', tl)),
        "CRANES_AND_RAIL": len(re.findall(r'\b(?:crane|cranes|rail|rails|track|tracks|rmqc|gantry|hoist)\b', tl)),
    }

    # Priority tie-breaker: specific equipment/product overrides broad infrastructure
    # e.g. "valves for water utility network" -> VALVES_AND_FLOW > PIPES_AND_FITTINGS
    if domain_scores["VALVES_AND_FLOW"] > 0:
        return "VALVES_AND_FLOW"
    if domain_scores["PUMPS_AND_ROTATING"] > 0 and domain_scores["PUMPS_AND_ROTATING"] >= domain_scores["ELECTRICAL_AND_POWER"]:
        return "PUMPS_AND_ROTATING"

    best_domain, best_score = max(domain_scores.items(), key=lambda x: x[1])
    if best_score > 0:
        return best_domain

    return "GENERAL_AND_ADMINISTRATIVE"


# ---------------------------------------------------------------------------
# Public Extraction API
# ---------------------------------------------------------------------------

def extract_from_text(
    text: str,
    requirement_id: str = "REQ-001",
    tender_id: Optional[str] = None,
    package_id: Optional[str] = None,
    package_name: Optional[str] = None,
    domain: Optional[str] = None
) -> Requirement:
    """
    Extracts a Requirement object from a plain text requirement string.
    """
    sanitized = sanitize_untrusted_text(text)
    cat = classify_category(sanitized)
    dom = domain or detect_technical_domain(sanitized)
    explicit_stds = detect_explicit_standards(text)
    decomp = decompose_requirement(sanitized)
    return Requirement(
        requirement_id=requirement_id,
        requirement_text=sanitized,
        category=cat,
        tender_id=tender_id,
        page=1,
        section="User Input",
        explicit_standards=explicit_stds,
        raw_context=text,
        components=decomp.components,
        decomposition_confidence=decomp.decomposition_confidence,
        package_id=package_id or "PKG-01",
        package_name=package_name or "Main Scope",
        domain=dom
    )


def extract_packages_and_requirements(
    text: str,
    tender_id: Optional[str] = None
) -> List[Requirement]:
    """
    Parses complex multi-package or multi-item tender text into structured Requirement objects.
    Identifies package/lot markers and individual requirement statements.
    """
    t_id = tender_id or "TENDER"
    raw_text = text or ""

    # 1. Check for explicit package/lot/schedule markers
    # e.g. "Package 1: Civil Works", "Package A - Civil & Structural", "Lot 2: Water Supply", "General Terms and Conditions"
    pkg_pattern = re.compile(
        r'(?i)(?:^|\n)\s*(?:'
        r'(?:package|lot|part|schedule|section)\s*([0-9a-zA-Z\-_]+)\s*[:\-]\s*([^\n]+)'
        r'|'
        r'(general\s+(?:terms|conditions|requirements|administrative)[^\n]*)'
        r')'
    )
    pkg_matches = list(pkg_pattern.finditer(raw_text))

    requirements: List[Requirement] = []

    if pkg_matches:
        for idx, pm in enumerate(pkg_matches):
            if pm.group(1):
                raw_code = pm.group(1).strip()
                pkg_code = f"{int(raw_code):02d}" if raw_code.isdigit() else raw_code.upper()
                pkg_title = pm.group(2).strip()
                pkg_id = f"PKG-{pkg_code}"
            else:
                pkg_code = "GEN"
                pkg_title = pm.group(3).strip()
                pkg_id = "PKG-GEN"

            start_pos = pm.end()
            end_pos = pkg_matches[idx + 1].start() if idx + 1 < len(pkg_matches) else len(raw_text)
            pkg_body = raw_text[start_pos:end_pos].strip()

            items = _split_into_requirement_items(pkg_body)
            if not items:
                items = [pkg_title]

            for r_idx, item_text in enumerate(items, 1):
                req_id = f"{t_id}-{pkg_code}-R{r_idx:02d}"
                req = extract_from_text(
                    item_text,
                    requirement_id=req_id,
                    tender_id=t_id,
                    package_id=pkg_id,
                    package_name=pkg_title
                )
                requirements.append(req)
        return requirements

    # 2. Check for numbered or bulleted items without package headers
    items = _split_into_requirement_items(raw_text)
    if len(items) > 1:
        for r_idx, item_text in enumerate(items, 1):
            req_id = f"{t_id}-R{r_idx:03d}"
            req = extract_from_text(
                item_text,
                requirement_id=req_id,
                tender_id=t_id,
                package_id="PKG-01",
                package_name="Main Scope"
            )
            requirements.append(req)
        return requirements

    # 3. Fallback: single requirement
    return [extract_from_text(text, requirement_id=f"{t_id}-R001", tender_id=t_id)]


def _split_into_requirement_items(body: str) -> List[str]:
    """Splits a text block into individual requirement statements using numbered/bulleted markers or paragraphs."""
    lines = body.splitlines()
    items = []
    curr = []
    item_marker = re.compile(r'^\s*(?:\d+[\.\)]|\([a-zA-Z0-9]+\)|[\-\*\•])\s*(.*)')

    for line in lines:
        l_str = line.strip()
        if not l_str:
            if curr:
                joined = " ".join(curr).strip()
                if len(joined) > 15:
                    items.append(joined)
                curr = []
            continue
        m = item_marker.match(l_str)
        if m:
            if curr:
                joined = " ".join(curr).strip()
                if len(joined) > 15:
                    items.append(joined)
                curr = []
            curr.append(m.group(1).strip())
        else:
            curr.append(l_str)

    if curr:
        joined = " ".join(curr).strip()
        if len(joined) > 15:
            items.append(joined)

    if not items:
        paragraphs = [p.strip() for p in body.split("\n\n") if len(p.strip()) > 15]
        if len(paragraphs) > 1:
            return paragraphs

    return items if items else ([body.strip()] if len(body.strip()) > 15 else [])


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
                sanitized_block = sanitize_untrusted_text(clean_block)
                req_query = sanitized_block if sanitized_block else clean_block
                cat = classify_category(req_query)
                dom = detect_technical_domain(req_query)
                explicit_stds = detect_explicit_standards(clean_block)
                decomp = decompose_requirement(req_query)
                requirements.append(Requirement(
                    requirement_id=f"{t_id}-R{req_counter:03d}",
                    requirement_text=req_query,
                    category=cat,
                    tender_id=t_id,
                    page=1,
                    section=sec_name,
                    explicit_standards=explicit_stds,
                    raw_context=clean_block,
                    components=decomp.components,
                    decomposition_confidence=decomp.decomposition_confidence,
                    package_id="PKG-01",
                    package_name="Tender Scope",
                    domain=dom
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
                sanitized_l = sanitize_untrusted_text(clean_l)
                req_query_l = sanitized_l if sanitized_l else clean_l
                cat = classify_category(req_query_l)
                dom_l = detect_technical_domain(req_query_l)
                explicit_stds = detect_explicit_standards(clean_l)
                decomp = decompose_requirement(req_query_l)

                requirements.append(Requirement(
                    requirement_id=f"{t_id}-R{req_counter:03d}",
                    requirement_text=req_query_l,
                    category=cat,
                    tender_id=t_id,
                    page=pno + 1,
                    section=f"Page {pno + 1}",
                    explicit_standards=explicit_stds,
                    raw_context=clean_l,
                    components=decomp.components,
                    decomposition_confidence=decomp.decomposition_confidence,
                    package_id="PKG-01",
                    package_name="Technical Specifications",
                    domain=dom_l
                ))
                req_counter += 1

    return requirements
