// Results.tsx — TenderSaathi Indian Standards Recommendation Results Page
import { useState, useMemo } from 'react';
import './Results.css';
import Header from '../components/Header';
import {
  RecommendationCard,
  AttentionCard,
  UpdateCard,
  RelatedCard,
} from '../components/RequirementCard';
import EvidenceDrawer from '../components/EvidenceDrawer';
import { downloadReport, triggerDownload } from '../api';
import type { AnalysisResult, Requirement, RelatedStandard } from '../types';

interface ResultsProps {
  result: AnalysisResult;
  onNewCheck: () => void;
}

export default function Results({ result, onNewCheck }: ResultsProps) {
  const [activeEvidenceReq, setActiveEvidenceReq] = useState<Requirement | null>(null);
  const [isDownloading, setIsDownloading] = useState(false);
  const [showReportMenu, setShowReportMenu] = useState(false);

  const { tender } = result;
  const allReqs = result.requirements || [];

  // 1. Recommended Standards: Genuine recommendations based on backend decision truth
  // Rule:
  // - RECOMMEND -> display as recommendation
  // - REVIEW_REQUIRED / RECOMMEND_WITH_REVIEW -> display recommendation + review warning
  // - INSUFFICIENT_EVIDENCE / INSUFFICIENT_INFORMATION / NONE -> excluded from recommendations
  const recommendedList = useMemo(() => {
    return allReqs.filter((req) => {
      const std = req.candidate_standard;
      if (!std || std === 'NONE' || std === 'INSUFFICIENT_INFORMATION') {
        return false;
      }
      // Never treat INSUFFICIENT_EVIDENCE as a recommended standard
      if (req.decision === 'INSUFFICIENT_EVIDENCE') {
        return false;
      }
      // If the candidate standard itself is superseded without replacement, don't recommend it
      if (
        req.lifecycle_status &&
        req.lifecycle_status.toLowerCase() === 'superseded' &&
        !req.successor_standard
      ) {
        return false;
      }

      if (
        req.decision === 'RECOMMEND' ||
        req.decision === 'RECOMMEND_WITH_REVIEW' ||
        req.decision === 'REVIEW_REQUIRED'
      ) {
        return true;
      }

      if (req.successor_standard && req.candidate_standard === req.successor_standard) {
        return true;
      }

      return false;
    });
  }, [allReqs]);

  // 2. Needs Attention: Actual missing parameters, ambiguity, or human review required
  const attentionList = useMemo(() => {
    return allReqs.filter((req) => {
      const hasMissing = req.missing_parameters && req.missing_parameters.length > 0;
      const isInsufficient =
        req.decision === 'INSUFFICIENT_EVIDENCE' ||
        req.candidate_standard === 'INSUFFICIENT_INFORMATION';
      const needsHumanReview = req.human_review_required || req.decision === 'REVIEW_REQUIRED';
      return hasMissing || isInsufficient || needsHumanReview;
    });
  }, [allReqs]);

  // 3. Standards That Need an Update: Superseded citations
  const updateList = useMemo(() => {
    return allReqs.filter((req) => {
      return Boolean(
        req.superseded_citation ||
        (req.lifecycle_status && req.lifecycle_status.toLowerCase() === 'superseded') ||
        (req.successor_standard && req.successor_standard !== req.candidate_standard)
      );
    });
  }, [allReqs]);

  // 4. Related Standards (Graph): Kept strictly separate ("Related ≠ Applicable")
  const relatedStandardsList = useMemo(() => {
    const list: Array<{ standard: RelatedStandard; parentStandard: string; parentReq: Requirement }> = [];
    const seen = new Set<string>();

    for (const req of allReqs) {
      if (!req.candidate_standard || req.candidate_standard === 'NONE' || req.candidate_standard === 'INSUFFICIENT_INFORMATION') {
        continue;
      }
      for (const rel of req.related_standards || []) {
        if (!rel.standard_number) continue;
        if (rel.standard_number === req.candidate_standard) continue;
        if (seen.has(rel.standard_number)) continue;
        seen.add(rel.standard_number);

        list.push({
          standard: rel,
          parentStandard: req.candidate_standard,
          parentReq: req,
        });
      }
    }
    return list;
  }, [allReqs]);

  // Format file size
  const formattedSize = useMemo(() => {
    if (!tender.file_size || tender.file_size === 0) return 'Tender Document';
    if (tender.file_size < 1024 * 1024) {
      return `${(tender.file_size / 1024).toFixed(1)} KB`;
    }
    return `${(tender.file_size / (1024 * 1024)).toFixed(1)} MB`;
  }, [tender.file_size]);

  // Ambiguity Summary Counts
  const ambiguityCounts = useMemo(() => {
    if (result.summary?.ambiguity_summary) {
      return result.summary.ambiguity_summary;
    }
    const counts = {
      clear: 0,
      ambiguous: 0,
      incomplete: 0,
      conflicting: 0,
      no_reliable_match: 0,
      review_required: 0,
    };
    allReqs.forEach((r) => {
      const st = (r.ambiguity_state || 'CLEAR').toLowerCase();
      if (st === 'clear') counts.clear++;
      else if (st === 'ambiguous') counts.ambiguous++;
      else if (st === 'incomplete') counts.incomplete++;
      else if (st === 'conflicting') counts.conflicting++;
      else if (st === 'no_reliable_match') counts.no_reliable_match++;
      else counts.review_required++;
    });
    return counts;
  }, [result.summary, allReqs]);

  // Download handler
  const handleDownload = async (format: 'markdown' | 'json') => {
    try {
      setIsDownloading(true);
      setShowReportMenu(false);
      const blob = await downloadReport(tender.id, format);
      const ext = format === 'markdown' ? 'md' : 'json';
      triggerDownload(blob, `TenderSaathi_Audit_${tender.id}.${ext}`);
    } catch (err) {
      alert(`Failed to download report: ${(err as Error).message}`);
    } finally {
      setIsDownloading(false);
    }
  };

  const recCount = recommendedList.length;

  return (
    <div className="results-page">
      <Header onLogoClick={onNewCheck} />

      <main className="results-container" role="main">
        {/* 1. Tender File Card at Top */}
        <section className="tender-file-card" aria-label="Analyzed tender file details">
          <div className="tender-file-card__left">
            <div className="tender-file-card__icon" aria-hidden="true">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
                <polyline points="10 9 9 9 8 9" />
              </svg>
            </div>
            <div className="tender-file-card__info">
              <h2 className="tender-file-card__name">{tender.source || 'Tender Document'}</h2>
              <p className="tender-file-card__meta">Uploaded · {formattedSize}</p>
            </div>
          </div>

          <div className="tender-file-card__right">
            <button
              type="button"
              className="tender-file-card__close-btn"
              onClick={onNewCheck}
              aria-label="Clear tender analysis"
              title="Clear check"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>

            <button
              type="button"
              className="tender-file-card__new-btn"
              onClick={onNewCheck}
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <polyline points="23 4 23 10 17 10" />
                <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
              </svg>
              New check
            </button>
          </div>
        </section>

        {/* 2. Hero Headline + Download Report Button */}
        <div className="results-hero">
          <div className="results-hero__left">
            <p className="results-eyebrow">ANALYSIS COMPLETE</p>
            <h1 className="results-title">
              Indian Standards for your tender.
            </h1>
            <p className="results-desc">
              We found standards that may apply to the requirements in your tender. Review the recommendations and any items that need clarification before publication.
            </p>
          </div>

          <div className="results-hero__right">
            <div className="report-download-wrap">
              <button
                type="button"
                className="btn-download-report"
                onClick={() => setShowReportMenu((prev) => !prev)}
                disabled={isDownloading}
                aria-label="Download analysis report"
                aria-expanded={showReportMenu}
              >
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="7 10 12 15 17 10" />
                  <line x1="12" y1="15" x2="12" y2="3" />
                </svg>
                {isDownloading ? 'Downloading...' : 'Download report'}
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <polyline points="6 9 12 15 18 9" />
                </svg>
              </button>

              {showReportMenu && (
                <div className="report-dropdown-menu">
                  <button
                    type="button"
                    onClick={() => handleDownload('markdown')}
                    className="report-dropdown-item"
                  >
                    <span>Full Audit Report</span>
                    <span className="file-type-tag">.MD</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDownload('json')}
                    className="report-dropdown-item"
                  >
                    <span>Machine-Readable Data</span>
                    <span className="file-type-tag">.JSON</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Ambiguity & Verification States Summary Bar */}
        <div className="ambiguity-summary-bar" style={{
          background: '#ffffff',
          border: '1px solid #e2e8f0',
          borderRadius: '12px',
          padding: '16px 20px',
          marginBottom: '24px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.02)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px', flexWrap: 'wrap', gap: '8px' }}>
            <span style={{ fontSize: '0.82rem', fontWeight: 700, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              6-Stage Ambiguity & Verification Audit Summary
            </span>
            <span style={{ fontSize: '0.78rem', color: '#64748b' }}>
              Deterministic Technical Gates · Human Review Enforced
            </span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '10px' }}>
            <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', padding: '10px', borderRadius: '8px', textAlign: 'center' }}>
              <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#166534' }}>{ambiguityCounts.clear}</div>
              <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#15803d' }}>Clear Matches</div>
            </div>
            <div style={{ background: '#f5f3ff', border: '1px solid #ddd6fe', padding: '10px', borderRadius: '8px', textAlign: 'center' }}>
              <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#6b21a8' }}>{ambiguityCounts.ambiguous}</div>
              <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#7c3aed' }}>Ambiguous</div>
            </div>
            <div style={{ background: '#fff7ed', border: '1px solid #fed7aa', padding: '10px', borderRadius: '8px', textAlign: 'center' }}>
              <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#c2410c' }}>{ambiguityCounts.incomplete}</div>
              <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#ea580c' }}>Incomplete Specs</div>
            </div>
            <div style={{ background: '#fef2f2', border: '1px solid #fecaca', padding: '10px', borderRadius: '8px', textAlign: 'center' }}>
              <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#b91c1c' }}>{ambiguityCounts.conflicting}</div>
              <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#dc2626' }}>Conflicting</div>
            </div>
            <div style={{ background: '#f8fafc', border: '1px solid #cbd5e1', padding: '10px', borderRadius: '8px', textAlign: 'center' }}>
              <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#475569' }}>{ambiguityCounts.no_reliable_match}</div>
              <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#64748b' }}>No Reliable Match</div>
            </div>
            <div style={{ background: '#fffdf7', border: '1px solid #fde68a', padding: '10px', borderRadius: '8px', textAlign: 'center' }}>
              <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#b45309' }}>{ambiguityCounts.review_required}</div>
              <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#d97706' }}>Review Required</div>
            </div>
          </div>
        </div>

        {/* 3. PRIMARY SECTION: INDIAN STANDARDS TO CONSIDER */}
        <section className="results-section results-section--primary" aria-label="Indian Standards to consider">
          <div className="section-banner">
            <div className="section-banner__header">
              <h2 className="section-banner__title">INDIAN STANDARDS TO CONSIDER</h2>
              <span className="section-banner__count">
                {recCount === 1
                  ? '1 Indian Standard recommended'
                  : recCount > 1
                  ? `${recCount} Indian Standards recommended`
                  : 'No reliable standard match found'}
              </span>
            </div>
          </div>

          <div className="recommendations-list">
            {recCount > 0 ? (
              recommendedList.map((req, i) => (
                <RecommendationCard
                  key={req.id || i}
                  req={req}
                  isPrimary={i === 0 && recCount > 1}
                  onOpenEvidence={setActiveEvidenceReq}
                />
              ))
            ) : (
              <div className="rec-empty-card">
                <div className="rec-empty-card__icon" aria-hidden="true">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="8" x2="12" y2="12" />
                    <line x1="12" y1="16" x2="12.01" y2="16" />
                  </svg>
                </div>
                <div>
                  <h3 className="rec-empty-card__title">No reliable standard match found</h3>
                  <p className="rec-empty-card__desc">
                    We could not establish a sufficiently supported Indian Standard from the available catalogue.
                  </p>
                </div>
              </div>
            )}
          </div>
        </section>

        {/* 4. SECTION 2: NEEDS YOUR ATTENTION */}
        {attentionList.length > 0 && (
          <section className="results-section results-section--attention" aria-label="Requirements that need your attention">
            <div className="section-header-row">
              <div className="section-header-row__left">
                <h3 className="section-subheading">NEEDS YOUR ATTENTION</h3>
                <p className="section-subheading-desc">
                  Review these items that need engineering clarification or additional specification details before publication.
                </p>
              </div>
              <span className="section-badge section-badge--attention">
                {attentionList.length} item{attentionList.length === 1 ? '' : 's'}
              </span>
            </div>

            <div className="attention-list">
              {attentionList.map((req, i) => (
                <AttentionCard
                  key={req.id || i}
                  req={req}
                  onOpenEvidence={setActiveEvidenceReq}
                />
              ))}
            </div>
          </section>
        )}

        {/* 5. SECTION 3: STANDARDS THAT NEED AN UPDATE */}
        <section className="results-section results-section--update" aria-label="Standards that need an update">
          <div className="section-header-row">
            <div className="section-header-row__left">
              <h3 className="section-subheading">STANDARDS THAT NEED AN UPDATE</h3>
              <p className="section-subheading-desc">
                Superseded or outdated Indian Standards identified in the tender specifications.
              </p>
            </div>
            {updateList.length > 0 && (
              <span className="section-badge section-badge--warning">
                {updateList.length} superseded
              </span>
            )}
          </div>

          {updateList.length > 0 ? (
            <div className="update-list">
              {updateList.map((req, i) => (
                <UpdateCard
                  key={req.id || i}
                  req={req}
                  onOpenEvidence={setActiveEvidenceReq}
                />
              ))}
            </div>
          ) : (
            <div className="update-empty-box">
              <span className="update-empty-box__icon" aria-hidden="true">✓</span>
              <span>No outdated or superseded standard references found.</span>
            </div>
          )}
        </section>

        {/* 6. SECTION 4: RELATED STANDARDS TO REVIEW */}
        {relatedStandardsList.length > 0 && (
          <section className="results-section results-section--related" aria-label="Related standards to review">
            <div className="section-header-row">
              <div className="section-header-row__left">
                <h3 className="section-subheading">RELATED STANDARDS TO REVIEW</h3>
                <p className="section-subheading-desc">
                  These standards are referenced by the recommended standards or exist in the standards knowledge graph. Review for co-application. They are not automatic recommendations.
                </p>
              </div>
              <span className="section-badge section-badge--neutral">
                {relatedStandardsList.length} reference{relatedStandardsList.length === 1 ? '' : 's'}
              </span>
            </div>

            <div className="related-list">
              {relatedStandardsList.map((item, i) => (
                <RelatedCard
                  key={i}
                  related={item.standard}
                  parentStandard={item.parentStandard}
                  parentReq={item.parentReq}
                  onOpenEvidence={setActiveEvidenceReq}
                />
              ))}
            </div>
          </section>
        )}

        {/* 7. Security & Privacy Footer Note */}
        <footer className="results-footer">
          <div className="security-notice">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
            <span>Your documents are secure and private.</span>
          </div>
        </footer>
      </main>

      {/* 8. Evidence Drawer (opens on 'See why') */}
      {activeEvidenceReq && (
        <EvidenceDrawer
          req={activeEvidenceReq}
          onClose={() => setActiveEvidenceReq(null)}
        />
      )}
    </div>
  );
}
