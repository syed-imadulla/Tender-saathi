"""Extract Indian Standard references and context from tender text."""

import re


STANDARD_PATTERNS = [
    # IS / ISO / IEC with standard number: e.g., IS 1239, IS:2062, IS/ISO 9001, IS/IEC 60335, IS 456-2000
    re.compile(r'\b(IS\s*[:/]?\s*(?:ISO|IEC)?\s*\d+(?:[\s\-:]+(?:Part|Sec|Section)?\s*\d+)*(?:[\s\-:]+\d{4})?)\b', re.IGNORECASE),
    # Special Publications: e.g. SP 7, SP 30, SP:34
    re.compile(r'\b(SP\s*[:/]?\s*\d+(?:[\s\-:]+(?:Part)?\s*\d+)*(?:[\s\-:]+\d{4})?)\b', re.IGNORECASE),
    # General BIS / Indian Standard mentions:
    re.compile(r'\b(Bureau\s+of\s+Indian\s+Standards|BIS(?:\s+certified|\s+certification|\s+marked|\s+standard|\s+standards|\s+compliance|\s+specifications?)?|Indian\s+Standards?)\b', re.IGNORECASE)
]


def extract_standards_from_pages(pages, tender_id):
    """
    Extracts all explicit standard references from the tender pages.
    Returns:
        list of dict records for standard_mentions.jsonl
    """
    mentions = []
    seen_keys = set()

    for p in pages:
        pno = p["page"]
        text = p["text"]
        
        # Search lines and paragraphs for context
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line_idx, line in enumerate(lines):
            for pat in STANDARD_PATTERNS:
                for match in pat.finditer(line):
                    raw_standard = match.group(1).strip()
                    clean_standard = normalize_standard_name(raw_standard)
                    
                    # Context window: current line + surrounding lines
                    start_idx = max(0, line_idx - 1)
                    end_idx = min(len(lines), line_idx + 2)
                    context_snippet = " ".join(lines[start_idx:end_idx])
                    
                    # Purpose / usage detection based on context
                    purpose = determine_standard_purpose(context_snippet)

                    key = (tender_id, clean_standard, pno, line[:40])
                    if key not in seen_keys:
                        seen_keys.add(key)
                        mentions.append({
                            "tender_id": tender_id,
                            "standard": clean_standard,
                            "full_reference": raw_standard,
                            "page": pno,
                            "context": context_snippet,
                            "purpose": purpose,
                            "source": "tender"
                        })

    return mentions


def normalize_standard_name(std_str):
    """Normalize standard mention to clean representation."""
    std = std_str.strip()
    # Normalize internal whitespace and colons
    std = re.sub(r'\s*:\s*', ' : ', std)
    std = re.sub(r'\s+', ' ', std)
    # Upper-case IS prefix
    if std.lower().startswith("is"):
        std = "IS" + std[2:]
    elif std.lower().startswith("sp"):
        std = "SP" + std[2:]
    return std


def determine_standard_purpose(context):
    """Classify the apparent purpose of the standard reference in the tender."""
    ctx = context.lower()
    purposes = []
    if any(w in ctx for w in ["material", "steel", "pipe", "cement", "cable", "conductor", "grade"]):
        purposes.append("material requirement")
    if any(w in ctx for w in ["test", "testing", "sampling", "inspection", "pressure"]):
        purposes.append("testing requirement")
    if any(w in ctx for w in ["safety", "protective", "shock", "fire"]):
        purposes.append("safety requirement")
    if any(w in ctx for w in ["quality", "qa", "qc", "guarantee"]):
        purposes.append("quality requirement")
    if any(w in ctx for w in ["laying", "installation", "construction", "workmanship", "erection"]):
        purposes.append("installation/execution requirement")
    if any(w in ctx for w in ["certification", "isi mark", "bis mark", "certified"]):
        purposes.append("certification requirement")
    return ", ".join(purposes) if purposes else "general compliance specification"
