// RequirementCard.tsx — Card component for displaying a single requirement
// Progressively reveals deeper details, with button to open the full EvidenceDrawer
import { useState } from 'react';
import './RequirementCard.css';
import type { Requirement } from '../types';

interface RequirementCardProps {
  req: Requirement;
  sectionType: 'attention' | 'good' | 'update';
  onOpenEvidence: (req: Requirement) => void;
  defaultExpanded?: boolean;
}

export default function RequirementCard({
  req,
  sectionType,
  onOpenEvidence,
  defaultExpanded = false,
}: RequirementCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  const statusClass =
    sectionType === 'attention'
      ? 'req-card--attention'
      : sectionType === 'update'
      ? 'req-card--update'
      : 'req-card--good';

  const riskClass =
    req.risk_level === 'CRITICAL' || req.risk_level === 'HIGH'
      ? 'badge--red'
      : req.risk_level === 'MEDIUM'
      ? 'badge--amber'
      : 'badge--green';

  return (
    <div className={`req-card ${statusClass}`}>
      {/* Header — Click to expand / collapse */}
      <div
        className="req-card__head"
        onClick={() => setExpanded((prev) => !prev)}
        role="button"
        tabIndex={0}
        aria-expanded={expanded}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setExpanded((prev) => !prev);
          }
        }}
      >
        <div className="req-card__head-main">
          <div className="req-card__title">{req.text}</div>

          <div className="req-card__subtitle">
            {sectionType === 'update' && req.successor_standard ? (
              <span>
                Cites superseded standard — update to{' '}
                <strong>{req.successor_standard}</strong>
              </span>
            ) : sectionType === 'attention' ? (
              <span>{req.why_flagged || 'Review required before publication.'}</span>
            ) : (
              <span>{req.title || 'Verified match with active national standard.'}</span>
            )}
          </div>

          <div className="req-card__std">
            <span>Matched:</span>
            <span className="req-card__std-num">{req.candidate_standard}</span>
            <span>•</span>
            <span
              className={`badge ${
                req.lifecycle_status === 'SUPERSEDED' || req.lifecycle_status === 'WITHDRAWN'
                  ? 'badge--red'
                  : 'badge--green'
              }`}
            >
              {req.lifecycle_status || 'ACTIVE'}
            </span>
            <span className={`badge ${riskClass}`}>{req.risk_level} RISK</span>
          </div>
        </div>

        <svg
          className={`req-card__chevron ${expanded ? 'req-card__chevron--open' : ''}`}
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </div>

      {/* Expanded body with progressive details */}
      {expanded && (
        <div className="req-card__body">
          {/* Successor Standard Banner if superseded */}
          {req.successor_standard && (
            <div className="req-card__successor">
              <div>
                <div className="req-card__successor-label">Action Required — Replace With</div>
                <div className="req-card__successor-std">{req.successor_standard}</div>
              </div>
            </div>
          )}

          {/* Standard Title & Category */}
          <div className="req-card__field">
            <span className="req-card__field-label">Standard Title</span>
            <span className="req-card__field-value">{req.title || 'N/A'}</span>
          </div>

          {/* Decision / Review Reason */}
          {req.why_flagged && (
            <div className="req-card__field">
              <span className="req-card__field-label">Review Guidance</span>
              <span className="req-card__field-value">{req.why_flagged}</span>
            </div>
          )}

          {/* Missing Parameters */}
          {req.missing_parameters && req.missing_parameters.length > 0 && (
            <div className="req-card__field">
              <span className="req-card__field-label">Missing Parameters for Compliance</span>
              <ul className="req-card__missing">
                {req.missing_parameters.map((param, idx) => (
                  <li key={idx}>{param}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Evidence Snippet */}
          {req.evidence && (
            <div className="req-card__field">
              <span className="req-card__field-label">Evidence Grounding</span>
              <span className="req-card__field-value text-muted" style={{ fontStyle: 'italic' }}>
                "{req.evidence}"
              </span>
            </div>
          )}

          {/* Actions */}
          <div className="req-card__actions">
            <button
              className="btn btn--secondary btn--sm"
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onOpenEvidence(req);
              }}
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="16" x2="12" y2="12" />
                <line x1="12" y1="8" x2="12.01" y2="8" />
              </svg>
              View Full Evidence & AI Breakdown
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
