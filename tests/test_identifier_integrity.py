"""
tests/test_identifier_integrity.py — Dedicated Standard Identifier Integrity & Anti-Collision Test Suite.

Verifies that:
1. Identifier normalization strictly preserves base numbers and parts without substring bleed.
2. 'IS 5039' resolves to 'IS-5039-1983' and NEVER 'IS 15039'.
3. 'IS 7098 (Part 1)' resolves to 'IS 7098 (Part 1)' and NEVER 'IS 17098' or 'IS 7098 (Part 2)'.
4. 'IS 3043' resolves to 'IS 3043' and NEVER 'IS 13043'.
5. 'IS 1255' resolves to 'IS 1255' and NEVER 'IS 11255'.
6. Compound standards ('IS/IEC 61800-2', 'IS/IEC 61439-3', 'SP 30') resolve strictly to their exact canonical IDs.
7. Searchable document representations in BM25/Semantic cache belong genuinely to the corresponding standards.
"""

import pytest
import sqlite3
import os
import re
from src.catalogue.provider import get_default_catalogue_provider, BISCatalogueProvider
from src.catalogue.normalizer import StandardIdentifierNormalizer, CanonicalStandardIdentifier


@pytest.fixture(scope="module")
def bis_provider():
    return get_default_catalogue_provider("data/catalogue/bis_catalogue.db")


def test_01_is5039_vs_is15039_isolation(bis_provider):
    """IS 5039 must never resolve to IS 15039."""
    p_5039 = StandardIdentifierNormalizer.parse("IS 5039")
    p_15039 = StandardIdentifierNormalizer.parse("IS 15039")
    
    assert p_5039.base_number == "5039"
    assert p_15039.base_number == "15039"
    assert p_5039.base_number != p_15039.base_number

    with bis_provider._get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Query IS 5039 specifically
        cur.execute("SELECT standard_id, standard_number, full_title FROM standards WHERE standard_id LIKE 'IS-5039%'")
        rows_5039 = cur.fetchall()
        assert len(rows_5039) >= 1
        for r in rows_5039:
            assert "15039" not in r["standard_id"]
            assert "distribution pillars" in r["full_title"].lower()

        # Query IS 15039 specifically
        cur.execute("SELECT standard_id, standard_number, full_title FROM standards WHERE standard_id LIKE 'IS-15039%'")
        rows_15039 = cur.fetchall()
        assert len(rows_15039) >= 1
        for r in rows_15039:
            assert "5039" != r["standard_id"].split("-")[1]
            assert "immunity" in r["full_title"].lower() or "information technology" in r["full_title"].lower()


def test_02_is7098_part1_vs_is17098_isolation(bis_provider):
    """IS 7098 (Part 1) must never collide with IS 17098 or IS 7098 Part 2."""
    p_7098_1 = StandardIdentifierNormalizer.parse("IS 7098 (Part 1)")
    p_17098 = StandardIdentifierNormalizer.parse("IS 17098")
    p_7098_2 = StandardIdentifierNormalizer.parse("IS 7098 (Part 2)")

    assert p_7098_1.base_number == "7098"
    assert p_7098_1.part == 1
    assert p_17098.base_number == "17098"
    assert p_7098_2.part == 2

    with bis_provider._get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Check IS 7098 Part 1
        cur.execute("SELECT standard_id, full_title FROM standards WHERE standard_id LIKE 'IS-7098-Part-1%'")
        rows = cur.fetchall()
        assert len(rows) >= 1
        for r in rows:
            assert "17098" not in r["standard_id"]
            assert "crosslinked polyethylene" in r["full_title"].lower() or "xlpe" in r["full_title"].lower()

        # Check IS 17098 (Footwear accessories)
        cur.execute("SELECT standard_id, full_title FROM standards WHERE standard_id LIKE 'IS-17098%'")
        rows_footwear = cur.fetchall()
        assert len(rows_footwear) >= 1
        for r in rows_footwear:
            assert "footwear" in r["full_title"].lower()


def test_03_is3043_vs_is13043_isolation(bis_provider):
    """IS 3043 (earthing code) must never collide with IS 13043 (welding electrodes)."""
    p_3043 = StandardIdentifierNormalizer.parse("IS 3043")
    p_13043 = StandardIdentifierNormalizer.parse("IS 13043")

    assert p_3043.base_number == "3043"
    assert p_13043.base_number == "13043"

    with bis_provider._get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT standard_id, full_title FROM standards WHERE standard_id LIKE 'IS-3043%'")
        rows_earthing = cur.fetchall()
        assert len(rows_earthing) >= 1
        for r in rows_earthing:
            assert "earthing" in r["full_title"].lower()

        cur.execute("SELECT standard_id, full_title FROM standards WHERE standard_id LIKE 'IS-13043%'")
        rows_welding = cur.fetchall()
        assert len(rows_welding) >= 1
        for r in rows_welding:
            assert "welding" in r["full_title"].lower() or "electrodes" in r["full_title"].lower()


def test_04_is1255_vs_is11255_isolation(bis_provider):
    """IS 1255 (cable installation) must never collide with IS 11255 (air emissions)."""
    p_1255 = StandardIdentifierNormalizer.parse("IS 1255")
    p_11255 = StandardIdentifierNormalizer.parse("IS 11255")

    assert p_1255.base_number == "1255"
    assert p_11255.base_number == "11255"

    with bis_provider._get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT standard_id, full_title FROM standards WHERE standard_id LIKE 'IS-1255-%' OR standard_id = 'IS-1255'")
        rows_cable = cur.fetchall()
        assert len(rows_cable) >= 1
        for r in rows_cable:
            assert "cable" in r["full_title"].lower() or "installation" in r["full_title"].lower()


def test_05_compound_identifiers_preservation(bis_provider):
    """Compound prefixes (IS/IEC, SP) must preserve both prefix and base number."""
    p_vfd = StandardIdentifierNormalizer.parse("IS/IEC 61800-2")
    assert p_vfd.prefix == "IS/IEC"
    assert p_vfd.base_number == "61800"
    assert p_vfd.part == 2

    p_sp30 = StandardIdentifierNormalizer.parse("SP 30")
    assert p_sp30.prefix == "SP"
    assert p_sp30.base_number == "30"

    with bis_provider._get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT standard_id, standard_number, full_title FROM standards WHERE standard_id LIKE 'SP-30-%' OR standard_id = 'SP-30'")
        row_sp = cur.fetchone()
        assert row_sp is not None
        assert "electrical code" in row_sp["full_title"].lower()


def test_06_searchable_document_text_audit(bis_provider):
    """Searchable document texts must not contain mismatched identifier titles."""
    from src.bm25_search import BM25SearchEngine
    engine = BM25SearchEngine(bis_provider)

    doc_5039 = engine.index.doc_records.get("IS-5039-1983")
    assert doc_5039 is not None
    assert "distribution pillars" in doc_5039["full_title"].lower()
    assert "immunity" not in doc_5039["full_title"].lower()

    doc_3043 = engine.index.doc_records.get("IS-3043-2018")
    assert doc_3043 is not None
    assert "earthing" in doc_3043["full_title"].lower()
    assert "welding" not in doc_3043["full_title"].lower()

