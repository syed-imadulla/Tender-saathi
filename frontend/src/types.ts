// types.ts — TypeScript types matching the TenderSaathi normalized API contract

export interface RelatedStandard {
  standard_number: string;
  title?: string;
  relationship_type?: string;
  direction?: string;
  lifecycle_status?: string;
  review_note?: string;
}

export interface ScoreBreakdown {
  bm25: number;
  semantic: number;
  deterministic: number;
  reranker: number | null;
  final: number;
}

export interface AIUnderstanding {
  facets: Record<string, string | string[]>;
  provider: string;
  model: string;
  is_fallback: boolean;
}

export interface ApplicabilityData {
  standard_number?: string;
  title?: string;
  applicable?: boolean;
  decision?: 'APPLICABLE' | 'REVIEW_REQUIRED' | 'NOT_APPLICABLE' | string;
  applicability_score?: number;
  domain_match?: boolean;
  product_match?: boolean;
  scope_match?: boolean;
  application_match?: boolean;
  evidence_support?: boolean;
  conflict_flags?: string[];
  reasons?: string[];
  rejection_reasons?: string[];
}

export interface Requirement {
  id: string;
  text: string;
  category: string;
  // Standard
  candidate_standard: string | null;
  title: string;
  lifecycle_status: string;
  successor_standard: string | null;
  superseded_citation: string | null;
  // Evidence
  evidence: string;
  evidence_strength: 'STRONG' | 'MODERATE' | 'WEAK' | 'NONE';
  provenance: 'VERIFIED' | 'CURATED' | 'INFERRED' | 'UNKNOWN';
  // Quality
  confidence: string;
  relevance_score: number;
  // Review
  human_review_required: boolean;
  why_flagged: string;
  why_this: string[];
  why_not: string[];
  risk_level: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  risk_reasons: string[];
  decision: string;
  // Completeness
  completeness_label: string;
  missing_parameters: string[];
  known_parameters: Record<string, string>;
  // Graph
  related_standards: RelatedStandard[];
  // AI
  ai_understanding: AIUnderstanding;
  // Scores
  scores: ScoreBreakdown;
  // Applicability (Milestone 9)
  applicability?: ApplicabilityData | null;
}

export interface AnalysisSummary {
  requirements_analyzed: number;
  needs_attention: number;
  looks_good: number;
  standards_to_update: number;
  review_required_count: number;
  insufficient_evidence_count: number;
  active_count: number;
  superseded_count: number;
  withdrawn_count: number;
  related_standards_count: number;
  evidence_distribution: Record<string, number>;
  risk_distribution: Record<string, number>;
}

export interface TenderInfo {
  id: string;
  source: string;
  file_size: number;
  timestamp: string;
}

export interface AnalysisResult {
  tender: TenderInfo;
  summary: AnalysisSummary;
  readiness: 'READY_FOR_REVIEW' | 'REVIEW_REQUIRED' | 'INSUFFICIENT_EVIDENCE';
  readiness_reasons: string[];
  sections: {
    needs_attention: Requirement[];
    looks_good: Requirement[];
    standards_to_update: Requirement[];
  };
  requirements: Requirement[];
  metadata: {
    ai_provider: string;
    ai_model: string;
    retrieval_mode: string;
    is_ai_fallback: boolean;
  };
}

export type AppState = 'home' | 'analyzing' | 'results';

export interface AnalysisStep {
  label: string;
  done: boolean;
}
