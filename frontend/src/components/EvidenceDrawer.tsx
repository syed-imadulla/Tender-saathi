// EvidenceDrawer.tsx — Right-side evidence panel with progressive disclosure
import { useState } from 'react';
import './EvidenceDrawer.css';
import type { Requirement } from '../types';

interface EvidenceDrawerProps {
  req: Requirement;
  onClose: () => void;
}

function CollapseSection({
  title,
  children,
  defaultOpen = false,
}: {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="drawer-collapsible">
      <button
        className="drawer-collapsible__toggle"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        type="button"
      >
        <span>{title}</span>
        <svg
          className={`drawer-collapsible__arrow${open ? ' drawer-collapsible__arrow--open' : ''}`}
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>
      {open && <div className="drawer-collapsible__body">{children}</div>}
    </div>
  );
}

function EvBadge({ strength }: { strength: string }) {
  const s = (strength || '').toLowerCase();
  return (
    <span
      className={`badge badge--${
        s === 'strong' ? 'strong' : s === 'moderate' ? 'moderate' : s === 'weak' ? 'weak' : 'none'
      }`}
    >
      {strength || 'NONE'}
    </span>
  );
}

function ScoreBar({
  label,
  value,
  max = 1,
}: {
  label: string;
  value: number | string | null | undefined;
  max?: number;
}) {
  if (value === null || value === undefined) return null;
  const isNumber = typeof value === 'number';
  const pct = isNumber ? Math.min(100, Math.max(0, Math.round((value as number / max) * 100))) : 0;
  return (
    <div className="score-row">
      <span className="score-row__label">{label}</span>
      <div className="score-bar-wrap">
        <div className="score-bar" style={{ width: `${pct}%`, opacity: isNumber ? 1 : 0.2 }} />
      </div>
      <span className="score-row__val">
        {isNumber ? (value as number).toFixed(3) : value}
      </span>
    </div>
  );
}

const FACET_KEYS = [
  { key: 'equipment', label: 'Equipment' },
  { key: 'control', label: 'Control' },
  { key: 'electrical', label: 'Electrical' },
  { key: 'voltage', label: 'Voltage' },
  { key: 'application', label: 'Application' },
  { key: 'work_type', label: 'Work type' },
];

export default function EvidenceDrawer({ req, onClose }: EvidenceDrawerProps) {
  const ai = req.ai_understanding || {
    facets: {},
    provider: 'unknown',
    model: 'unknown',
    is_fallback: true,
  };

  const isAiFallback = ai.is_fallback;
  const lifecycle = (req.lifecycle_status || '').toLowerCase();
  const lifecycleClass =
    lifecycle === 'superseded'
      ? 'badge--superseded'
      : lifecycle === 'active'
      ? 'badge--active'
      : 'badge--low';

  return (
    <>
      {/* Overlay Backdrop */}
      <div
        className="drawer-overlay"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer Panel */}
      <aside
        className="drawer"
        role="dialog"
        aria-label="Evidence and technical details"
      >
        <div className="drawer__head">
          <h2 className="drawer__title">
            {req.candidate_standard === 'INSUFFICIENT_INFORMATION' 
              ? 'Why no standard was recommended?' 
              : 'Why this standard?'}
          </h2>
          <button
            className="drawer__close"
            onClick={onClose}
            aria-label="Close evidence drawer"
            type="button"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div className="drawer__body">
          {/* 1. Requirement */}
          <div className="drawer-section">
            <span className="drawer-section__label">1. Requirement</span>
            <div className="drawer-section__value">{req.text}</div>
          </div>

          {/* 2. Standard */}
          {req.candidate_standard && req.candidate_standard !== 'NONE' && (
            <div className="drawer-section">
              <span className="drawer-section__label">2. Indian Standard</span>
              <div className="drawer-section__value drawer-section__value--standard">
                {req.candidate_standard}
              </div>
              {req.title && (
                <div className="drawer-section__value drawer-section__value--muted">
                  {req.title}
                </div>
              )}
            </div>
          )}

          {/* 3. Why this was suggested */}
          {(req.why_this?.length > 0 || req.why_flagged) && (
            <div className="drawer-section">
              <span className="drawer-section__label">3. Why This Was Suggested</span>
              {req.why_this?.length > 0 ? (
                <ul className="drawer-bullet-list">
                  {req.why_this.map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              ) : (
                <div className="drawer-section__value">{req.why_flagged}</div>
              )}
            </div>
          )}

          {/* 4. Evidence */}
          {req.evidence && (
            <div className="drawer-section">
              <span className="drawer-section__label">4. Evidence</span>
              <blockquote className="drawer-evidence-quote">
                "{req.evidence}"
              </blockquote>
            </div>
          )}

          {/* 5 & 6. Evidence Strength + Provenance */}
          <div className="drawer-section drawer-section--row">
            <div>
              <span className="drawer-section__label">5. Evidence Strength</span>
              <EvBadge strength={req.evidence_strength} />
            </div>
            <div>
              <span className="drawer-section__label">6. Provenance</span>
              <span className="badge badge--low">{req.provenance}</span>
            </div>
          </div>

          {/* 7. Lifecycle */}
          <div className="drawer-section drawer-section--row">
            <div>
              <span className="drawer-section__label">7. Lifecycle Status</span>
              <span className={`badge ${lifecycleClass}`}>
                {req.lifecycle_status || 'Unknown'}
              </span>
            </div>
            {req.successor_standard && (
              <div>
                <span className="drawer-section__label">Current Successor</span>
                <span className="drawer-successor-num">{req.successor_standard}</span>
              </div>
            )}
          </div>

          {/* 8. Related Standards (Graph) */}
          {req.related_standards?.length > 0 && (
            <div className="drawer-section">
              <span className="drawer-section__label">8. Related Standards (Graph)</span>
              <div className="drawer-related">
                {req.related_standards.slice(0, 5).map((rel, i) => (
                  <div key={i} className="drawer-related-item">
                    <div className="drawer-related-item__std">{rel.standard_number}</div>
                    <div className="drawer-related-item__rel">
                      {rel.relationship_type} · {rel.lifecycle_status || 'Active'}
                      {rel.review_note ? ` — ${rel.review_note}` : ''}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 9. Missing Parameters / Completeness */}
          {req.missing_parameters?.length > 0 && (
            <div className="drawer-section">
              <span className="drawer-section__label">9. Missing Parameters / Completeness</span>
              <ul className="drawer-bullet-list">
                {req.missing_parameters.map((p, i) => (
                  <li key={i}>{p}</li>
                ))}
              </ul>
            </div>
          )}

          {/* 10. Risk & Decision */}
          <div className="drawer-section drawer-section--row">
            <div>
              <span className="drawer-section__label">10. Risk Level</span>
              <span className={`badge badge--${(req.risk_level || 'low').toLowerCase()}`}>
                {req.risk_level} RISK
              </span>
            </div>
            <div>
              <span className="drawer-section__label">Audit Decision</span>
              <span className="badge badge--review">{req.decision}</span>
            </div>
            {req.human_review_required && (
              <div>
                <span className="drawer-section__label">Review Flag</span>
                <span className="badge badge--human">⚠ HUMAN REVIEW REQUIRED</span>
              </div>
            )}
          </div>

          {/* COLLAPSED SECTION 1: How TenderSaathi understood this requirement */}
          <CollapseSection title="How TenderSaathi understood this requirement" defaultOpen={false}>
            <div className="drawer-ai-facets">
              {FACET_KEYS.map(({ key, label }) => {
                const val = ai.facets ? ai.facets[key] : null;
                const displayVal = Array.isArray(val) ? val.join(', ') : val ? String(val) : '—';
                return (
                  <div key={key} className="drawer-ai-facet">
                    <div className="drawer-ai-facet__key">{label}</div>
                    <div className="drawer-ai-facet__val">{displayVal}</div>
                  </div>
                );
              })}
            </div>

            <div className="drawer-ai-attr">
              {isAiFallback ? (
                <span>Understood using: <strong>Deterministic fallback</strong></span>
              ) : (
                <span>
                  Understood by: <strong>Groq · {ai.model || 'openai/gpt-oss-120b'}</strong>
                </span>
              )}
            </div>

            <p className="drawer-ai-trust">
              "AI helps understand the requirement. It does not decide which Indian Standard applies."
            </p>
          </CollapseSection>

          {/* COLLAPSED SECTION 2: Technical score details */}
          <CollapseSection title="Technical score details" defaultOpen={false}>
            <div className="score-breakdown-list">
              <ScoreBar label="BM25" value={req.scores?.deterministic === 1.0 ? 'Not used' : req.scores?.bm25} />
              <ScoreBar label="Semantic" value={req.scores?.deterministic === 1.0 ? 'Not used' : req.scores?.semantic} />
              <ScoreBar label="Deterministic" value={req.scores?.deterministic} />
              {req.scores?.reranker !== null && req.scores?.reranker !== undefined && (
                <ScoreBar label="Reranker" value={req.scores?.deterministic === 1.0 ? 'Not used' : req.scores?.reranker} />
              )}
              <ScoreBar label="Final" value={req.scores?.final} />
            </div>

            <p className="score-formula-note">
              Relevance score σ(logit) = 1 / (1 + exp(-logit)). Combines BM25 lexical keyword matching,
              bge/MiniLM embeddings, deterministic catalogue lookups, and cross-encoder reranking.
            </p>
          </CollapseSection>
        </div>
      </aside>
    </>
  );
}
