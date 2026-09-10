// RequirementCard.tsx — Expandable requirement card matching Reference Image 2
import { useState } from 'react';
import './RequirementCard.css';
import type { Requirement } from '../types';

interface RequirementCardProps {
  req: Requirement;
  index: number;
  sectionType: 'attention' | 'good' | 'update';
  onOpenEvidence: (req: Requirement) => void;
  defaultExpanded?: boolean;
}

export default function RequirementCard({
  req,
  index,
  sectionType,
  onOpenEvidence,
  defaultExpanded = false,
}: RequirementCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  // Extract a clean title from requirement text
  const displayTitle = req.text.length > 55 ? `${req.text.slice(0, 52)}...` : req.text;

  // Format standard name
  const standardCode = req.candidate_standard && req.candidate_standard !== 'NONE'
    ? req.candidate_standard
    : null;

  return (
    <div className={`req-item ${expanded ? 'req-item--expanded' : ''}`}>
      {/* Collapsed Header Bar */}
      <div
        className="req-item__summary"
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
        <div className="req-item__left">
          <div className="req-item__index-title">
            <span className="req-item__number">{index}.</span>
            <span className="req-item__title">{displayTitle}</span>
          </div>

          {/* Subtitle / Why flagged / Missing params */}
          <div className="req-item__desc">
            {sectionType === 'update' ? (
              <span className="req-item__desc-update">
                Cited standard is superseded.
                {req.successor_standard && (
                  <> Current active successor: <strong>{req.successor_standard}</strong></>
                )}
              </span>
            ) : sectionType === 'attention' ? (
              <span>{req.why_flagged || 'Missing required specifications or testing parameters.'}</span>
            ) : (
              <span>{req.title || 'Verified match with active Indian Standard.'}</span>
            )}
          </div>

          {/* Standard line */}
          <div className="req-item__std-line">
            <span className="req-item__std-icon" aria-hidden="true">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
              </svg>
            </span>
            <span className="req-item__std-label">
              {sectionType === 'update' ? 'Superseded standard' : 'Possible standard'}
            </span>
            <span className="req-item__std-num">
              {sectionType === 'update' && req.superseded_citation
                ? req.superseded_citation
                : standardCode || 'None Identified'}
            </span>

            {sectionType === 'update' && (
              <span className="badge badge--superseded">SUPERSEDED</span>
            )}

            {sectionType === 'good' && (
              <span className="badge badge--strong">{req.evidence_strength} EVIDENCE</span>
            )}
          </div>
        </div>

        {/* Right action: "See why →" */}
        <div className="req-item__right">
          <button
            type="button"
            className="req-item__see-why"
            onClick={(e) => {
              e.stopPropagation();
              onOpenEvidence(req);
            }}
            aria-label={`See evidence why ${standardCode || 'standard'} was suggested`}
          >
            See why →
          </button>
        </div>
      </div>

      {/* Expanded In-Place Content */}
      {expanded && (
        <div className="req-item__details">
          {/* Full requirement clause */}
          <div className="req-detail-block">
            <span className="req-detail-label">Full Requirement Clause</span>
            <p className="req-detail-text">{req.text}</p>
          </div>

          {/* Why flagged / Missing parameters */}
          {sectionType === 'attention' && (
            <div className="req-detail-block">
              <span className="req-detail-label">Why This Was Flagged</span>
              <p className="req-detail-text">
                {req.why_flagged || 'Clarification or technical parameters are missing.'}
              </p>

              {req.missing_parameters && req.missing_parameters.length > 0 && (
                <div className="req-missing-params">
                  <span className="req-missing-title">Missing Engineering Parameters:</span>
                  <ul className="req-missing-list">
                    {req.missing_parameters.map((p, i) => (
                      <li key={i}>{p}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Update notice for superseded standards */}
          {sectionType === 'update' && (
            <div className="req-detail-block req-detail-block--warning">
              <span className="req-detail-label">Supersedence Warning</span>
              <p className="req-detail-text">
                The cited standard <strong>{req.superseded_citation || req.candidate_standard}</strong> is outdated
                or superseded.
                {req.successor_standard && (
                  <> Tender specifications should cite current active standard <strong>{req.successor_standard}</strong>.</>
                )}
              </p>
            </div>
          )}

          {/* Recommended Standard details */}
          {standardCode && (
            <div className="req-detail-block">
              <span className="req-detail-label">
                {sectionType === 'update' ? 'Current Active Successor Standard' : 'Recommended Indian Standard'}
              </span>
              <div className="req-std-box">
                <span className="req-std-box__num">{req.successor_standard || standardCode}</span>
                {req.title && <span className="req-std-box__title">{req.title}</span>}
              </div>
            </div>
          )}

          {/* Grounded Evidence excerpt */}
          {req.evidence && (
            <div className="req-detail-block">
              <span className="req-detail-label">Evidence Excerpt</span>
              <blockquote className="req-evidence-quote">
                "{req.evidence}"
              </blockquote>
            </div>
          )}

          {/* Risk & Review Status */}
          <div className="req-detail-row">
            <div>
              <span className="req-detail-label">Risk Level</span>
              <span className={`badge badge--${(req.risk_level || 'low').toLowerCase()}`}>
                {req.risk_level} RISK
              </span>
            </div>

            <div>
              <span className="req-detail-label">Audit Decision</span>
              <span className="badge badge--review">{req.decision}</span>
            </div>

            {req.human_review_required && (
              <div>
                <span className="req-detail-label">Human Action</span>
                <span className="badge badge--human">⚠ HUMAN REVIEW REQUIRED</span>
              </div>
            )}
          </div>

          {/* Deep Drawer Trigger */}
          <div className="req-detail-footer">
            <button
              type="button"
              className="btn-view-evidence"
              onClick={() => onOpenEvidence(req)}
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="16" x2="12" y2="12" />
                <line x1="12" y1="8" x2="12.01" y2="8" />
              </svg>
              View full evidence drawer & technical details →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
