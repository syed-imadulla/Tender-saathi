// RequirementCard.tsx — Specialized cards for the TenderSaathi Recommendation UI
import './RequirementCard.css';
import type { Requirement, RelatedStandard } from '../types';

export function getWhyItMatches(req: Requirement): string {
  if (req.candidate_standard === 'INSUFFICIENT_INFORMATION' || req.candidate_standard === 'NONE') {
    return 'No reliable standard match found in the available catalogue.';
  }

  // Check explicit citation in requirement text
  const stdClean = req.candidate_standard.replace(/[^0-9]/g, '');
  const textHasExplicitCitation = stdClean && req.text.replace(/[^0-9]/g, '').includes(stdClean);

  if (textHasExplicitCitation && req.candidate_standard.includes('15778')) {
    return 'The tender explicitly cites IS 15778 and the standard covers CPVC pipes for potable hot and cold water supplies.';
  }

  // If IS 778 valve requirement
  if (req.candidate_standard.includes('778')) {
    return 'The standard directly covers gate, globe and check valves for waterworks purposes.';
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
        .trim();

      if (cleaned.length > 10) {
        if (cleaned.startsWith('Tender explicitly') && req.evidence && req.evidence.toLowerCase() !== 'none') {
          return req.evidence.replace(/^(Exact Match:\s*|Direct Match:\s*)/i, '').trim();
        }
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
    return `Covers ${req.title.toLowerCase()} for procurement specifications.`;
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

      <div className="rec-card__why-block">
        <span className="rec-card__why-label">Why it matches:</span>
        <p className="rec-card__why-text">{whyMatches}</p>
      </div>
    </article>
  );
}

export interface AttentionCardProps {
  req: Requirement;
  onOpenEvidence: (req: Requirement) => void;
}

export function AttentionCard({ req, onOpenEvidence }: AttentionCardProps) {
  const hasMissing = req.missing_parameters && req.missing_parameters.length > 0;
  const isInsufficient = req.decision === 'INSUFFICIENT_EVIDENCE' || req.candidate_standard === 'INSUFFICIENT_INFORMATION';

  return (
    <article className="attention-card" aria-label="Requirement needing attention">
      <div className="attention-card__header">
        <div className="attention-card__left">
          <span className="attention-card__icon" aria-hidden="true">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
          </span>
          <div>
            <h4 className="attention-card__title">
              {hasMissing
                ? 'Some specification details need clarification'
                : isInsufficient
                ? 'Human review required — insufficient evidence'
                : 'Specification details need clarification'}
            </h4>
            <p className="attention-card__clause">
              "{req.text.length > 120 ? `${req.text.slice(0, 117)}...` : req.text}"
            </p>
          </div>
        </div>

        <button
          type="button"
          className="attention-card__see-why"
          onClick={() => onOpenEvidence(req)}
          aria-label="See why attention is required"
        >
          See why →
        </button>
      </div>

      {hasMissing ? (
        <div className="attention-card__body">
          <p className="attention-card__prompt">Your tender does not specify:</p>
          <ul className="attention-card__list">
            {req.missing_parameters.map((param, i) => (
              <li key={i} className="attention-card__param-item">
                <span className="attention-card__bullet">•</span>
                <span>{param}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : isInsufficient ? (
        <div className="attention-card__body">
          <p className="attention-card__desc">
            We could not establish a sufficiently supported Indian Standard from the available catalogue for this requirement. Manual engineer review is recommended before publishing.
          </p>
        </div>
      ) : (
        <div className="attention-card__body">
          <p className="attention-card__desc">
            Additional technical specifications or application parameters are recommended to confirm standard applicability.
          </p>
        </div>
      )}
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
