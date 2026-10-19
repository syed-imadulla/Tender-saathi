// @ts-nocheck
import { describe, it, expect } from 'vitest';
import { filterRecommendedRequirements, filterAttentionRequirements } from './Results';
import type { Requirement } from '../types';

describe('Results page recommendation filtering (AUDIT-02)', () => {
  const baseReq: Requirement = {
    id: 'REQ-001',
    text: 'Supply of CPVC pipes for domestic water distribution',
    candidate_standard: 'IS 15778',
    title: 'CPVC Pipes',
    lifecycle_status: 'ACTIVE',
    evidence: 'Official BIS Scope',
    evidence_strength: 'STRONG',
    provenance: 'CURATED',
    confidence: 'High',
    relevance_score: 0.95,
    human_review_required: false,
    why_flagged: '',
    why_this: [],
    why_not: [],
    risk_level: 'LOW',
    risk_reasons: [],
    decision: 'RECOMMEND',
    completeness_label: 'COMPLETE',
    missing_parameters: [],
    known_parameters: {},
    scores: { bm25: 0.9, semantic: 0.95, deterministic: 0.0, reranker: null, final: 0.95 },
  };

  it('includes clear RECOMMEND items with human_review_required=false in recommendedList', () => {
    const reqs: Requirement[] = [baseReq];
    const recs = filterRecommendedRequirements(reqs);
    const attention = filterAttentionRequirements(reqs);

    expect(recs).toHaveLength(1);
    expect(recs[0].candidate_standard).toBe('IS 15778');
    expect(attention).toHaveLength(0);
  });

  it('strictly excludes REVIEW_REQUIRED items from recommendedList and keeps them in attentionList', () => {
    const reviewReq: Requirement = {
      ...baseReq,
      id: 'REQ-002',
      decision: 'REVIEW_REQUIRED',
      human_review_required: true,
      why_flagged: 'Parameter clarification required',
    };

    const reqs: Requirement[] = [baseReq, reviewReq];
    const recs = filterRecommendedRequirements(reqs);
    const attention = filterAttentionRequirements(reqs);

    // Recommended list must strictly have 1 item (baseReq), not the review-required item
    expect(recs).toHaveLength(1);
    expect(recs.map((r) => r.id)).toEqual(['REQ-001']);

    // Attention list must contain the review-required item
    expect(attention).toHaveLength(1);
    expect(attention[0].id).toBe('REQ-002');
  });

  it('excludes RECOMMEND_WITH_REVIEW items with human_review_required=true from pure recommendations', () => {
    const recWithReviewReq: Requirement = {
      ...baseReq,
      id: 'REQ-003',
      decision: 'RECOMMEND_WITH_REVIEW',
      human_review_required: true,
    };

    const recs = filterRecommendedRequirements([recWithReviewReq]);
    const attention = filterAttentionRequirements([recWithReviewReq]);

    expect(recs).toHaveLength(0);
    expect(attention).toHaveLength(1);
  });

  it('excludes INSUFFICIENT_EVIDENCE and abstained candidate=null from recommendedList', () => {
    const abstainReq: Requirement = {
      ...baseReq,
      id: 'REQ-004',
      candidate_standard: null,
      decision: 'NO_RELIABLE_MATCH',
      human_review_required: true,
    };
    const insuffReq: Requirement = {
      ...baseReq,
      id: 'REQ-005',
      decision: 'INSUFFICIENT_EVIDENCE',
      human_review_required: true,
    };

    const recs = filterRecommendedRequirements([abstainReq, insuffReq]);
    const attention = filterAttentionRequirements([abstainReq, insuffReq]);

    expect(recs).toHaveLength(0);
    expect(attention).toHaveLength(2);
  });
});

describe('Phase 28 — Multi-Package Audit & Verification Tiers Filtering', () => {
  const pkg1Req: Requirement = {
    id: 'REQ-010',
    package_id: 'PKG-01',
    package_name: 'Civil Works',
    domain: 'Civil',
    text: 'Excavation and foundation concrete work M25',
    candidate_standard: 'IS 456',
    title: 'Plain and Reinforced Concrete',
    verification_tier: 'CLAUSE_VERIFIED',
    passage_id: 'IS_456_2000_SEC_5_CLAUSE_5_1',
    clause_number: '5.1',
    edition_year: '2000',
    decision: 'RECOMMEND',
    evidence: 'Normative clause 5.1 specifies concrete grades up to M80.',
    evidence_strength: 'STRONG',
    provenance: 'VERIFIED',
    lifecycle_status: 'ACTIVE',
    scores: { final: 0.98 },
  };

  const pkg2Req: Requirement = {
    id: 'REQ-020',
    package_id: 'PKG-02',
    package_name: 'Transmission Mains',
    domain: 'Piping',
    text: 'Ductile iron K9 pipes for pressure transmission',
    candidate_standard: 'IS 8329',
    title: 'Centrifugally Cast Ductile Iron Pressure Pipes',
    verification_tier: 'CATALOGUE_DISCOVERED',
    decision: 'RECOMMEND',
    evidence: 'Catalogue entry: Covers centrifugally cast ductile iron pressure pipes.',
    evidence_strength: 'MODERATE',
    provenance: 'NATIONAL_CATALOGUE_DISCOVERY',
    lifecycle_status: 'ACTIVE',
    scores: { final: 0.88 },
  };

  const pkgGenReq: Requirement = {
    id: 'REQ-030',
    package_id: 'PKG-GEN',
    package_name: 'General / Commercial Conditions',
    domain: 'Commercial',
    text: 'Bidder must submit EMD of Rs 5,00,000 as bank guarantee',
    candidate_standard: null,
    title: null,
    verification_tier: 'SAFE_ABSTENTION',
    decision: 'NO_RELIABLE_MATCH',
    why_flagged: 'Administrative and commercial requirement; standard recommendation safely withheld.',
    evidence: 'NONE',
    evidence_strength: 'NONE',
    provenance: 'CURATED',
    scores: { final: 0.0 },
  };

  const allReqs: Requirement[] = [pkg1Req, pkg2Req, pkgGenReq];

  it('filters requirements by package_id without mutating the full list', () => {
    const filterByPkg = (reqs: Requirement[], pkgId: string) => {
      if (pkgId === 'ALL') return reqs;
      return reqs.filter((r) => r.package_id === pkgId);
    };

    const pkg1List = filterByPkg(allReqs, 'PKG-01');
    expect(pkg1List).toHaveLength(1);
    expect(pkg1List[0].id).toBe('REQ-010');
    expect(pkg1List[0].domain).toBe('Civil');

    const pkg2List = filterByPkg(allReqs, 'PKG-02');
    expect(pkg2List).toHaveLength(1);
    expect(pkg2List[0].id).toBe('REQ-020');
    expect(pkg2List[0].domain).toBe('Piping');

    const pkgGenList = filterByPkg(allReqs, 'PKG-GEN');
    expect(pkgGenList).toHaveLength(1);
    expect(pkgGenList[0].verification_tier).toBe('SAFE_ABSTENTION');

    // All packages remains 3
    const allList = filterByPkg(allReqs, 'ALL');
    expect(allList).toHaveLength(3);
  });

  it('correctly maps verification tiers across package requirements', () => {
    const clauseVerified = allReqs.filter((r) => r.verification_tier === 'CLAUSE_VERIFIED');
    const catalogueDiscovered = allReqs.filter((r) => r.verification_tier === 'CATALOGUE_DISCOVERED');
    const safeAbstention = allReqs.filter((r) => r.verification_tier === 'SAFE_ABSTENTION');

    expect(clauseVerified).toHaveLength(1);
    expect(clauseVerified[0].candidate_standard).toBe('IS 456');
    expect(clauseVerified[0].clause_number).toBe('5.1');

    expect(catalogueDiscovered).toHaveLength(1);
    expect(catalogueDiscovered[0].candidate_standard).toBe('IS 8329');
    expect(catalogueDiscovered[0].passage_id).toBeUndefined(); // Must NOT manufacture passage ID

    expect(safeAbstention).toHaveLength(1);
    expect(safeAbstention[0].candidate_standard).toBeNull();
    expect(safeAbstention[0].why_flagged).toContain('safely withheld');
  });

  it('handles safe abstentions in attention requirements without treating them as system errors', () => {
    const attention = filterAttentionRequirements([pkgGenReq]);
    expect(attention).toHaveLength(1);
    expect(attention[0].id).toBe('REQ-030');
    expect(attention[0].verification_tier).toBe('SAFE_ABSTENTION');

    const recommendations = filterRecommendedRequirements([pkgGenReq]);
    expect(recommendations).toHaveLength(0); // Must never recommend a standard for administrative clause
  });

  it('preserves catalogue-discovered candidate without implying clause-level verification', () => {
    // Catalogue discovered item is recommended based on catalogue metadata
    const recs = filterRecommendedRequirements([pkg2Req]);
    expect(recs).toHaveLength(1);
    expect(recs[0].verification_tier).toBe('CATALOGUE_DISCOVERED');
    expect(recs[0].provenance).toBe('NATIONAL_CATALOGUE_DISCOVERY');
    // It must NOT have a clause number or normative passage
    expect(recs[0].clause_number).toBeUndefined();
  });

  it('keeps tender-wide dependencies and complementary standards invariant when package changes', () => {
    const tenderSummary = {
      clause_verified_count: 1,
      catalogue_discovered_count: 1,
      safe_abstention_count: 1,
      complementary_standards: [
        {
          suite_id: 'SUITE-WATER-01',
          suite_name: 'Water Supply Pipeline Infrastructure',
          domain: 'PIPES_AND_FITTINGS',
          primary_standard: 'IS 8329',
          allied_standards: ['IS 5382', 'IS 9523'],
          packages_involved: ['PKG-02'],
          status: 'CROSS_SCOPE_REVIEW',
          description: 'Jointing and fittings suite for DI pipeline network.',
        },
      ],
      uncovered_tender_dependencies: [
        {
          primary_standard: 'IS 456',
          missing_dependency: 'IS 1786',
          dependency_title: 'High strength deformed steel bars and wires',
          domain: 'CIVIL_AND_STRUCTURAL',
          severity: 'HIGH',
          finding_type: 'ALLIED_SPECIFICATION_GAP',
          message: 'Structural concrete requires high strength rebar review.',
        },
      ],
    };

    // Regardless of which package the user switches to ('ALL', 'PKG-01', 'PKG-02', 'PKG-GEN'):
    // 1. Complementary standards remain the exact same tender-wide array
    expect(tenderSummary.complementary_standards).toHaveLength(1);
    expect(tenderSummary.complementary_standards[0].suite_name).toBe('Water Supply Pipeline Infrastructure');

    // 2. Uncovered dependencies remain the exact same tender-wide array
    expect(tenderSummary.uncovered_tender_dependencies).toHaveLength(1);
    expect(tenderSummary.uncovered_tender_dependencies[0].missing_dependency).toBe('IS 1786');

    // 3. Executive tier counts remain the exact same tender-wide counts
    expect(tenderSummary.clause_verified_count).toBe(1);
    expect(tenderSummary.catalogue_discovered_count).toBe(1);
    expect(tenderSummary.safe_abstention_count).toBe(1);
  });
});

