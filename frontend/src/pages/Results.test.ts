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
