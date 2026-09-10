// Results.tsx — Main Results screen matching Reference Image 2
import { useState, useMemo } from 'react';
import './Results.css';
import Header from '../components/Header';
import RequirementCard from '../components/RequirementCard';
import EvidenceDrawer from '../components/EvidenceDrawer';
import { downloadReport, triggerDownload } from '../api';
import type { AnalysisResult, Requirement } from '../types';

interface ResultsProps {
  result: AnalysisResult;
  onNewCheck: () => void;
}

export default function Results({ result, onNewCheck }: ResultsProps) {
  const [activeEvidenceReq, setActiveEvidenceReq] = useState<Requirement | null>(null);
  const [isDownloading, setIsDownloading] = useState(false);
  const [showReportMenu, setShowReportMenu] = useState(false);

  // Accordion open/close states (default attention & update open, good closed if attention has items)
  const [attentionOpen, setAttentionOpen] = useState(true);
  const [goodOpen, setGoodOpen] = useState(result.sections?.needs_attention?.length === 0);
  const [updateOpen, setUpdateOpen] = useState(true);

  const { tender, summary, readiness, sections } = result;

  const attentionList = sections?.needs_attention || [];
  const goodList = sections?.looks_good || [];
  const updateList = sections?.standards_to_update || [];

  // Format file size
  const formattedSize = useMemo(() => {
    if (!tender.file_size || tender.file_size === 0) return 'Tender Document';
    if (tender.file_size < 1024 * 1024) {
      return `${(tender.file_size / 1024).toFixed(1)} KB`;
    }
    return `${(tender.file_size / (1024 * 1024)).toFixed(1)} MB`;
  }, [tender.file_size]);

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

  // Readiness badge color & label
  const readinessBadge = useMemo(() => {
    switch (readiness) {
      case 'READY_FOR_REVIEW':
        return { label: 'READY FOR REVIEW', className: 'readiness-pill--ready' };
      case 'INSUFFICIENT_EVIDENCE':
        return { label: 'INSUFFICIENT EVIDENCE', className: 'readiness-pill--insufficient' };
      case 'REVIEW_REQUIRED':
      default:
        return { label: 'REVIEW REQUIRED', className: 'readiness-pill--review' };
    }
  }, [readiness]);

  // Dynamic summary sentence
  const attentionCount = summary.needs_attention + summary.standards_to_update;
  const standardsCount = summary.active_count + summary.superseded_count || attentionList.length + goodList.length;

  return (
    <div className="results-page">
      <Header onLogoClick={onNewCheck} />

      <main className="results-container" role="main">
        {/* 1. Tender File Card at Top */}
        <div className="tender-file-card" aria-label="Analyzed tender file details">
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
        </div>

        {/* 2. Analysis Complete Headline + Download Report Button */}
        <div className="results-hero">
          <div className="results-hero__left">
            <p className="results-eyebrow">ANALYSIS COMPLETE</p>
            <h1 className="results-title">
              Here’s what we <span>found.</span>
            </h1>
            <p className="results-desc">
              We analysed your tender using relevant Indian Standards (BIS) and found a few things that need your attention.
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

        {/* 3. Summary Card */}
        <div className="summary-card" aria-label="Tender findings summary">
          <div className="summary-card__icon-wrap" aria-hidden="true">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
          </div>

          <div className="summary-card__content">
            <div className="summary-card__headline-row">
              <h3 className="summary-card__title">
                {attentionList.length > 0
                  ? `${attentionList.length} thing${attentionList.length === 1 ? '' : 's'} need your attention.`
                  : updateList.length > 0
                  ? `${updateList.length} standard${updateList.length === 1 ? '' : 's'} need an update.`
                  : 'All analyzed requirements look good.'}
              </h3>
              <span className={`readiness-pill ${readinessBadge.className}`}>
                {readinessBadge.label}
              </span>
            </div>
            <p className="summary-card__stats">
              {goodList.length} requirement{goodList.length === 1 ? '' : 's'} look good
              &nbsp;&nbsp;·&nbsp;&nbsp;
              {attentionList.length} need{attentionList.length === 1 ? 's' : ''} more details
              &nbsp;&nbsp;·&nbsp;&nbsp;
              {standardsCount} relevant Indian Standard{standardsCount === 1 ? '' : 's'} found
            </p>
          </div>
        </div>

        {/* 4. MAIN RESULTS: EXACTLY THREE EXPANDABLE SECTIONS */}
        <div className="results-accordions">
          {/* Section A: Needs your attention */}
          <section className="accordion-section accordion-section--attention" aria-label="Requirements that need your attention">
            <div
              className="accordion-header"
              onClick={() => setAttentionOpen((prev) => !prev)}
              role="button"
              tabIndex={0}
              aria-expanded={attentionOpen}
              onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && setAttentionOpen((prev) => !prev)}
            >
              <div className="accordion-header__left">
                <div className="accordion-badge accordion-badge--attention" aria-hidden="true">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                    <line x1="12" y1="9" x2="12" y2="13" />
                    <line x1="12" y1="17" x2="12.01" y2="17" />
                  </svg>
                </div>
                <div className="accordion-header__text">
                  <h3 className="accordion-title">Needs your attention</h3>
                  <p className="accordion-subtitle">These items may need clarification or additional details.</p>
                </div>
              </div>

              <div className="accordion-header__right">
                <span className="accordion-count">{attentionList.length} item{attentionList.length === 1 ? '' : 's'}</span>
                <svg
                  className={`accordion-chevron ${attentionOpen ? 'accordion-chevron--open' : ''}`}
                  width="18"
                  height="18"
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
              </div>
            </div>

            {attentionOpen && (
              <div className="accordion-body">
                {attentionList.length > 0 ? (
                  attentionList.map((req, i) => (
                    <RequirementCard
                      key={req.id || i}
                      req={req}
                      index={i + 1}
                      sectionType="attention"
                      onOpenEvidence={setActiveEvidenceReq}
                      defaultExpanded={false}
                    />
                  ))
                ) : (
                  <div className="accordion-empty">
                    No requirements flagged for attention. All citations meet verified standards.
                  </div>
                )}
              </div>
            )}
          </section>

          {/* Section B: Looks good */}
          <section className="accordion-section accordion-section--good" aria-label="Requirements that look good">
            <div
              className="accordion-header"
              onClick={() => setGoodOpen((prev) => !prev)}
              role="button"
              tabIndex={0}
              aria-expanded={goodOpen}
              onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && setGoodOpen((prev) => !prev)}
            >
              <div className="accordion-header__left">
                <div className="accordion-badge accordion-badge--good" aria-hidden="true">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                </div>
                <div className="accordion-header__text">
                  <h3 className="accordion-title">Looks good</h3>
                  <p className="accordion-subtitle">These requirements have strong supporting evidence.</p>
                </div>
              </div>

              <div className="accordion-header__right">
                <span className="accordion-count">{goodList.length} item{goodList.length === 1 ? '' : 's'}</span>
                <svg
                  className={`accordion-chevron ${goodOpen ? 'accordion-chevron--open' : ''}`}
                  width="18"
                  height="18"
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
              </div>
            </div>

            {goodOpen && (
              <div className="accordion-body">
                {goodList.length > 0 ? (
                  goodList.map((req, i) => (
                    <RequirementCard
                      key={req.id || i}
                      req={req}
                      index={i + 1}
                      sectionType="good"
                      onOpenEvidence={setActiveEvidenceReq}
                      defaultExpanded={false}
                    />
                  ))
                ) : (
                  <div className="accordion-empty">
                    No active citations currently marked fully verified without notes.
                  </div>
                )}
              </div>
            )}
          </section>

          {/* Section C: Standards that need an update */}
          <section className="accordion-section accordion-section--update" aria-label="Standards that need an update">
            <div
              className="accordion-header"
              onClick={() => setUpdateOpen((prev) => !prev)}
              role="button"
              tabIndex={0}
              aria-expanded={updateOpen}
              onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && setUpdateOpen((prev) => !prev)}
            >
              <div className="accordion-header__left">
                <div className="accordion-badge accordion-badge--update" aria-hidden="true">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                  </svg>
                </div>
                <div className="accordion-header__text">
                  <h3 className="accordion-title">Standards that need an update</h3>
                  <p className="accordion-subtitle">These standards seem outdated. Consider using the latest version.</p>
                </div>
              </div>

              <div className="accordion-header__right">
                <span className="accordion-count">{updateList.length} item{updateList.length === 1 ? '' : 's'}</span>
                <svg
                  className={`accordion-chevron ${updateOpen ? 'accordion-chevron--open' : ''}`}
                  width="18"
                  height="18"
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
              </div>
            </div>

            {updateOpen && (
              <div className="accordion-body">
                {updateList.length > 0 ? (
                  updateList.map((req, i) => (
                    <RequirementCard
                      key={req.id || i}
                      req={req}
                      index={i + 1}
                      sectionType="update"
                      onOpenEvidence={setActiveEvidenceReq}
                      defaultExpanded={false}
                    />
                  ))
                ) : (
                  <div className="accordion-empty">
                    No outdated or superseded standard citations identified in this tender.
                  </div>
                )}
              </div>
            )}
          </section>
        </div>

        {/* 5. Security & Privacy Footer Note */}
        <footer className="results-footer">
          <div className="security-notice">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
            <span>Your documents are secure and private.</span>
          </div>
        </footer>
      </main>

      {/* 6. Evidence Drawer (opens on 'See why') */}
      {activeEvidenceReq && (
        <EvidenceDrawer
          req={activeEvidenceReq}
          onClose={() => setActiveEvidenceReq(null)}
        />
      )}
    </div>
  );
}
