// EvidenceDrawer.tsx — Right-side evidence panel (not a separate page)
// Evidence first, then AI understanding, then technical scores (all progressive disclosure)
import { useState } from 'react';
import './EvidenceDrawer.css';
import type { Requirement } from '../types';

interface EvidenceDrawerProps {
  req: Requirement;
  onClose: () => void;
}

function CollapseSection({ title, children, defaultOpen = false }: {
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
        {title}
        <svg
          className={`drawer-collapsible__arrow${open ? ' drawer-collapsible__arrow--open' : ''}`}
          width="14" height="14" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
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
    <span className={`badge badge--${s === 'strong' ? 'strong' : s === 'moderate' ? 'moderate' : s === 'weak' ? 'weak' : 'none'}`}>
      {strength || 'NONE'}
    </span>
  );
}

function ScoreBar({ label, value, max = 1 }: { label: string; value: number | null; max?: number }) {
  if (value === null || value === undefined) return null;
  const pct = Math.min(100, Math.round((value / max) * 100));
  return (
    <div className="score-row">
      <span className="score-row__label">{label}</span>
      <div className="score-bar-wrap">
        <div className="score-bar" style={{ width: `${pct}%` }} />
      </div>
      <span className="score-row__val">{value.toFixed(3)}</span>
    </div>
  );
}

export default function EvidenceDrawer({ req, onClose }: EvidenceDrawerProps) {
  const ai = req.ai_understanding || { facets: {}, provider: 'unknown', model: 'unknown', is_fallback: true };
  const hasFacets = Object.keys(ai.facets || {}).filter((k) => ai.facets[k]).length > 0;
  const isAiFallback = ai.is_fallback;

  const lifecycleClass = (req.lifecycle_status || '').toLowerCase() === 'superseded'
    ? 'badge--superseded'
    : (req.lifecycle_status || '').toLowerCase() === 'active'
    ? 'badge--active'
    : 'badge--low';

  return (
    <>
      {/* Overlay */}
      <div
        className="drawer-overlay"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer panel */}
      <aside
        className="drawer"
        role="complementary"
        aria-label="Evidence details"
      >
        <div className="drawer__head">
          <span className="drawer__title">Why this standard?</span>
          <button className="drawer__close" onClick={onClose} aria-label="Close evidence panel" type="button">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div className="drawer__body">
          {/* 1. Requirement */}
          <div className="drawer-section">
            <div className="drawer-section__label">Requirement</div>
            <div className="drawer-section__value">{req.text}</div>
          </div>

          {/* 2. Standard */}
          {req.candidate_standard && req.candidate_standard !== 'NONE' && (
            <div className="drawer-section">
              <div className="drawer-section__label">Candidate Standard</div>
              <div className="drawer-section__value drawer-section__value--standard">{req.candidate_standard}</div>
              {req.title && <div className="drawer-section__value drawer-section__value--muted" style={{ marginTop: 4 }}>{req.title}</div>}
            </div>
          )}

          {/* 3. Evidence */}
          {req.evidence && (
            <div className="drawer-section">
              <div className="drawer-section__label">Evidence</div>
              <div className="drawer-section__value">{req.evidence}</div>
            </div>
          )}

          {/* 4. Evidence Strength + Provenance */}
          <div className="drawer-section" style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
            <div>
              <div className="drawer-section__label">Evidence Strength</div>
              <EvBadge strength={req.evidence_strength} />
            </div>
            <div>
              <div className="drawer-section__label">Provenance</div>
              <span className="badge badge--low">{req.provenance}</span>
            </div>
          </div>

          {/* 5. Lifecycle */}
          <div className="drawer-section" style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
            <div>
              <div className="drawer-section__label">Lifecycle Status</div>
              <span className={`badge ${lifecycleClass}`}>{req.lifecycle_status || 'Unknown'}</span>
            </div>
            {req.successor_standard && (
              <div>
                <div className="drawer-section__label">Current Successor</div>
                <span style={{ fontSize: '0.9rem', fontWeight: 700 }}>{req.successor_standard}</span>
              </div>
            )}
          </div>

          {/* 6. Related Standards */}
          {req.related_standards?.length > 0 && (
            <div className="drawer-section">
              <div className="drawer-section__label">Related Standards (Graph)</div>
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

          {/* 7. Completeness */}
          {req.missing_parameters?.length > 0 && (
            <div className="drawer-section">
              <div className="drawer-section__label">Potentially Missing Parameters</div>
              <ul style={{ paddingLeft: 18, fontSize: '0.87rem', color: 'var(--color-navy)', lineHeight: 1.7 }}>
                {req.missing_parameters.map((p, i) => <li key={i}>{p}</li>)}
              </ul>
            </div>
          )}

          {/* 8. Risk & Decision */}
          <div className="drawer-section" style={{ display: 'flex', gap: 24, flexWrap: 'wrap', alignItems: 'flex-start' }}>
            <div>
              <div className="drawer-section__label">Risk</div>
              <span className={`badge badge--${(req.risk_level || 'low').toLowerCase()}`}>{req.risk_level}</span>
            </div>
            <div>
              <div className="drawer-section__label">Decision</div>
              <span className="badge badge--review">{req.decision}</span>
            </div>
            {req.human_review_required && (
              <div>
                <span className="badge badge--human">⚠ Human Review Required</span>
              </div>
            )}
          </div>

          {/* 9. Why this (collapsible) */}
          {req.why_this?.length > 0 && (
            <CollapseSection title="Why This Candidate">
              <ul style={{ paddingLeft: 18, fontSize: '0.87rem', color: 'var(--color-navy)', lineHeight: 1.7 }}>
                {req.why_this.map((w, i) => <li key={i}>{w}</li>)}
              </ul>
            </CollapseSection>
          )}

          {/* 10. AI Understanding (collapsed by default) */}
          <CollapseSection title="How TenderSaathi understood this requirement" defaultOpen={false}>
            {hasFacets ? (
              <div className="drawer-ai-facets">
                {Object.entries(ai.facets).filter(([, v]) => v).map(([k, v]) => (
                  <div key={k} className="drawer-ai-facet">
                    <div className="drawer-ai-facet__key">{k.replace(/_/g, ' ')}</div>
                    <div className="drawer-ai-facet__val">{Array.isArray(v) ? v.join(', ') : String(v)}</div>
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>No structured facets available.</p>
            )}
            <div className="drawer-ai-attr">
              {isAiFallback
                ? 'Understood using: Deterministic fallback'
                : `Understood by: ${ai.provider} · ${ai.model}`}
            </div>
            <p className="drawer-ai-trust">
              AI helps understand the requirement. It does not decide which Indian Standard applies.
            </p>
          </CollapseSection>

          {/* 11. Technical Scores (collapsed by default) */}
          <CollapseSection title="Technical Score Breakdown" defaultOpen={false}>
            <div style={{ marginTop: 8 }}>
              <ScoreBar label="BM25" value={req.scores?.bm25} />
              <ScoreBar label="Semantic" value={req.scores?.semantic} />
              <ScoreBar label="Deterministic" value={req.scores?.deterministic} />
              {req.scores?.reranker !== null && (
                <ScoreBar label="Reranker" value={req.scores?.reranker} />
              )}
              <ScoreBar label="Final" value={req.scores?.final} />
            </div>
            <p style={{ marginTop: 12, fontSize: '0.73rem', color: 'var(--color-text-faint)', lineHeight: 1.5 }}>
              BM25 + semantic + deterministic retrieval scores combined with cross-encoder reranking.
              Relevance score = 1 / (1 + exp(-logit)).
            </p>
          </CollapseSection>
        </div>
      </aside>
    </>
  );
}
