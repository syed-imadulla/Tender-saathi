// Results.tsx — The central Results screen (State 3)
// Features progressive disclosure: high-level readiness banner -> categorized cards -> deep evidence drawer
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

type TabType = 'all' | 'attention' | 'good' | 'update';

export default function Results({ result, onNewCheck }: ResultsProps) {
  const [activeTab, setActiveTab] = useState<TabType>('all');
  const [activeEvidenceReq, setActiveEvidenceReq] = useState<Requirement | null>(null);
  const [isDownloading, setIsDownloading] = useState(false);

  const { tender, summary, readiness, readiness_reasons, sections, metadata } = result;

  const attentionList = sections?.needs_attention || [];
  const goodList = sections?.looks_good || [];
  const updateList = sections?.standards_to_update || [];

  // Determine readiness theme
  const readinessTheme = useMemo(() => {
    if (readiness === 'READY_FOR_REVIEW') {
      return {
        variant: 'green',
        label: 'Ready for Review',
        headline: 'All Citations Validated with Active Standards',
        desc: 'All analyzed requirements cite active Indian standards and meet baseline technical completeness requirements.',
      };
    }
    if (readiness === 'REVIEW_REQUIRED') {
      return {
        variant: 'amber',
        label: 'Action Required',
        headline: `${summary.needs_attention} Requirement${summary.needs_attention === 1 ? '' : 's'} Need Review Before Publishing`,
        desc: 'Ambiguous wording, missing mandatory testing parameters, or unconfirmed citations require procurement officer sign-off.',
      };
    }
    return {
      variant: 'red',
      label: 'Critical Warning',
      headline: 'Superseded Standards or Critical Gaps Identified',
      desc: 'Outdated standard citations or severe specification gaps detected. Revisions are mandatory before publishing the tender.',
    };
  }, [readiness, summary.needs_attention]);

  // Filtered requirements list
  const displayItems = useMemo(() => {
    if (activeTab === 'attention') {
      return attentionList.map((req) => ({ req, type: 'attention' as const }));
    }
    if (activeTab === 'good') {
      return goodList.map((req) => ({ req, type: 'good' as const }));
    }
    if (activeTab === 'update') {
      return updateList.map((req) => ({ req, type: 'update' as const }));
    }
    // 'all' shows update items first, then attention, then good
    return [
      ...updateList.map((req) => ({ req, type: 'update' as const })),
      ...attentionList.map((req) => ({ req, type: 'attention' as const })),
      ...goodList.map((req) => ({ req, type: 'good' as const })),
    ];
  }, [activeTab, attentionList, goodList, updateList]);

  // Report downloads
  const handleDownload = async (format: 'markdown' | 'json') => {
    try {
      setIsDownloading(true);
      const blob = await downloadReport(tender.id, format);
      const ext = format === 'markdown' ? 'md' : 'json';
      triggerDownload(blob, `TenderSaathi_Audit_${tender.id}.${ext}`);
    } catch (err) {
      alert(`Failed to download report: ${(err as Error).message}`);
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div className="results-page">
      <Header onLogoClick={onNewCheck} />

      <main className="results-content">
        {/* Top bar with tender metadata and actions */}
        <div className="results-topbar">
          <div className="results-topbar__meta">
            <span className="results-topbar__id">{tender.id}</span>
            <span className="results-topbar__source">
              Source: <strong>{tender.source}</strong>
            </span>
            <span className="ai-meta-tag">
              <span
                className={`ai-meta-tag__dot ${
                  metadata?.is_ai_fallback ? 'ai-meta-tag__dot--fallback' : ''
                }`}
              />
              {metadata?.is_ai_fallback
                ? 'Deterministic Decomposition'
                : `AI: ${metadata?.ai_model || 'Groq'}`}
            </span>
          </div>

          <div className="results-topbar__actions">
            <button
              type="button"
              className="btn btn--secondary btn--sm"
              onClick={() => handleDownload('markdown')}
              disabled={isDownloading}
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
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              Audit Report (.md)
            </button>

            <button
              type="button"
              className="btn btn--secondary btn--sm"
              onClick={() => handleDownload('json')}
              disabled={isDownloading}
            >
              Export JSON
            </button>

            <button
              type="button"
              className="btn btn--primary btn--sm"
              onClick={onNewCheck}
            >
              Check Another Tender
            </button>
          </div>
        </div>

        {/* Readiness Hero Banner */}
        <section
          className={`readiness-banner readiness-banner--${readinessTheme.variant}`}
          aria-label="Tender readiness status"
        >
          <div className="readiness-header">
            <div>
              <div className="readiness-status">
                <span
                  className={`readiness-badge readiness-badge--${readinessTheme.variant}`}
                >
                  {readinessTheme.label}
                </span>
                <span className="text-muted" style={{ fontSize: '0.85rem' }}>
                  Indian Standards Compliance Audit
                </span>
              </div>
              <h1 className="readiness-title">{readinessTheme.headline}</h1>
              <p className="readiness-desc">{readinessTheme.desc}</p>
            </div>
          </div>

          {readiness_reasons && readiness_reasons.length > 0 && (
            <ul className="readiness-reasons">
              {readiness_reasons.map((reason, idx) => (
                <li key={idx}>{reason}</li>
              ))}
            </ul>
          )}

          {/* Metric Stats Strip */}
          <div className="metric-strip">
            <div className="metric-card">
              <span className="metric-card__val">
                {summary.requirements_analyzed || 0}
              </span>
              <span className="metric-card__label">Requirements</span>
            </div>

            <div className="metric-card">
              <span className="metric-card__val metric-card__val--amber">
                {summary.needs_attention || 0}
              </span>
              <span className="metric-card__label">Needs Attention</span>
            </div>

            <div className="metric-card">
              <span className="metric-card__val metric-card__val--green">
                {summary.looks_good || 0}
              </span>
              <span className="metric-card__label">Looks Good</span>
            </div>

            <div className="metric-card">
              <span className="metric-card__val metric-card__val--red">
                {summary.standards_to_update || 0}
              </span>
              <span className="metric-card__label">To Update</span>
            </div>

            <div className="metric-card">
              <span className="metric-card__val">
                {summary.active_count || 0}
              </span>
              <span className="metric-card__label">Active BIS</span>
            </div>

            <div className="metric-card">
              <span className="metric-card__val">
                {summary.related_standards_count || 0}
              </span>
              <span className="metric-card__label">Graph Relations</span>
            </div>
          </div>
        </section>

        {/* Filter Navigation */}
        <div className="results-filter-bar">
          <div className="filter-pills" role="tablist" aria-label="Filter requirements">
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === 'all'}
              className={`filter-pill ${activeTab === 'all' ? 'filter-pill--active' : ''}`}
              onClick={() => setActiveTab('all')}
            >
              All Requirements
              <span className="filter-pill__count">
                {summary.requirements_analyzed || 0}
              </span>
            </button>

            <button
              type="button"
              role="tab"
              aria-selected={activeTab === 'attention'}
              className={`filter-pill ${
                activeTab === 'attention' ? 'filter-pill--active' : ''
              }`}
              onClick={() => setActiveTab('attention')}
            >
              Needs Attention
              <span className="filter-pill__count">
                {attentionList.length}
              </span>
            </button>

            <button
              type="button"
              role="tab"
              aria-selected={activeTab === 'good'}
              className={`filter-pill ${activeTab === 'good' ? 'filter-pill--active' : ''}`}
              onClick={() => setActiveTab('good')}
            >
              Looks Good
              <span className="filter-pill__count">{goodList.length}</span>
            </button>

            {updateList.length > 0 && (
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === 'update'}
                className={`filter-pill ${
                  activeTab === 'update' ? 'filter-pill--active' : ''
                }`}
                onClick={() => setActiveTab('update')}
              >
                Standards to Update
                <span className="filter-pill__count">
                  {updateList.length}
                </span>
              </button>
            )}
          </div>
        </div>

        {/* Section Intro */}
        <div className="section-intro">
          <h2 className="section-intro__title">
            {activeTab === 'attention' && 'Requirements Requiring Procurement Review'}
            {activeTab === 'good' && 'Compliant Requirements with Active Standards'}
            {activeTab === 'update' && 'Outdated or Superseded Citations to Replace'}
            {activeTab === 'all' && 'All Detailed Requirement Verifications'}
          </h2>
          <p className="section-intro__desc">
            Click any requirement card to inspect full parameters, or open the
            Evidence Drawer for full grounding and AI decomposition details.
          </p>
        </div>

        {/* Requirements Stack */}
        <div className="requirements-stack">
          {displayItems.length === 0 ? (
            <div className="results-empty">
              <div className="results-empty__title">No requirements in this category</div>
              <p>Everything in this section is clear or has been verified.</p>
            </div>
          ) : (
            displayItems.map(({ req, type }) => (
              <RequirementCard
                key={req.id}
                req={req}
                sectionType={type}
                onOpenEvidence={(r) => setActiveEvidenceReq(r)}
              />
            ))
          )}
        </div>
      </main>

      {/* Progressive Disclosure Evidence Drawer */}
      {activeEvidenceReq && (
        <EvidenceDrawer
          req={activeEvidenceReq}
          onClose={() => setActiveEvidenceReq(null)}
        />
      )}
    </div>
  );
}
