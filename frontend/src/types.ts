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
  evidence_standard?: string | null;
  why_it_matches?: string;
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
  // Milestone 10: Standards Dependency & Coverage
  dependencies?: DependencyItem[];
  standards_coverage?: StandardsCoverage | null;
  potential_gaps?: GapItem[];
  verified_missing?: GapItem[];
  potentially_missing?: GapItem[];
  related_for_review?: GapItem[];
  // Milestone 11: Regulatory & Certification Intelligence
  regulatory?: RegulatoryData | null;
}

export interface RegulatoryItem {
  category: 'BIS_PRODUCT_CERTIFICATION' | 'QCO' | 'CRS' | 'HALLMARKING' | string;
  status: 'CURRENT' | 'UPCOMING' | 'APPLICABLE' | 'NOT_IDENTIFIED' | 'REVIEW_REQUIRED' | 'NOT_APPLICABLE' | 'UNKNOWN' | string;
  matched_product: string;
  standard_number: string;
  legal_basis: string;
  source: string;
  source_url?: string;
  effective_date?: string | null;
  provenance: string;
  confidence: number;
  human_review_required: boolean;
  explanation: string;
  additional_metadata?: Record<string, any>;
}

export interface RegulatoryData {
  certification?: RegulatoryItem;
  qco?: RegulatoryItem;
  crs?: RegulatoryItem;
  hallmarking?: RegulatoryItem;
}

export interface DependencyItem {
  standard_number: string;
  title: string;
  relationship_type: string;
  dependency_status: string;
  direction: string;
  lifecycle_status: string;
  provenance: string;
  evidence_strength: string;
  evidence_text: string;
  source: string;
  confidence: number;
  why_related: string;
  functional_category: string;
  is_applicable_to_requirement: boolean;
  applicability_decision: string;
}

export interface GapItem {
  gap_type: 'STANDARD_GAP' | 'SPECIFICATION_GAP' | 'LIFECYCLE_RISK' | 'EVIDENCE_GAP' | string;
  standard_number?: string | null;
  title?: string | null;
  gap_severity: 'VERIFIED_MISSING' | 'POTENTIALLY_MISSING' | 'RELATED_FOR_REVIEW' | 'CRITICAL' | 'HIGH' | 'MEDIUM' | string;
  relationship_type?: string | null;
  description: string;
  why_flagged: string;
  remediation_suggestion: string;
  provenance: string;
  confidence: number;
}

export interface CoverageSummary {
  primary_standard_covered: boolean;
  total_dependencies: number;
  covered_in_tender: number;
  potentially_missing: number;
  verified_missing: number;
  related_for_review: number;
  coverage_percentage: number;
}

export interface StandardsCoverage {
  requirement_id: string;
  requirement_text: string;
  primary_standard?: { standard: string; title: string; status: string } | null;
  coverage_summary: CoverageSummary;
  dependencies_coverage: Array<{
    standard: string;
    title: string;
    relationship_type: string;
    dependency_status: string;
    coverage_status: string;
    evidence: string;
    provenance: string;
    why_flagged?: string;
  }>;
  specification_gaps: GapItem[];
  standard_gaps: GapItem[];
  all_gaps: GapItem[];
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
  dependency_count?: number;
  normative_reference_count?: number;
  allied_standard_count?: number;
  test_standard_count?: number;
  installation_standard_count?: number;
  verified_missing_count?: number;
  potentially_missing_count?: number;
  related_for_review_count?: number;
  standards_coverage?: Record<string, any>;
  gap_summary?: Record<string, any>;
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
