"""Extract candidate technical requirements from tender text and layout."""

import re


IGNORE_FORM_QUESTIONS = [
    "is multi currency",
    "allow two stage bidding",
    "general technical",
    "evaluation allowed",
    "itemwise technical evaluation",
    "withdrawal allowed",
    "should allow nda",
    "allow preferential bidder",
    "payment instruments",
    "cover details",
    "tender fee details",
    "emd fee details",
    "critical dates",
    "document download",
    "bid submission",
    "clarification",
    "latest corrigendum",
    "tender inviting authority",
    "eprocurement system",
    "date :"
]


def extract_candidate_requirements(tender_doc, standard_mentions):
    """
    Extract candidate technical requirements from tender text.
    Each requirement is flagged as a candidate with human_verified = False.
    Returns:
        list of requirement records (one dict per requirement)
    """
    tender_id = tender_doc["tender_id"]
    parsed_meta = tender_doc.get("parsed_metadata", {})
    pages = tender_doc.get("pages", [])
    
    requirements = []
    req_counter = 1

    standards_by_page = {}
    for sm in standard_mentions:
        p = sm["page"]
        standards_by_page.setdefault(p, []).append(sm["standard"])

    title = parsed_meta.get("title", "").strip()
    work_desc = parsed_meta.get("work_description", "").strip()
    prod_cat = parsed_meta.get("product_category", "").strip()

    seen_reqs = set()

    def add_req(req_text, category_override=None, section_name="Work /Item(s)", page_no=1, evidence_text=None):
        nonlocal req_counter
        norm_key = re.sub(r'\s+', ' ', req_text.strip().lower())
        if not norm_key or norm_key in seen_reqs or len(norm_key) < 10:
            return
        if any(ign in norm_key for ign in IGNORE_FORM_QUESTIONS):
            return

        seen_reqs.add(norm_key)
        cat, val, unit = detect_requirement_category(req_text)
        if category_override:
            cat = category_override

        std_ref = find_matching_standard(req_text, standard_mentions) or (
            standards_by_page.get(page_no, [None])[0] if find_standard_in_line(req_text) else None
        )

        requirements.append({
            "tender_id": tender_id,
            "requirement_id": f"{tender_id}-R{req_counter:03d}",
            "status": "candidate",
            "is_candidate": True,
            "human_verified": False,
            "category": cat,
            "candidate_requirement": req_text.strip(),
            "value": val,
            "unit": unit,
            "mentioned_standard": std_ref,
            "has_explicit_standard": bool(std_ref),
            "page": page_no,
            "section": section_name,
            "evidence": evidence_text or req_text.strip()
        })
        req_counter += 1

    # 1. Scope decomposition from title & description
    base_text = work_desc if len(work_desc) >= len(title) else title
    if base_text:
        add_req(base_text, section_name="Work /Item(s) - Main Scope", evidence_text=f"Title/Scope: {base_text}")

        # Split compound clauses (e.g. incl replacement of..., repair of..., SITC of...)
        clauses = re.split(r'[,;]|\bincl\b|\bincluding\b|\band\b', base_text, flags=re.IGNORECASE)
        for clause in clauses:
            clause = clause.strip()
            if any(tech_kw in clause.lower() for tech_kw in [
                "pipe", "cable", "pump", "valve", "panel", "insulation", "dg set",
                "flange", "fitting", "tiles", "plaster", "cc works", "shed", "shelter",
                "wall", "switchgear", "motor", "vfd", "stp", "transformer"
            ]):
                add_req(clause, section_name="Work /Item(s) - Specification Clause", evidence_text=f"Clause from Scope: {clause}")

    # 2. Extract Document & BOQ Descriptions from Page 2
    for page_data in pages:
        pno = page_data["page"]
        text = page_data["text"]
        lines = [l.strip() for l in text.splitlines() if l.strip()]

        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(ign in line_lower for ign in IGNORE_FORM_QUESTIONS):
                continue

            # Check for technical item descriptions in documents / BOQ
            if any(k in line_lower for k in ["tendernotice", "boq", "work description", "technical specification", "schedule of work"]):
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if len(next_line) > 15 and not any(ign in next_line.lower() for ign in IGNORE_FORM_QUESTIONS):
                        add_req(next_line, section_name="Tender Documents", page_no=pno, evidence_text=f"Document Specification: {next_line}")

            # Specific technical lines
            if any(kw in line_lower for kw in [
                "replacement", "repair", "installation", "pipeline", "underground cable",
                "food outlet", "waste collection", "partition wall", "sewerage pipeline",
                "mechanical maintenance", "distribution boards", "surveillance cum op shelter"
            ]) and len(line) > 15:
                add_req(line, section_name=page_data["primary_section"], page_no=pno, evidence_text=f"Page {pno} line: {line}")

    return requirements


def detect_requirement_category(text):
    """Detect category, value, and unit from requirement snippet."""
    t = text.lower()
    cat = "general_specification"
    val = None
    unit = None

    if any(w in t for w in ["pipe", "cable", "steel", "cement", "cpvc", "gi", "upvc", "insulation", "tile", "tiles", "timber", "conductor"]):
        cat = "material"
    elif any(w in t for w in ["pump", "motor", "vfd", "valve", "feeder", "transformer", "dg set", "panel", "shutter", "fitting", "fittings"]):
        cat = "product_equipment"
    elif any(w in t for w in ["test", "testing", "pressure test", "sampling", "commissioning"]):
        cat = "testing_requirement"
    elif any(w in t for w in ["inspection", "witness", "inspecting"]):
        cat = "inspection_requirement"
    elif any(w in t for w in ["laying", "installation", "erection", "sitc", "repair", "maintenance", "plaster", "cc works", "renovation", "construction"]):
        cat = "installation_execution"
    elif any(w in t for w in ["isi", "bis", "certification", "compliance", "standard", "quality"]):
        cat = "certification_compliance"

    # Value & Unit detection (e.g. 5 no, 4 lane, 160 bn, 240 v, etc.)
    m = re.search(r'\b(\d+(?:\.\d+)?)\s*(mm|cm|m|inch|v|kv|kva|hp|kw|rpm|kg|ton|nos?|lane)\b', t)
    if m:
        val = m.group(1)
        unit = m.group(2)

    return cat, val, unit


def find_matching_standard(text, standard_mentions):
    """Check if any extracted standard is mentioned within this snippet."""
    for sm in standard_mentions:
        if sm["standard"].lower() in text.lower():
            return sm["standard"]
    return None


def find_standard_in_line(line):
    """Regex check for IS/SP/BIS in line."""
    return bool(re.search(r'\b(IS\s*[:/]?\s*\d+|SP\s*[:/]?\s*\d+|BIS)\b', line, re.IGNORECASE))
