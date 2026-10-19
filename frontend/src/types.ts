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
  understanding_method?: string;
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

export type AmbiguityState =
  | 'CLEAR'
  | 'AMBIGUOUS'
  | 'INCOMPLETE'
  | 'CONFLICTING'
  | 'NO_RELIABLE_MATCH'
  | 'REVIEW_REQUIRED';

export interface CompetingInterpretation {
  standard_number: string;
  title?: string;
  score?: number;
  technical_scope?: string;
  distinguishing_parameter_needed?: string;
}

export interface MultilingualMetadata {
  is_multilingual: boolean;
  detected_language: string;
  original_text: string;
  canonical_text: string;
  language_confidence: number;
  normalization_confidence: number;
  entity_preservation_status: string;
  is_translated: boolean;
  human_review_required: boolean;
  normalization_method: string;
  missing_entities?: string[];
  notes?: string[];
}

export interface Requirement {
  id: string;
  text: string;
  multilingual?: MultilingualMetadata;
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
  provenance: 'VERIFIED' | 'CURATED' | 'INFERRED' | 'UNKNOWN' | 'OFFICIAL_PRIMARY' | 'OFFICIAL_SECONDARY' | string;
  source?: string | null;
  source_url?: string | null;
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
  review_reason?: string;
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
  // Milestone 12: Controlled Ambiguity & Human Review
  ambiguity_state?: AmbiguityState;
  ambiguity_reason?: string;
  retrieval_status?: 'CANDIDATES_FOUND' | 'ZERO_RESULTS' | string;
  applicability_status?: 'APPLICABLE' | 'ALL_REJECTED' | 'REVIEW_REQUIRED' | string;
  evidence_status?: 'VALID' | 'INSUFFICIENT' | 'GROUNDING_FAILED' | string;
  missing_information?: string[];
  competing_interpretations?: CompetingInterpretation[];
  suggested_clarification_question?: string | null;
  unresolved_components?: string[];
  // Phase 16: Evidence Traceability & Recommendation Verification
  trace_record?: TraceRecord | null;
  component_trace_records?: TraceRecord[];
  // Phase 19: Normative Clause Evidence
  clause_evidence?: ClauseEvidenceData | null;
  // Phase 27 & 28: Multi-Package & Verification Tier
  package_id?: string;
  package_name?: string;
  domain?: string;
  verification_tier?: VerificationTier | string;
  passage_id?: string | null;
  clause_number?: string | null;
  edition_year?: string | null;
  traversed_cross_references?: TraversedReference[];
}

export type VerificationTier = 'CLAUSE_VERIFIED' | 'CATALOGUE_DISCOVERED' | 'SAFE_ABSTENTION';

export interface PackageSummary {
  package_id: string;
  package_name: string;
  requirement_count: number;
  clause_verified_count: number;
  catalogue_discovered_count: number;
  safe_abstention_count: number;
  human_review_count: number;
  domains: string[];
  standards: string[];
  is_general_conditions?: boolean;
}

export interface ComplementaryStandardSuite {
  suite_id: string;
  suite_name: string;
  domain: string;
  primary_standard: string;
  allied_standards: string[];
  packages_involved: string[];
  status: string;
  description: string;
}

export interface UncoveredTenderDependency {
  primary_standard: string;
  missing_dependency: string;
  dependency_title: string;
  domain: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | string;
  finding_type: string;
  message: string;
}

export interface ClauseEvidenceData {
  outcome: 'CLAUSE_EVIDENCE_FOUND' | 'CLAUSE_EVIDENCE_NOT_FOUND' | 'CORPUS_NOT_AVAILABLE' | 'CORPUS_DOCUMENT_NOT_ELIGIBLE' | 'CORPUS_LOOKUP_ERROR' | string;
  passage_text?: string | null;
  clause_identifier?: string | null;
  page_number?: number | null;
  page_end?: number | null;
  document_id?: string | null;
  standard_number?: string | null;
  edition_year?: number | null;
  source_citation?: string | null;
  source_url?: string | null;
  file_sha256?: string | null;
  passage_sha256?: string | null;
  extraction_quality_status?: string | null;
  has_table?: boolean;
  is_grounded?: boolean;
  requirement_evidence_support?: 'FULLY_SUPPORTED' | 'PARTIALLY_SUPPORTED' | 'UNSUPPORTED' | 'CONFLICTING' | 'UNVERIFIED_COVERAGE' | string;
  message?: string;
}

export interface TraceRecord {
  requirement_id: string;
  requirement_text: string;
  sub_requirement_id?: string | null;
  sub_requirement_text?: string | null;
  standard_number?: string | null;
  official_title?: string | null;
  standard_year?: number | null;
  lifecycle_status: string;
  retrieval_method: string;
  relevance_score: number;
  rank_position: number;
  supporting_passage?: string | null;
  evidence_type: string;
  evidence_source: string;
  document_id?: string | null;
  source_url?: string | null;
  content_hash?: string | null;
  applicability_decision: string;
  applicability_rejection_reasons?: string[];
  ambiguity_state: string;
  competing_standards?: string[];
  critic_decision: string;
  final_system_decision: string;
  human_review_required: boolean;
  evidence_completeness: 'SUPPORTING_EVIDENCE_AVAILABLE' | 'CATALOGUE_METADATA_ONLY' | 'EVIDENCE_INCOMPLETE' | 'HUMAN_REVIEW_REQUIRED' | 'UNKNOWN_STANDARD' | 'REJECTED_INELIGIBLE' | string;
  is_catalogue_verified: boolean;
  is_passage_verified_in_source: boolean;
  is_lifecycle_verified: boolean;
  is_human_verified: boolean;
  is_rejected_candidate: boolean;
  is_local_catalogue_verified?: boolean;
  is_official_source_authenticated?: boolean;
  is_normative_clause_verified?: boolean;
  // Phase 19: Normative Clause Evidence Fields
  clause_evidence_outcome?: string | null;
  clause_identifier?: string | null;
  clause_passage?: string | null;
  clause_page_number?: number | null;
  clause_passage_hash?: string | null;
  corpus_document_id?: string | null;
  corpus_file_sha256?: string | null;
  extraction_quality_status?: string | null;
  // Phase 20: Requirement Evidence Support State
  requirement_evidence_support?: 'FULLY_SUPPORTED' | 'PARTIALLY_SUPPORTED' | 'UNSUPPORTED' | 'CONFLICTING' | 'UNVERIFIED_COVERAGE' | string;
  validation_errors?: string[];
  validation_warnings?: string[];
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
  ambiguity_summary?: {
    clear: number;
    ambiguous: number;
    incomplete: number;
    conflicting: number;
    no_reliable_match: number;
    review_required: number;
  };
  // Phase 27 & 28: Multi-Package & Verification Tier Intelligence
  clause_verified_count?: number;
  catalogue_discovered_count?: number;
  safe_abstention_count?: number;
  package_summaries?: PackageSummary[];
  domain_distribution?: Record<string, number>;
  complementary_standards?: ComplementaryStandardSuite[];
  uncovered_tender_dependencies?: UncoveredTenderDependency[];
}


export interface OcrPageResult {
  page_number: number;
  source_type: string;
  extracted_text: string;
  ocr_used: boolean;
  language: string | null;
  confidence: number | null;
  ocr_quality_flag: string | null;
}

export interface OcrMetadata {
  ocr_used: boolean;
  ocr_pages: number;
  total_pages: number;
  any_low_quality: boolean;
  pages: OcrPageResult[];
}

export interface TenderInfo {
  id: string;
  source: string;
  file_size: number;
  timestamp: string;
  // Present for image uploads
  source_type?: string;
  ocr_metadata?: OcrMetadata;
  ocr_quality_warning?: boolean;
}

export interface AnalysisResult {
  tender: TenderInfo;
  understanding_method?: string;
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
    understanding_method?: string;
  };
}

export type AppState = 'home' | 'analyzing' | 'results';

/** Which input mode is active on the Home page */
export type InputMode = 'text' | 'pdf' | 'image';

export interface AnalysisStep {
  label: string;
  done: boolean;
}

// Phase 5: Human Review & Decision Types
export type HumanDecisionType = 'PENDING' | 'ACCEPT' | 'EDIT' | 'DISMISS';

export interface HumanReviewDecision {
  requirement_id: string;
  decision: HumanDecisionType;
  reviewer_standard?: string | null;
  reviewer_note?: string;
  reviewed_at?: string;
  system_standard?: string | null;
  system_finding?: string | null;
}

export interface ReviewProgressSummary {
  total_review_items: number;
  reviewed_count: number;
  pending_count: number;
  accepted_count: number;
  edited_count: number;
  dismissed_count: number;
  review_status: 'REVIEW_REQUIRED' | 'IN_PROGRESS' | 'REVIEW_COMPLETE';
}

export interface TenderReviewResponse {
  status: string;
  tender_id: string;
  decisions: HumanReviewDecision[];
  progress: ReviewProgressSummary;
}

// Phase 23: Standards Knowledge Graph Types
export interface GraphNode {
  id: string;
  standard_number: string;
  year?: number | null;
  title: string;
  status: string;
  verification_status: 'VERIFIED' | 'CURATED' | string;
  technical_committee?: string | null;
  scope?: string | null;
  is_focal?: boolean;
  // D3 force simulation properties
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number | null;
  fy?: number | null;
}

export interface GraphEdge {
  id: string;
  source: string | GraphNode;
  target: string | GraphNode;
  source_standard: string;
  target_standard: string;
  relationship_type: string;
  direction: 'OUTGOING' | 'INCOMING';
  evidence: string;
  evidence_clause?: string;
  provenance: 'VERIFIED' | 'CURATED' | string;
  confidence: number;
  source_url?: string | null;
}

export interface GraphHub {
  standard_id: string;
  standard_number: string;
  year?: number | null;
  full_title: string;
  status: string;
  verification_status: string;
  domain: string;
  icon: string;
  relationships_count: number;
}

export interface StandardsSearchItem {
  standard_id: string;
  standard_number: string;
  year?: number | null;
  full_title: string;
  status: string;
  technical_committee?: string | null;
  verification_status: string;
}

export interface StandardsSearchResponse {
  query: string;
  total: number;
  standards: StandardsSearchItem[];
}

export interface StandardsNeighborsResponse {
  focal_standard: GraphNode;
  nodes: GraphNode[];
  edges: GraphEdge[];
  meta: {
    total_nodes: number;
    total_edges: number;
    depth: number;
    disclaimer: string;
  };
}

export interface StandardsGraphOverviewResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  stats: {
    total_standards_in_db: number;
    total_explicit_relationships: number;
    total_normative_references: number;
    overview_nodes_count: number;
    overview_edges_count: number;
  };
  disclaimer: string;
}

export interface TraversedReference {
  source_standard: string;
  originating_standard?: string;
  originating_clause: string;
  target_standard: string;
  target_title: string;
  relationship_type: string;
  reference_kind: string;
  hop_depth: number;
  lifecycle_status: string;
  target_lifecycle_status?: string;
  is_active: boolean;
  originating_evidence: string;
  evidence_snippet?: string;
  source_citation: string;
  provenance: string;
  verification_tier?: string;
  is_contextually_relevant?: boolean;
  relevance_reason?: string;
  review_note?: string;
}

export interface StandardsTraversalResponse {
  start_standard: string;
  max_depth: number;
  traversed_references: TraversedReference[];
  count: number;
  disclaimer: string;
}


