// EvidenceDrawer.tsx — Evidence and audit trail panel with progressive disclosure
import { useState } from 'react';
import './EvidenceDrawer.css';
import type { Requirement } from '../types';
import { areStandardsEquivalent } from './RequirementCard';

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

function getProvenanceDetails(provenance?: string): { label: string; description: string; badgeClass: string } {
  const p = (provenance || '').toUpperCase();
  switch (p) {
    case 'OFFICIAL_PRIMARY':
      return {
        label: 'Verified Official Primary Source',
        description: 'Gazette notification, Ministry QCO order, or statutory BIS core registry.',
        badgeClass: 'badge--active',
      };
    case 'OFFICIAL_SECONDARY':
      return {
        label: 'Official Secondary Source',
        description: 'Ministry or departmental procurement catalogue / public sector schedule.',
        badgeClass: 'badge--active',
      };
    case 'VERIFIED':
      return {
        label: 'Verified Official Source',
        description: 'Cross-verified active record in Bureau of Indian Standards catalogue.',
        badgeClass: 'badge--active',
      };
    case 'CURATED':
      return {
        label: 'Curated Technical Source',
        description: 'Expert-compiled engineering standard repository verified against domain specifications.',
        badgeClass: 'badge--low',
      };
    case 'INFERRED':
      return {
        label: 'Inferred / Derived',
        description: 'Heuristic specification mapping requiring human technical review.',
        badgeClass: 'badge--review',
      };
    default:
      return {
        label: p || 'Unverified Source',
        description: 'Source metadata awaiting formal verification.',
        badgeClass: 'badge--low',
      };
  }
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
  const pct = isNumber ? Math.min(100, Math.max(0, Math.round(((value as number) / max) * 100))) : 0;
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

  const isNoMatch = !req.candidate_standard || req.candidate_standard === 'INSUFFICIENT_INFORMATION' || req.candidate_standard === 'NONE' || req.decision === 'NO_RELIABLE_MATCH';
  const prov = getProvenanceDetails(req.provenance);

  return (
    <>
      {/* Overlay Backdrop */}
      <div className="drawer-overlay" onClick={onClose} aria-hidden="true" />

      {/* Drawer Panel */}
      <aside className="drawer" role="dialog" aria-label="Evidence and technical details">
        <div className="drawer__head">
          <div>
            <span className="drawer__eyebrow">AUDIT & EVIDENCE</span>
            <h2 className="drawer__title">
              {isNoMatch ? 'Why no standard was recommended?' : 'Why this standard?'}
            </h2>
          </div>
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
          <section className="drawer-section">
            <span className="drawer-section__label">1. Requirement</span>
            <div className="drawer-section__value drawer-section__value--req">
              <div>
                <strong>Tender Text:</strong> {req.multilingual?.original_text || req.text}
              </div>
              {req.multilingual?.is_multilingual && (
                <div style={{ marginTop: '0.5rem', padding: '0.5rem 0.75rem', background: '#f8fafc', borderRadius: '4px', borderLeft: '3px solid #3b82f6' }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#475569', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
                    System interpretation ({req.multilingual.detected_language === 'hi' ? 'Hindi → English' : req.multilingual.detected_language === 'kn' ? 'Kannada → English' : req.multilingual.detected_language === 'ta' ? 'Tamil → English' : 'Mixed → English'}):
                  </div>
                  <div style={{ color: '#1e293b', fontStyle: 'italic' }}>
                    "{req.multilingual.canonical_text}"
                  </div>
                </div>
              )}
            </div>
          </section>


          {/* 2. Indian Standard */}
          {/* 2. Indian Standard */}
          <section className="drawer-section">
            <span className="drawer-section__label">2. Indian Standard & Grounding Integrity</span>
            {isNoMatch ? (
              <div className="drawer-section__value drawer-section__value--nomatch">
                <div style={{ fontWeight: 700, color: '#475569', marginBottom: '4px' }}>
                  No reliable standard match found in catalogue
                </div>
                <div style={{ fontSize: '0.8rem', color: '#64748b' }}>
                  Candidate Standard: <span style={{ fontFamily: 'monospace' }}>None (Abstained)</span> · Evidence Standard: <span style={{ fontFamily: 'monospace' }}>None</span>
                </div>
              </div>
            ) : (
              <div className="drawer-std-block">
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px', marginBottom: '4px' }}>
                  <div className="drawer-section__value drawer-section__value--standard">
                    {req.candidate_standard}
                  </div>
                  {req.candidate_standard && req.evidence_standard && areStandardsEquivalent(req.candidate_standard, req.evidence_standard) ? (
                    <span className="badge badge--active" style={{ fontSize: '0.72rem' }}>
                      ✓ Grounding Established (Candidate == Evidence)
                    </span>
                  ) : req.candidate_standard && req.evidence_standard ? (
                    <span className="badge badge--superseded" style={{ fontSize: '0.72rem' }}>
                      ⚠ Evidence Review (Candidate ≠ Evidence)
                    </span>
                  ) : null}
                </div>
                <div style={{ fontSize: '0.8rem', color: '#475569', marginBottom: '4px' }}>
                  <strong>Grounded Evidence Standard:</strong>{' '}
                  <span style={{ fontFamily: 'monospace', fontWeight: 600, color: '#0f172a' }}>
                    {req.evidence_standard || req.candidate_standard}
                  </span>
                </div>
                {req.title && (
                  <div className="drawer-section__value drawer-section__value--title">
                    {req.title}
                  </div>
                )}
              </div>
            )}
          </section>

          {/* 3. Why It Matches / Why Rejected */}
          <section className="drawer-section">
            <span className="drawer-section__label">
              {isNoMatch ? '3. Why No Standard Was Recommended' : '3. Why It Matches'}
            </span>
            {isNoMatch ? (
              req.why_not && req.why_not.length > 0 ? (
                <ul className="drawer-bullet-list drawer-bullet-list--missing">
                  {req.why_not.map((reason, i) => (
                    <li key={i}>{reason}</li>
                  ))}
                </ul>
              ) : (
                <div className="drawer-section__value">
                  We could not establish a sufficiently supported Indian Standard from the available catalogue.
                </div>
              )
            ) : req.why_this && req.why_this.length > 0 ? (
              <ul className="drawer-bullet-list">
                {req.why_this.map((reason, i) => (
                  <li key={i}>{reason}</li>
                ))}
              </ul>
            ) : req.why_flagged ? (
              <div className="drawer-section__value">{req.why_flagged}</div>
            ) : (
              <div className="drawer-section__value">Verified match against active BIS catalogue standards.</div>
            )}
          </section>

          {/* 4. Evidence */}
          {req.evidence && (
            <section className="drawer-section">
              <span className="drawer-section__label">
                {req.evidence_strength === 'STRONG' && (req.provenance === 'VERIFIED' || req.provenance === 'OFFICIAL_PRIMARY')
                  ? '4. Authoritative Evidence Quote'
                  : '4. Supporting Evidence Quote'}
              </span>
              <blockquote className="drawer-evidence-quote">
                "{req.evidence_standard && !areStandardsEquivalent(req.candidate_standard, req.evidence_standard)
                  ? 'Match identified from the requirement context; supporting evidence needs review.'
                  : req.evidence}"
              </blockquote>
            </section>
          )}

          {/* 5. Source / Provenance */}
          <section className="drawer-section">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span className="drawer-section__label">5. Record Provenance & Verification Source</span>
              <EvBadge strength={req.evidence_strength} />
            </div>
            <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '10px 12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                <span className={`badge ${prov.badgeClass}`}>{prov.label}</span>
              </div>
              <p style={{ fontSize: '0.8rem', color: '#475569', margin: '4px 0 0 0', lineHeight: '1.4' }}>
                {prov.description}
              </p>
              {(req.source || req.source_url) && (
                <div style={{ marginTop: '8px', paddingTop: '6px', borderTop: '1px solid #e2e8f0', fontSize: '0.78rem', color: '#64748b' }}>
                  <strong>Verification Source:</strong> {req.source || 'BIS Official Catalogue'}
                  {req.provenance === 'CURATED' && (
                    <span style={{ display: 'block', fontSize: '0.74rem', color: '#94a3b8', marginTop: '2px' }}>
                      (Curated technical entry verified against standards scope; distinct from statutory primary gazette orders)
                    </span>
                  )}
                  {req.source_url && (
                    <div style={{ wordBreak: 'break-all', marginTop: '2px', color: '#0369a1' }}>
                      Ref: {req.source_url}
                    </div>
                  )}
                </div>
              )}
            </div>
          </section>

          {/* 6. Lifecycle */}
          <section className="drawer-section">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
              <span className="drawer-section__label">6. Lifecycle Status</span>
              <span className={`badge ${lifecycleClass}`}>
                {req.lifecycle_status || 'Unknown'}
              </span>
            </div>
            {Boolean(req.superseded_citation || lifecycle === 'superseded') && (
              <div style={{ padding: '10px 12px', background: '#fffbeb', border: '1px solid #fde68a', borderRadius: '8px', fontSize: '0.82rem', color: '#92400e', marginTop: '6px' }}>
                <div style={{ fontWeight: 700, marginBottom: '2px' }}>⚠️ Lifecycle Advisory</div>
                <div>
                  Your tender references <strong>{req.superseded_citation || req.candidate_standard}</strong>, which appears superseded.
                  {req.successor_standard && (
                    <span> Recommended current active successor: <strong>{req.successor_standard}</strong>.</span>
                  )}
                  <span> Technical officer verification is required before tender finalization.</span>
                </div>
              </div>
            )}
            {req.successor_standard && !req.superseded_citation && lifecycle !== 'superseded' && (
              <div style={{ marginTop: '6px', fontSize: '0.82rem', color: '#475569' }}>
                <strong>Current Successor:</strong> <span className="drawer-successor-num">{req.successor_standard}</span>
              </div>
            )}
          </section>

          {/* 7. Missing Details (Only when present) */}
          {req.missing_parameters && req.missing_parameters.length > 0 && (
            <section className="drawer-section">
              <span className="drawer-section__label">7. Missing Details</span>
              <p className="drawer-missing-note">
                These technical parameters should be specified in the tender for unambiguous standard compliance:
              </p>
              <ul className="drawer-bullet-list drawer-bullet-list--missing">
                {req.missing_parameters.map((p, i) => (
                  <li key={i}>{p}</li>
                ))}
              </ul>
            </section>
          )}

          {/* 8. Related Standards (Only when present) */}
          {req.related_standards && req.related_standards.length > 0 && (
            <section className="drawer-section">
              <span className="drawer-section__label">8. Related Standards</span>
              <div className="drawer-related">
                {req.related_standards.map((rel, i) => (
                  <div key={i} className="drawer-related-item">
                    <div className="drawer-related-item__std">{rel.standard_number}</div>
                    <div className="drawer-related-item__rel">
                      {rel.relationship_type === 'REFERENCES' ? 'Normative Reference' : rel.relationship_type}
                      {rel.lifecycle_status ? ` · ${rel.lifecycle_status}` : ''}
                      {rel.review_note ? ` — ${rel.review_note}` : ''}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* 9. Standards Dependencies & Ecosystem Coverage (Milestone 10) */}
          {((req.dependencies && req.dependencies.length > 0) || req.standards_coverage) && (
            <section className="drawer-section">
              <span className="drawer-section__label">9. Standards Ecosystem & Dependencies</span>
              <div className="drawer-coverage-summary" style={{ marginTop: '0.5rem' }}>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginBottom: '0.75rem' }}>
                  <span className="badge badge--active" style={{ fontSize: '0.75rem' }}>
                    ✓ Primary: {req.candidate_standard || 'Standard Identified'}
                  </span>
                  {req.standards_coverage?.coverage_summary && (
                    <>
                      <span className="badge badge--low" style={{ fontSize: '0.75rem' }}>
                        {req.standards_coverage.coverage_summary.total_dependencies} Dependencies Mapped
                      </span>
                      {req.standards_coverage.coverage_summary.covered_in_tender > 0 && (
                        <span className="badge badge--active" style={{ fontSize: '0.75rem' }}>
                          {req.standards_coverage.coverage_summary.covered_in_tender} Cited in Tender
                        </span>
                      )}
                      {(req.standards_coverage.coverage_summary.potentially_missing + req.standards_coverage.coverage_summary.verified_missing) > 0 && (
                        <span className="badge badge--superseded" style={{ fontSize: '0.75rem' }}>
                          {req.standards_coverage.coverage_summary.potentially_missing + req.standards_coverage.coverage_summary.verified_missing} Potential Gaps
                        </span>
                      )}
                    </>
                  )}
                </div>

                <div className="drawer-dependencies-list" style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                  {(req.dependencies || []).map((dep, idx) => (
                    <div
                      key={idx}
                      style={{
                        background: '#f9fafb',
                        border: '1px solid #e5e7eb',
                        borderRadius: '6px',
                        padding: '0.65rem 0.75rem',
                        fontSize: '0.85rem'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                        <strong style={{ color: '#1a1f36' }}>{dep.standard_number}</strong>
                        <div style={{ display: 'flex', gap: '0.3rem', alignItems: 'center' }}>
                          <span className="badge badge--low" style={{ fontSize: '0.65rem', padding: '1px 6px' }}>
                            {dep.relationship_type.replace(/_/g, ' ')}
                          </span>
                          <span className="badge badge--active" style={{ fontSize: '0.65rem', padding: '1px 6px' }}>
                            {dep.provenance}
                          </span>
                        </div>
                      </div>
                      <div style={{ color: '#4b5563', fontSize: '0.8rem', marginBottom: '0.35rem' }}>{dep.title}</div>
                      <div style={{ color: '#6b7280', fontSize: '0.78rem', lineHeight: '1.4' }}>{dep.why_related}</div>
                    </div>
                  ))}
                </div>
              </div>
            </section>
          )}

          {/* 10. Regulatory & Certification Intelligence */}
          {req.regulatory && (
            <section className="drawer-section">
              <h3 className="drawer-section__title">10. Regulatory & Certification Intelligence</h3>
              <p style={{ fontSize: '0.78rem', color: '#64748b', marginTop: '-0.25rem', marginBottom: '0.75rem' }}>
                Statutory conformity assessment under the BIS Act, 2016 and Ministry Gazette Orders.
              </p>

              <div className="drawer-regulatory-grid">
                {/* BIS Product Certification */}
                <div className="regulatory-status-card">
                  <span className="regulatory-status-card__header">BIS Product Certification</span>
                  <div>
                    {req.regulatory.certification?.status === 'APPLICABLE' ? (
                      <span className="regulatory-badge regulatory-badge--applicable">✓ Mandatory Scheme-I</span>
                    ) : req.regulatory.certification?.status === 'REVIEW_REQUIRED' ? (
                      <span className="regulatory-badge regulatory-badge--review_required">⚠ Review Scheme</span>
                    ) : req.regulatory.certification?.status === 'NOT_IDENTIFIED' ? (
                      <span className="regulatory-badge regulatory-badge--not_identified">— Not Identified</span>
                    ) : (
                      <span className="regulatory-badge regulatory-badge--unknown">? Unknown</span>
                    )}
                  </div>
                </div>

                {/* Quality Control Order (QCO) */}
                <div className="regulatory-status-card">
                  <span className="regulatory-status-card__header">Quality Control Order</span>
                  <div>
                    {req.regulatory.qco?.status === 'CURRENT' ? (
                      <span className="regulatory-badge regulatory-badge--current">✓ Current QCO</span>
                    ) : req.regulatory.qco?.status === 'UPCOMING' ? (
                      <span className="regulatory-badge regulatory-badge--upcoming">⚠ Upcoming QCO</span>
                    ) : req.regulatory.qco?.status === 'NOT_IDENTIFIED' ? (
                      <span className="regulatory-badge regulatory-badge--not_identified">— Not Identified</span>
                    ) : (
                      <span className="regulatory-badge regulatory-badge--unknown">? Unknown</span>
                    )}
                  </div>
                </div>

                {/* Compulsory Registration Scheme (CRS) */}
                <div className="regulatory-status-card">
                  <span className="regulatory-status-card__header">Compulsory Registration (CRS)</span>
                  <div>
                    {req.regulatory.crs?.status === 'APPLICABLE' ? (
                      <span className="regulatory-badge regulatory-badge--applicable">✓ Mandatory Scheme-II</span>
                    ) : req.regulatory.crs?.status === 'NOT_IDENTIFIED' ? (
                      <span className="regulatory-badge regulatory-badge--not_identified">— Not Identified</span>
                    ) : (
                      <span className="regulatory-badge regulatory-badge--unknown">? Unknown</span>
                    )}
                  </div>
                </div>

                {/* Hallmarking */}
                <div className="regulatory-status-card">
                  <span className="regulatory-status-card__header">Hallmarking</span>
                  <div>
                    {req.regulatory.hallmarking?.status === 'APPLICABLE' ? (
                      <span className="regulatory-badge regulatory-badge--applicable">✓ Mandatory Gold HUID</span>
                    ) : req.regulatory.hallmarking?.status === 'REVIEW_REQUIRED' ? (
                      <span className="regulatory-badge regulatory-badge--review_required">⚠ Voluntary Silver</span>
                    ) : req.regulatory.hallmarking?.status === 'NOT_APPLICABLE' ? (
                      <span className="regulatory-badge regulatory-badge--not_applicable">— Not Applicable</span>
                    ) : (
                      <span className="regulatory-badge regulatory-badge--unknown">? Unknown</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Expandable Evidentiary Basis */}
              <div style={{ marginTop: '0.75rem' }}>
                <CollapseSection title="View Regulatory Evidentiary Basis" defaultOpen={false}>
                  <div className="regulatory-detail-box">
                    {req.regulatory.qco && req.regulatory.qco.status !== 'NOT_IDENTIFIED' && (
                      <div className="regulatory-detail-row">
                        <span className="regulatory-detail-label">QCO Basis: </span>
                        <span>{req.regulatory.qco.explanation}</span>
                        {req.regulatory.qco.legal_basis && (
                          <div style={{ color: '#64748b', fontSize: '0.74rem', marginTop: '2px' }}>
                            Legal Basis: {req.regulatory.qco.legal_basis} · Source: {req.regulatory.qco.source}
                          </div>
                        )}
                      </div>
                    )}

                    {req.regulatory.certification && req.regulatory.certification.status === 'APPLICABLE' && (
                      <div className="regulatory-detail-row">
                        <span className="regulatory-detail-label">Certification Basis: </span>
                        <span>{req.regulatory.certification.explanation}</span>
                        <div style={{ color: '#64748b', fontSize: '0.74rem', marginTop: '2px' }}>
                          Legal Basis: {req.regulatory.certification.legal_basis} · Source: {req.regulatory.certification.source}
                        </div>
                      </div>
                    )}

                    {req.regulatory.crs && req.regulatory.crs.status === 'APPLICABLE' && (
                      <div className="regulatory-detail-row">
                        <span className="regulatory-detail-label">CRS Basis: </span>
                        <span>{req.regulatory.crs.explanation}</span>
                        <div style={{ color: '#64748b', fontSize: '0.74rem', marginTop: '2px' }}>
                          Legal Basis: {req.regulatory.crs.legal_basis} · Source: {req.regulatory.crs.source}
                        </div>
                      </div>
                    )}

                    {req.regulatory.hallmarking && req.regulatory.hallmarking.status !== 'NOT_APPLICABLE' && (
                      <div className="regulatory-detail-row">
                        <span className="regulatory-detail-label">Hallmarking Basis: </span>
                        <span>{req.regulatory.hallmarking.explanation}</span>
                        <div style={{ color: '#64748b', fontSize: '0.74rem', marginTop: '2px' }}>
                          Legal Basis: {req.regulatory.hallmarking.legal_basis} · Source: {req.regulatory.hallmarking.source}
                        </div>
                      </div>
                    )}

                    {(!req.regulatory.qco || req.regulatory.qco.status === 'NOT_IDENTIFIED') &&
                     (!req.regulatory.certification || req.regulatory.certification.status !== 'APPLICABLE') &&
                     (!req.regulatory.crs || req.regulatory.crs.status !== 'APPLICABLE') &&
                     (!req.regulatory.hallmarking || req.regulatory.hallmarking.status === 'NOT_APPLICABLE') && (
                      <div style={{ color: '#64748b', fontStyle: 'italic' }}>
                        No mandatory Quality Control Order, CRS schedule, or Hallmarking mandate identified for this standard in current authoritative gazette records. Note: The existence of an Indian Standard does not automatically imply mandatory BIS certification.
                      </div>
                    )}
                  </div>
                </CollapseSection>
              </div>

              <div className="regulatory-disclaimer">
                Regulatory intelligence is evaluated deterministically from authoritative Ministry Gazette orders and BIS registries without LLM interpretation. Technical and legal officer review is required before contract finalization.
              </div>
            </section>
          )}

          {/* 11. Controlled Ambiguity & Decision Pipeline (Milestone 12) */}
          <section className="drawer-section" style={{ background: '#f8fafc', padding: '14px 16px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
            <h3 className="drawer-section__title" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span>11. Ambiguity & Decision Pipeline Audit</span>
              <span className={`badge ${
                req.ambiguity_state === 'CLEAR' ? 'badge--active' :
                req.ambiguity_state === 'CONFLICTING' ? 'badge--superseded' :
                req.ambiguity_state === 'AMBIGUOUS' ? 'badge--primary' :
                'badge--warning'
              }`} style={{ fontSize: '0.75rem', textTransform: 'uppercase' }}>
                {req.ambiguity_state || 'REVIEW_REQUIRED'}
              </span>
            </h3>

            {req.ambiguity_reason && (
              <p style={{ fontSize: '0.84rem', color: '#334155', margin: '4px 0 10px 0', lineHeight: '1.45', fontWeight: 500 }}>
                {req.ambiguity_reason}
              </p>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', margin: '8px 0 12px 0', fontSize: '0.78rem' }}>
              <div style={{ background: '#ffffff', padding: '6px 8px', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                <span style={{ color: '#64748b', display: 'block', fontSize: '0.7rem' }}>RETRIEVAL</span>
                <strong style={{ color: req.retrieval_status === 'ZERO_RESULTS' ? '#b91c1c' : '#1e293b' }}>
                  {req.retrieval_status || 'CANDIDATES_FOUND'}
                </strong>
              </div>
              <div style={{ background: '#ffffff', padding: '6px 8px', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                <span style={{ color: '#64748b', display: 'block', fontSize: '0.7rem' }}>APPLICABILITY</span>
                <strong style={{ color: req.applicability_status === 'ALL_REJECTED' ? '#b91c1c' : '#1e293b' }}>
                  {req.applicability_status || 'APPLICABLE'}
                </strong>
              </div>
              <div style={{ background: '#ffffff', padding: '6px 8px', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                <span style={{ color: '#64748b', display: 'block', fontSize: '0.7rem' }}>EVIDENCE</span>
                <strong style={{ color: req.evidence_status === 'VALID' ? '#166534' : '#b91c1c' }}>
                  {req.evidence_status || 'VALID'}
                </strong>
              </div>
            </div>

            {/* Competing Interpretations within separation threshold */}
            {req.competing_interpretations && req.competing_interpretations.length > 0 && (
              <div style={{ marginTop: '10px', background: '#ffffff', padding: '10px', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                <span style={{ fontSize: '0.78rem', fontWeight: 700, color: '#475569', display: 'block', marginBottom: '6px', textTransform: 'uppercase' }}>
                  Competing Candidate Standards ({req.competing_interpretations.length}):
                </span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {req.competing_interpretations.map((ci, idx) => (
                    <div key={idx} style={{ fontSize: '0.82rem', padding: '4px 6px', background: '#f8fafc', borderRadius: '4px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <strong style={{ color: '#1e293b' }}>{ci.standard_number}</strong>
                        {ci.score !== undefined && <span style={{ color: '#64748b', fontSize: '0.75rem' }}>Score: {ci.score.toFixed(3)}</span>}
                      </div>
                      {ci.title && <div style={{ color: '#475569', fontSize: '0.78rem' }}>{ci.title}</div>}
                      {ci.distinguishing_parameter_needed && (
                        <div style={{ color: '#7c3aed', fontSize: '0.75rem', marginTop: '2px' }}>
                          Distinguishing requirement: <em>{ci.distinguishing_parameter_needed}</em>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Actionable clarification question */}
            {req.suggested_clarification_question && (
              <div style={{ marginTop: '10px', padding: '10px 12px', background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '6px' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#166534', display: 'block', marginBottom: '3px' }}>
                  SUGGESTED CLARIFICATION QUESTION FOR TENDER OFFICER:
                </span>
                <p style={{ margin: 0, fontSize: '0.82rem', color: '#14532d', lineHeight: '1.4' }}>
                  "{req.suggested_clarification_question}"
                </p>
              </div>
            )}
          </section>

          {/* 12. Technical Details (Collapsed by default) */}
          <CollapseSection title="12. Technical Scoring & Algorithms" defaultOpen={false}>
            <div className="score-breakdown-list">
              <ScoreBar label="BM25" value={req.scores?.deterministic === 1.0 ? 'Not used' : req.scores?.bm25} />
              <ScoreBar label="Semantic" value={req.scores?.deterministic === 1.0 ? 'Not used' : req.scores?.semantic} />
              <ScoreBar label="Deterministic" value={req.scores?.deterministic} />
              {req.scores?.reranker !== null && req.scores?.reranker !== undefined && (
                <ScoreBar label="Reranker" value={req.scores?.deterministic === 1.0 ? 'Not used' : req.scores?.reranker} />
              )}
              <ScoreBar label="Final Score" value={req.scores?.final} />
            </div>


            <p className="score-formula-note">
              Relevance score σ(logit) = 1 / (1 + exp(-logit)). Combines BM25 lexical matching,
              bge/MiniLM embeddings, deterministic catalogue lookups, and cross-encoder reranking.
            </p>

            <div className="drawer-meta-row">
              <div>
                <span className="drawer-meta-label">Audit Decision</span>
                <span className="badge badge--review">{req.decision}</span>
              </div>
              <div>
                <span className="drawer-meta-label">Risk Level</span>
                <span className={`badge badge--${(req.risk_level || 'low').toLowerCase()}`}>
                  {req.risk_level} RISK
                </span>
              </div>
            </div>

            {req.applicability && (
              <div style={{ marginTop: '1rem', paddingTop: '0.75rem', borderTop: '1px solid #e2e8f0' }}>
                <span className="drawer-meta-label" style={{ fontWeight: 600, display: 'block', marginBottom: '0.5rem', color: '#1e293b' }}>
                  Applicability Assessment
                </span>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', fontSize: '0.82rem', color: '#475569' }}>
                  <div>Domain Match: <strong style={{ color: req.applicability.domain_match ? '#166534' : '#b91c1c' }}>{req.applicability.domain_match ? '✓ Yes' : '✗ Mismatch'}</strong></div>
                  <div>Product Match: <strong style={{ color: req.applicability.product_match ? '#166534' : '#b91c1c' }}>{req.applicability.product_match ? '✓ Yes' : '✗ Mismatch'}</strong></div>
                  <div>Scope Grounding: <strong style={{ color: req.applicability.scope_match ? '#166534' : '#b91c1c' }}>{req.applicability.scope_match ? '✓ Grounded' : '✗ Generic only'}</strong></div>
                  <div>Evidence Support: <strong style={{ color: req.applicability.evidence_support ? '#166534' : '#b91c1c' }}>{req.applicability.evidence_support ? '✓ Established' : '✗ Not established'}</strong></div>
                </div>
              </div>
            )}
          </CollapseSection>

          {/* 13. AI Understanding (Collapsed by default) */}
          <CollapseSection title="13. AI Requirement Understanding" defaultOpen={false}>
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
                <span>Understood using: <strong>Deterministic parser</strong></span>
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
        </div>
      </aside>
    </>
  );
}
