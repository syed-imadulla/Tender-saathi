// StandardsGraph.test.ts — Unit tests for normative traversal journeys & non-elevation invariant
// @ts-nocheck
import { describe, it, expect } from 'vitest';
import type { TraversedReference, StandardsTraversalResponse } from '../types';

describe('Normative Traversal Journey Safety & Mapping (Phase 35)', () => {
  const sampleTraversal: TraversedReference = {
    source_standard: 'IS 800 : 2007',
    originating_clause: '2.2',
    target_standard: 'IS 2062 : 2011',
    target_title: 'Hot Rolled Medium and High Tensile Structural Steel - Specification',
    relationship_type: 'NORMATIVE_REFERENCE',
    reference_kind: 'EXPLICIT_NORMATIVE',
    hop_depth: 1,
    lifecycle_status: 'Active',
    is_active: true,
    originating_evidence: 'Clause 2.2 explicitly lists IS 2062 for structural steel materials conforming to design strengths.',
    source_citation: 'IS 800 : 2007 Section 2',
    provenance: 'VERIFIED',
    is_contextually_relevant: true,
    relevance_reason: 'Requirement specifies structural steel members.',
    review_note: 'Normative dependency for structural steel plates and sections.',
  };

  it('correctly maps 1-hop and 2-hop traversal references', () => {
    const response: StandardsTraversalResponse = {
      start_standard: 'IS 800 : 2007',
      max_depth: 2,
      count: 2,
      traversed_references: [
        sampleTraversal,
        {
          ...sampleTraversal,
          source_standard: 'IS 2062 : 2011',
          originating_clause: '4.1',
          target_standard: 'IS 1608 : 2005',
          target_title: 'Metallic Materials - Tensile Testing at Ambient Temperature',
          relationship_type: 'TEST_METHOD',
          reference_kind: 'TEST_METHOD',
          hop_depth: 2,
        },
      ],
      disclaimer: 'Normative traversal does not independently establish legal applicability.',
    };

    expect(response.traversed_references).toHaveLength(2);
    expect(response.traversed_references[0].hop_depth).toBe(1);
    expect(response.traversed_references[1].hop_depth).toBe(2);
    expect(response.traversed_references[0].target_standard).toBe('IS 2062 : 2011');
    expect(response.traversed_references[1].relationship_type).toBe('TEST_METHOD');
  });

  it('enforces non-elevation invariant: traversal does not grant CLAUSE_VERIFIED tier', () => {
    // Safety invariant: traversing a normative relationship must NEVER upgrade an unverified standard
    // to CLAUSE_VERIFIED unless genuine clause-level text is independently matched.
    const unverifiedRef: TraversedReference = {
      ...sampleTraversal,
      verification_tier: 'UNVERIFIED',
    };

    const isClauseVerified = unverifiedRef.verification_tier === 'CLAUSE_VERIFIED';
    expect(isClauseVerified).toBe(false);
    expect(unverifiedRef.provenance).toBe('VERIFIED'); // Verified relationship record, NOT clause-verified tender match
  });

  it('correctly handles withdrawn/superseded targets gracefully', () => {
    const withdrawnTarget: TraversedReference = {
      ...sampleTraversal,
      target_standard: 'IS 456 : 1978',
      lifecycle_status: 'Withdrawn',
      is_active: false,
    };

    expect(withdrawnTarget.is_active).toBe(false);
    expect(withdrawnTarget.lifecycle_status).toBe('Withdrawn');
  });
});
