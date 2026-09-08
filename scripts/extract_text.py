"""Extract text and structural sections from tender PDFs."""

import os
import json
import pymupdf


def extract_tender_text(pdf_path, tender_id):
    """
    Extracts text page-by-page from a tender PDF preserving page boundaries and sections.
    Returns:
        dict with tender_id, page_count, ocr_required, extraction_method, metadata, and pages list.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = pymupdf.open(pdf_path)
    page_count = len(doc)
    pages_data = []
    total_chars = 0

    known_sections = [
        "Basic Details",
        "Payment Instruments",
        "Cover Details",
        "Tender Fee Details",
        "EMD Fee Details",
        "Work /Item(s)",
        "Critical Dates",
        "Tender Documents",
        "NIT Document",
        "Work Item Documents",
        "Tender Inviting Authority",
        "Technical Specifications",
        "Special Conditions",
        "General Conditions"
    ]

    for pno in range(page_count):
        page = doc[pno]
        text = page.get_text()
        total_chars += len(text.strip())

        page_sections = []
        for sec in known_sections:
            if sec.lower() in text.lower():
                page_sections.append(sec)

        primary_section = page_sections[0] if page_sections else "General"

        pages_data.append({
            "tender_id": tender_id,
            "page": pno + 1,
            "sections_detected": page_sections,
            "primary_section": primary_section,
            "char_count": len(text.strip()),
            "text": text
        })

    avg_chars = total_chars / max(page_count, 1)
    ocr_required = avg_chars < 50
    extraction_method = "ocr_tesseract" if ocr_required else "pymupdf_native_text"

    # Extract high-level key-values from text
    full_text = "\n".join([p["text"] for p in pages_data])
    metadata = parse_tender_summary_fields(full_text)

    result = {
        "tender_id": tender_id,
        "original_filename": os.path.basename(pdf_path),
        "file_path": os.path.abspath(pdf_path),
        "file_size": os.path.getsize(pdf_path),
        "page_count": page_count,
        "ocr_required": ocr_required,
        "extraction_method": extraction_method,
        "parsed_metadata": metadata,
        "pages": pages_data
    }

    return result


def get_field_text(lines, start_tag, end_tags):
    """Helper to collect multi-line text between start_tag and any marker in end_tags."""
    if start_tag not in lines:
        return ""
    idx = lines.index(start_tag) + 1
    content = []
    while idx < len(lines) and not any(lines[idx].startswith(et) for et in end_tags):
        content.append(lines[idx])
        idx += 1
    return " ".join(content).strip()


def parse_tender_summary_fields(text):
    """
    Parses key-value fields from eProcurement / CPPP summary tender sheets.
    Handles multi-line titles, descriptions, and categories.
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    
    end_markers = [
        "Work Description", "Pre Qualification", "Independent External",
        "Tender Value", "Product Category", "Sub category", "Contract Type",
        "Location", "Critical Dates", "Bid Validity", "Period Of Work",
        "Basic Details", "Tender Documents", "Payment Instruments"
    ]

    title = get_field_text(lines, "Title", end_markers)
    work_desc = get_field_text(lines, "Work Description", end_markers)
    prod_cat = get_field_text(lines, "Product Category", end_markers)
    sub_cat = get_field_text(lines, "Sub category", end_markers)
    contract_type = get_field_text(lines, "Form of contract", end_markers)
    location = get_field_text(lines, "Location", end_markers)

    data = {
        "tender_id": "",
        "tender_ref_number": "",
        "organisation_chain": "",
        "title": title,
        "work_description": work_desc,
        "product_category": prod_cat,
        "sub_category": sub_cat,
        "tender_category": "",
        "contract_type": contract_type,
        "tender_value": "",
        "location": location,
        "source_url": ""
    }

    for i, line in enumerate(lines):
        if line == "Tender ID" and i + 1 < len(lines):
            data["tender_id"] = lines[i + 1]
        elif line == "Tender Reference Number" and i + 1 < len(lines):
            data["tender_ref_number"] = lines[i + 1]
        elif line == "Organisation Chain" and i + 1 < len(lines):
            data["organisation_chain"] = lines[i + 1]
        elif line == "Tender Category" and i + 1 < len(lines):
            data["tender_category"] = lines[i + 1]
        elif line == "Tender Value in ₹" and i + 1 < len(lines):
            data["tender_value"] = lines[i + 1]
        elif "https://eprocure.gov.in" in line and not data["source_url"]:
            data["source_url"] = line

    return data
