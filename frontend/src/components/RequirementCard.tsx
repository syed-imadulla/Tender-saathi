// RequirementCard.tsx — Specialized cards for the TenderSaathi Recommendation UI
import './RequirementCard.css';
import type { Requirement, RelatedStandard } from '../types';

export function areStandardsEquivalent(std1?: string | null, std2?: string | null): boolean {
  if (!std1 || !std2) return false;
  const norm = (s: string) => s.split(':')[0].trim().toUpperCase().replace(/\s+/g, ' ');
  return norm(std1) === norm(std2);
}

export function getWhyItMatches(req: Requirement): string {
  if (!req.candidate_standard || req.candidate_standard === 'INSUFFICIENT_INFORMATION' || req.candidate_standard === 'NONE') {
    return 'No reliable standard match found in the available catalogue.';
  }

  // EVIDENCE CONSISTENCY RULE:
  // Before displaying evidence, validate: evidence.standard_number == candidate_standard
  // If this cannot be established, do NOT display candidate-specific evidence.
  if (req.evidence_standard && !areStandardsEquivalent(req.candidate_standard, req.evidence_standard)) {
    return 'Match identified from the requirement context; supporting evidence needs review.';
  }

  // Use backend validated why_it_matches if provided
  if (req.why_it_matches && req.why_it_matches.trim().length > 0) {
    return req.why_it_matches.trim();
  }

  // Look in why_this array from backend
  if (req.why_this && req.why_this.length > 0) {
    const scopeItem = req.why_this.find((item) =>
      item.toLowerCase().includes('scope explicitly covers') ||
      item.toLowerCase().includes('directly covers') ||
      item.toLowerCase().includes('covers')
    );

    if (scopeItem) {
      const cleaned = scopeItem
        .replace(/^Authoritative scope explicitly covers application:\s*["']?/, '')
        .replace(/["']?\s*$/, '')
        .replace(/^(Exact Match:\s*|Direct Match:\s*)/i, '')
        .trim();

      if (cleaned.length > 10 && !cleaned.toLowerCase().startsWith('insufficient')) {
        return cleaned;
      }
    }

    const titleItem = req.why_this.find((item) =>
      item.toLowerCase().includes('title directly matches') ||
      item.toLowerCase().includes('official title aligns')
    );
    if (titleItem) {
      return titleItem;
    }

    return req.why_this[0];
  }

  // Fallback to grounded evidence text
  if (req.evidence && req.evidence.toLowerCase() !== 'none' && !req.evidence.toLowerCase().includes('insufficient evidence')) {
    return req.evidence.replace(/^(Exact Match:\s*|Direct Match:\s*)/i, '').trim();
  }

  if (req.title) {
    return `Official title aligns with specification: "${req.title}".`;
  }

  return 'Verified match with active Indian Standard catalogue.';
}

export interface RecommendationCardProps {
  req: Requirement;
  isPrimary?: boolean;
  onOpenEvidence: (req: Requirement) => void;
}

export function RecommendationCard({ req, isPrimary = false, onOpenEvidence }: RecommendationCardProps) {
  const isSupersededNotice = Boolean(req.superseded_citation);
  const isStrongMatch = req.decision === 'RECOMMEND' || (req.evidence_strength === 'STRONG' && req.relevance_score >= 0.85 && !isSupersededNotice);
  const isPotentialMatch = !isStrongMatch && (req.decision === 'RECOMMEND_WITH_REVIEW' || req.decision === 'REVIEW_REQUIRED' || req.human_review_required);

  const isExplicitlyCited = req.provenance === 'VERIFIED' ||
    (req.why_this || []).some((w) => w.toLowerCase().includes('explicitly cites') || w.toLowerCase().includes('explicitly requires'));

  const whyMatches = getWhyItMatches(req);

  return (
    <article className="rec-card" aria-label={`Recommended standard ${req.candidate_standard}`}>
      <div className="rec-card__top">
        <div className="rec-card__indicator">
          {isPotentialMatch ? (
            <span className="rec-card__icon rec-card__icon--review" aria-label="Review recommended">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="9" />
              </svg>
            </span>
          ) : (
            <span className="rec-card__icon rec-card__icon--check" aria-label="Recommended standard">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            </span>
          )}

          <div className="rec-card__standard-wrap">
            <h3 className="rec-card__standard-num">{req.candidate_standard}</h3>
            {isPrimary && <span className="rec-badge rec-badge--primary">Primary recommendation</span>}
            {isExplicitlyCited && <span className="rec-badge rec-badge--cited">Explicitly cited in tender</span>}
            {req.evidence_strength && req.evidence_strength !== 'NONE' && (
              <span className={`rec-badge ${req.evidence_strength === 'STRONG' ? 'rec-badge--strong' : 'rec-badge--moderate'}`}>
                {req.evidence_strength === 'STRONG' ? 'Strong Evidence' : 'Supporting Evidence'}
              </span>
            )}
            {req.lifecycle_status && (
              <span className={`rec-badge ${req.lifecycle_status.toLowerCase() === 'active' ? 'rec-badge--active' : 'rec-badge--warning'}`}>
                {req.lifecycle_status}
              </span>
            )}
            {req.regulatory?.qco?.status === 'CURRENT' && (
              <span className="rec-badge rec-badge--qco">Mandatory QCO</span>
            )}
            {isPotentialMatch && (
              <span className="rec-badge rec-badge--warning">Potential match — human review required</span>
            )}
          </div>
        </div>

        <button
          type="button"
          className="rec-card__see-why"
          onClick={() => onOpenEvidence(req)}
          aria-label={`See evidence why ${req.candidate_standard} was recommended`}
        >
          See why →
        </button>
      </div>

      {req.title && (
        <h4 className="rec-card__title">{req.title}</h4>
      )}

      {req.multilingual?.is_multilingual && (
        <div className="rec-card__multilingual-block" style={{ margin: '0.5rem 0', padding: '0.4rem 0.6rem', background: '#f0fdf4', borderRadius: '4px', fontSize: '0.8125rem', borderLeft: '3px solid #10b981' }}>
          <span style={{ fontWeight: 600, color: '#166534', display: 'block', fontSize: '0.75rem' }}>
            🌐 System interpretation ({req.multilingual.detected_language === 'hi' ? 'Hindi → English' : req.multilingual.detected_language === 'kn' ? 'Kannada → English' : req.multilingual.detected_language === 'ta' ? 'Tamil → English' : 'Mixed → English'}):
          </span>
          <span style={{ color: '#14532d', fontStyle: 'italic' }}>
            "{req.multilingual.canonical_text}"
          </span>
        </div>
      )}

      <div className="rec-card__why-block">

        <span className="rec-card__why-label">Why it matches:</span>
        <p className="rec-card__why-text">{whyMatches}</p>
      </div>

      {req.dependencies && req.dependencies.length > 0 && (
        <div className="rec-card__coverage-bar" style={{ marginTop: '0.75rem', paddingTop: '0.625rem', borderTop: '1px solid #f1f5f9', display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap', fontSize: '0.8125rem' }}>
          <span style={{ fontWeight: 600, color: '#475569' }}>Standards Coverage:</span>
          <span style={{ color: '#059669', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>✓ Primary standard</span>
          {req.potentially_missing && req.potentially_missing.length > 0 && (
            <span style={{ color: '#d97706', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
              ⚠ {req.potentially_missing.length} potential {req.potentially_missing.length === 1 ? 'dependency' : 'dependencies'}
            </span>
          )}
          {req.missing_parameters && req.missing_parameters.length > 0 && (
            <span style={{ color: '#d97706', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
              ⚠ Specification gap
            </span>
          )}
          <button
            type="button"
            onClick={() => onOpenEvidence(req)}
            style={{ marginLeft: 'auto', background: 'none', border: 'none', color: '#2563eb', cursor: 'pointer', fontWeight: 500, fontSize: '0.8125rem', padding: 0 }}
          >
            Review dependencies ({req.dependencies.length}) →
          </button>
        </div>
      )}
    </article>
  );
}

export interface AttentionCardProps {
  req: Requirement;
  onOpenEvidence: (req: Requirement) => void;
}

export function AttentionCard({ req, onOpenEvidence }: AttentionCardProps) {
  const ambiguityState = req.ambiguity_state || (
    req.decision === 'NO_RELIABLE_MATCH' ? 'NO_RELIABLE_MATCH' :
    req.missing_parameters && req.missing_parameters.length > 0 ? 'INCOMPLETE' :
    'REVIEW_REQUIRED'
  );

  const isConflicting = ambiguityState === 'CONFLICTING';
  const isIncomplete = ambiguityState === 'INCOMPLETE';
  const isAmbiguous = ambiguityState === 'AMBIGUOUS';
  const isNoMatch = ambiguityState === 'NO_RELIABLE_MATCH';
  const isReviewRequired = ambiguityState === 'REVIEW_REQUIRED';

  const cardClass = `attention-card attention-card--${ambiguityState.toLowerCase().replace(/_/g, '-')}`;

  let stateTitle = 'Specification details need clarification';
  let badgeLabel = 'REVIEW REQUIRED';
  let badgeClass = 'badge--warning';

  if (isConflicting) {
    stateTitle = 'Conflicting Specifications Detected';
    badgeLabel = 'CONFLICTING';
    badgeClass = 'badge--superseded';
  } else if (isIncomplete) {
    stateTitle = 'Incomplete Specification — Critical Parameters Missing';
    badgeLabel = 'INCOMPLETE';
    badgeClass = 'badge--warning';
  } else if (isAmbiguous) {
    stateTitle = 'Ambiguous Requirement — Multiple Competing Standards';
    badgeLabel = 'AMBIGUOUS';
    badgeClass = 'badge--primary';
  } else if (isNoMatch) {
    stateTitle = 'No Reliable Indian Standard Match Found in Catalogue';
    badgeLabel = 'NO RELIABLE MATCH';
    badgeClass = 'badge--low';
  } else if (isReviewRequired) {
    stateTitle = 'Technical Review Required Prior to Procurement';
    badgeLabel = 'REVIEW REQUIRED';
    badgeClass = 'badge--warning';
  }

  const missingList = (req.missing_information && req.missing_information.length > 0)
    ? req.missing_information
    : (req.missing_parameters && req.missing_parameters.length > 0)
    ? req.missing_parameters
    : [];

  return (
    <article className={cardClass} aria-label={`Requirement needing attention: ${badgeLabel}`}>
      <div className="attention-card__header">
        <div className="attention-card__left">
          <span className="attention-card__icon" aria-hidden="true">
            {isConflicting ? (
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#dc2626" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
              </svg>
            ) : isAmbiguous ? (
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#7c3aed" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                <path d="M16 3h5v5" />
                <path d="M8 21H3v-5" />
                <path d="M21 3l-7.5 7.5" />
                <path d="M3 21l7.5-7.5" />
              </svg>
            ) : isNoMatch ? (
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="4.93" y1="4.93" x2="19.07" y2="19.07" />
              </svg>
            ) : (
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#ea580c" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                <line x1="12" y1="9" x2="12" y2="13" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
            )}
          </span>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px', flexWrap: 'wrap' }}>
              <h4 className="attention-card__title" style={{ margin: 0 }}>
                {stateTitle}
              </h4>
              <span className={`rec-badge ${badgeClass}`} style={{ fontSize: '0.72rem', padding: '2px 8px' }}>
                {badgeLabel}
              </span>
            </div>
            <p className="attention-card__clause">
              "{req.text.length > 130 ? `${req.text.slice(0, 127)}...` : req.text}"
            </p>
            {req.multilingual?.is_multilingual && (
              <div style={{ marginTop: '4px', fontSize: '0.8rem', color: '#0369a1', background: '#f0f9ff', padding: '3px 8px', borderRadius: '4px', borderLeft: '3px solid #0284c7' }}>
                <span style={{ fontWeight: 600 }}>
                  🌐 System interpretation ({req.multilingual.detected_language === 'hi' ? 'Hindi → English' : req.multilingual.detected_language === 'kn' ? 'Kannada → English' : req.multilingual.detected_language === 'ta' ? 'Tamil → English' : 'Mixed → English'}):
                </span>{' '}
                <span style={{ fontStyle: 'italic' }}>"{req.multilingual.canonical_text}"</span>
              </div>
            )}
          </div>
        </div>


        <button
          type="button"
          className="attention-card__see-why"
          onClick={() => onOpenEvidence(req)}
          aria-label="See technical details and audit evidence"
        >
          Audit Details →
        </button>
      </div>

      <div className="attention-card__body">
        {/* State description / reason */}
        {(req.ambiguity_reason || req.review_reason || req.why_flagged || (req.risk_reasons && req.risk_reasons[0])) && (
          <p className="attention-card__desc" style={{ marginBottom: '8px', fontWeight: 500, color: '#334155' }}>
            {req.ambiguity_reason || req.review_reason || req.why_flagged || req.risk_reasons[0]}
          </p>
        )}

        {/* Missing discriminating parameters */}
        {missingList.length > 0 && (
          <div style={{ marginTop: '6px', marginBottom: '8px' }}>
            <p className="attention-card__prompt">Critical parameters required to determine standard:</p>
            <ul className="attention-card__list">
              {missingList.map((param, i) => (
                <li key={i} className="attention-card__param-item">
                  <span className="attention-card__bullet">•</span>
                  <span>{param}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Competing Interpretations for AMBIGUOUS state */}
        {isAmbiguous && req.competing_interpretations && req.competing_interpretations.length > 0 && (
          <div className="competing-standards-block" style={{ marginTop: '8px', marginBottom: '8px', background: '#f8fafc', padding: '10px 12px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
            <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#475569', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Competing Candidate Standards (Within Separation Margin):
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {req.competing_interpretations.map((ci, idx) => (
                <div key={idx} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.85rem', flexWrap: 'wrap', gap: '4px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <strong style={{ color: '#1e293b' }}>{ci.standard_number}</strong>
                    {ci.score !== undefined && (
                      <span style={{ fontSize: '0.75rem', color: '#64748b' }}>(Score: {(ci.score).toFixed(3)})</span>
                    )}
                    {ci.title && <span style={{ color: '#475569', fontSize: '0.8rem' }}>— {ci.title}</span>}
                  </div>
                  {ci.distinguishing_parameter_needed && (
                    <span style={{ fontSize: '0.78rem', color: '#7c3aed', background: '#f5f3ff', padding: '1px 6px', borderRadius: '4px' }}>
                      Requires: {ci.distinguishing_parameter_needed}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Suggested clarification question for tender officer */}
        {req.suggested_clarification_question && (
          <div
            className="clarification-callout"
            style={{
              marginTop: '10px',
              padding: '10px 14px',
              background: isConflicting ? '#fef2f2' : isIncomplete ? '#fffbeb' : '#f8fafc',
              border: `1px solid ${isConflicting ? '#fca5a5' : isIncomplete ? '#fde68a' : '#cbd5e1'}`,
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '10px'
            }}
          >
            <span style={{ fontSize: '1rem', marginTop: '1px' }}>💬</span>
            <div style={{ fontSize: '0.85rem', lineHeight: '1.45' }}>
              <strong style={{ color: isConflicting ? '#991b1b' : isIncomplete ? '#92400e' : '#1e293b' }}>
                Actionable Tender Clarification Recommendation:
              </strong>
              <p style={{ margin: '3px 0 0 0', color: '#334155' }}>
                {req.suggested_clarification_question}
              </p>
            </div>
          </div>
        )}
      </div>
    </article>
  );
}

export interface UpdateCardProps {
  req: Requirement;
  onOpenEvidence: (req: Requirement) => void;
}

export function UpdateCard({ req, onOpenEvidence }: UpdateCardProps) {
  const citedStandard = req.superseded_citation || req.candidate_standard;
  const currentReference = req.successor_standard || req.candidate_standard;

  return (
    <article className="update-card" aria-label={`Superseded standard notice for ${citedStandard}`}>
      <div className="update-card__header">
        <div className="update-card__left">
          <span className="update-card__icon" aria-hidden="true">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
          </span>
          <div>
            <h4 className="update-card__title">
              Tender cites <strong>{citedStandard}</strong>
            </h4>
            <p className="update-card__status">This standard appears superseded.</p>
          </div>
        </div>

        <button
          type="button"
          className="update-card__see-why"
          onClick={() => onOpenEvidence(req)}
          aria-label={`See evidence regarding superseded standard ${citedStandard}`}
        >
          See why →
        </button>
      </div>

      <div className="update-card__body">
        <div className="update-card__replacement">
          <span className="update-card__label">Recommended current reference:</span>
          <span className="update-card__successor">{currentReference}</span>
          {req.title && <span className="update-card__successor-title">{req.title}</span>}
        </div>
      </div>
    </article>
  );
}

export interface RelatedCardProps {
  related: RelatedStandard;
  parentStandard: string;
  parentReq: Requirement;
  onOpenEvidence: (req: Requirement) => void;
}

export function RelatedCard({ related, parentStandard, parentReq, onOpenEvidence }: RelatedCardProps) {
  const relationshipLabel =
    related.relationship_type === 'REFERENCES'
      ? `Normative reference from ${parentStandard}`
      : related.relationship_type === 'SUPERSEDES'
      ? `Superseded standard referenced from ${parentStandard}`
      : related.relationship_type === 'CODE_OF_PRACTICE_FOR'
      ? `Code of practice for ${parentStandard}`
      : `Reference from ${parentStandard}`;

  return (
    <article className="related-card" aria-label={`Related standard ${related.standard_number}`}>
      <div className="related-card__header">
        <div className="related-card__left">
          <span className="related-card__icon" aria-hidden="true">○</span>
          <div>
            <h4 className="related-card__std">{related.standard_number}</h4>
            <p className="related-card__note">{relationshipLabel}</p>
            {related.title && <p className="related-card__title">{related.title}</p>}
          </div>
        </div>

        <button
          type="button"
          className="related-card__see-why"
          onClick={() => onOpenEvidence(parentReq)}
          aria-label={`See details for ${related.standard_number}`}
        >
          See why →
        </button>
      </div>

      <p className="related-card__guidance">Review for co-application.</p>
    </article>
  );
}

// Default export wrapper for compatibility
export default function RequirementCard(props: any) {
  if (props.variant === 'recommendation' || props.sectionType === 'good') {
    return <RecommendationCard req={props.req} isPrimary={props.isPrimary} onOpenEvidence={props.onOpenEvidence} />;
  }
  if (props.variant === 'attention' || props.sectionType === 'attention') {
    return <AttentionCard req={props.req} onOpenEvidence={props.onOpenEvidence} />;
  }
  if (props.variant === 'update' || props.sectionType === 'update') {
    return <UpdateCard req={props.req} onOpenEvidence={props.onOpenEvidence} />;
  }
  return <RecommendationCard req={props.req} isPrimary={props.isPrimary} onOpenEvidence={props.onOpenEvidence} />;
}
