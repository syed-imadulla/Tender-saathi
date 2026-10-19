// Results.tsx — TenderSaathi Indian Standards Recommendation Results Page
import { useState, useMemo, useEffect } from 'react';
import './Results.css';
import Header from '../components/Header';
import {
  RecommendationCard,
  AttentionCard,
  UpdateCard,
  RelatedCard,
} from '../components/RequirementCard';
import EvidenceDrawer from '../components/EvidenceDrawer';
import { downloadReport, triggerDownload, submitReviewDecisions, getReviewDecisions } from '../api';
import type {
  AnalysisResult,
  Requirement,
  RelatedStandard,
  HumanReviewDecision,
  ReviewProgressSummary,
  PackageSummary,
  ComplementaryStandardSuite,
  UncoveredTenderDependency,
} from '../types';

interface ResultsProps {
  result: AnalysisResult;
  onNewCheck: () => void;
}

export function filterRecommendedRequirements(allReqs: Requirement[]): Requirement[] {
  return allReqs.filter((req) => {
    const std = req.candidate_standard;
    if (!std || std === 'NONE' || std === 'INSUFFICIENT_INFORMATION') {
      return false;
    }
    // Never treat INSUFFICIENT_EVIDENCE as a recommended standard
    if (req.decision === 'INSUFFICIENT_EVIDENCE') {
      return false;
    }
    // Pure recommendations must not require human engineering review
    if (req.decision === 'REVIEW_REQUIRED' || req.human_review_required) {
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

    if (req.decision === 'RECOMMEND') {
      return true;
    }

    if (req.successor_standard && req.candidate_standard === req.successor_standard) {
      return true;
    }

    return false;
  });
}

export function filterAttentionRequirements(allReqs: Requirement[]): Requirement[] {
  return allReqs.filter((req) => {
    const hasMissing = req.missing_parameters && req.missing_parameters.length > 0;
    const isInsufficient =
      req.decision === 'INSUFFICIENT_EVIDENCE' ||
      req.candidate_standard === 'INSUFFICIENT_INFORMATION';
    const needsHumanReview = req.human_review_required || req.decision === 'REVIEW_REQUIRED';
    const isAbstentionOrNonClear =
      !req.candidate_standard ||
      req.candidate_standard === 'NONE' ||
      req.decision === 'NO_RELIABLE_MATCH' ||
      req.decision === 'REJECT' ||
      (req.ambiguity_state && req.ambiguity_state !== 'CLEAR');
    return hasMissing || isInsufficient || needsHumanReview || isAbstentionOrNonClear;
  });
}

export default function Results({ result, onNewCheck }: ResultsProps) {
  const [activeEvidenceReq, setActiveEvidenceReq] = useState<Requirement | null>(null);
  const [isDownloading, setIsDownloading] = useState(false);
  const [showReportMenu, setShowReportMenu] = useState(false);
  const [humanDecisions, setHumanDecisions] = useState<Record<string, HumanReviewDecision>>({});
  const [serverProgress, setServerProgress] = useState<ReviewProgressSummary | null>(null);
  const [reviewFilterTab, setReviewFilterTab] = useState<'all' | 'pending' | 'reviewed'>('all');
  const [selectedPackage, setSelectedPackage] = useState<string>('ALL');

  const { tender } = result;
  const allReqs = result.requirements || [];

  // Package summaries derivation (Phase 28)
  const packageSummaries = useMemo<PackageSummary[]>(() => {
    if (result.summary?.package_summaries && result.summary.package_summaries.length > 0) {
      return result.summary.package_summaries;
    }
    const map = new Map<string, PackageSummary>();
    allReqs.forEach((r) => {
      const pkgId = r.package_id || 'PKG-GENERAL';
      if (!map.has(pkgId)) {
        map.set(pkgId, {
          package_id: pkgId,
          package_name: r.package_name || (pkgId === 'PKG-GEN' || pkgId === 'PKG-GENERAL' ? 'General / Commercial Conditions' : pkgId),
          domains: r.domain ? [r.domain] : ['General'],
          standards: [],
          requirement_count: 0,
          clause_verified_count: 0,
          catalogue_discovered_count: 0,
          safe_abstention_count: 0,
          human_review_count: 0,
          is_general_conditions: pkgId === 'PKG-GEN' || pkgId === 'PKG-GENERAL',
        });
      }
      const entry = map.get(pkgId)!;
      entry.requirement_count++;
      if (r.candidate_standard && !entry.standards.includes(r.candidate_standard)) {
        entry.standards.push(r.candidate_standard);
      }
      if (r.verification_tier === 'CLAUSE_VERIFIED') entry.clause_verified_count++;
      else if (r.verification_tier === 'CATALOGUE_DISCOVERED') entry.catalogue_discovered_count++;
      else if (r.verification_tier === 'SAFE_ABSTENTION') entry.safe_abstention_count++;
      if (r.human_review_required || r.decision === 'REVIEW_REQUIRED') entry.human_review_count++;
    });
    return Array.from(map.values());
  }, [result.summary?.package_summaries, allReqs]);

  const activePackageSummary = useMemo(() => {
    if (selectedPackage === 'ALL') return null;
    return packageSummaries.find((p) => p.package_id === selectedPackage) || null;
  }, [packageSummaries, selectedPackage]);

  // Requirement filtering by selected package without altering tender-wide findings
  const displayedReqs = useMemo(() => {
    if (selectedPackage === 'ALL') return allReqs;
    return allReqs.filter((req) => (req.package_id || 'PKG-GENERAL') === selectedPackage);
  }, [allReqs, selectedPackage]);

  // Verification Tier summary counts across entire tender
  const tierCounts = useMemo(() => {
    const cv = result.summary?.clause_verified_count ?? allReqs.filter((r) => r.verification_tier === 'CLAUSE_VERIFIED').length;
    const cd = result.summary?.catalogue_discovered_count ?? allReqs.filter((r) => r.verification_tier === 'CATALOGUE_DISCOVERED').length;
    const sa = result.summary?.safe_abstention_count ?? allReqs.filter((r) => r.verification_tier === 'SAFE_ABSTENTION').length;
    return {
      clause_verified: cv,
      catalogue_discovered: cd,
      safe_abstention: sa,
      total: cv + cd + sa,
    };
  }, [result.summary, allReqs]);

  // 1. Recommended Standards: Only valid, grounded standards with clear decisions
  // Filtered by selected package
  const recommendedList = useMemo(() => filterRecommendedRequirements(displayedReqs), [displayedReqs]);

  // 2. Needs Attention: Missing parameters, ambiguity, review required, or safe abstentions
  // Filtered by selected package
  const attentionList = useMemo(() => filterAttentionRequirements(displayedReqs), [displayedReqs]);

  // 3. Standards That Need an Update: Superseded citations
  // Filtered by selected package
  const updateList = useMemo(() => {
    return displayedReqs.filter((req) => {
      return Boolean(
        req.superseded_citation ||
        (req.lifecycle_status && req.lifecycle_status.toLowerCase() === 'superseded') ||
        (req.successor_standard && req.successor_standard !== req.candidate_standard)
      );
    });
  }, [displayedReqs]);

  // 4. Related Standards (Graph): Kept strictly separate ("Related ≠ Applicable")
  // Filtered by selected package
  const relatedStandardsList = useMemo(() => {
    const list: Array<{ standard: RelatedStandard; parentStandard: string; parentReq: Requirement }> = [];
    const seen = new Set<string>();

    for (const req of displayedReqs) {
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
  }, [displayedReqs]);

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

  // Fetch existing review decisions for this tender
  useEffect(() => {
    let mounted = true;
    getReviewDecisions(tender.id)
      .then((res) => {
        if (mounted && res && res.decisions) {
          const map: Record<string, HumanReviewDecision> = {};
          res.decisions.forEach((d) => {
            map[d.requirement_id] = d;
          });
          setHumanDecisions(map);
          if (res.progress) {
            setServerProgress(res.progress);
          }
        }
      })
      .catch(() => {
        // Silently ignore if no review session cached yet
      });
    return () => {
      mounted = false;
    };
  }, [tender.id]);

  const handleSaveDecision = async (decision: HumanReviewDecision) => {
    const updated = {
      ...humanDecisions,
      [decision.requirement_id]: decision,
    };
    setHumanDecisions(updated);
    try {
      const resp = await submitReviewDecisions(tender.id, Object.values(updated));
      if (resp && resp.progress) {
        setServerProgress(resp.progress);
      }
    } catch (err) {
      console.warn('Failed to persist human decision to server:', err);
    }
  };

  // Review Progress Computation
  const reviewProgress = useMemo(() => {
    const allDecs = Object.values(humanDecisions);
    const acceptedCount = allDecs.filter((d) => d.decision === 'ACCEPT').length;
    const editedCount = allDecs.filter((d) => d.decision === 'EDIT').length;
    const dismissedCount = allDecs.filter((d) => d.decision === 'DISMISS').length;
    const reviewedCount = acceptedCount + editedCount + dismissedCount;

    const totalItems = attentionList.length > 0 ? attentionList.length : allReqs.length;
    const pendingCount = Math.max(0, totalItems - reviewedCount);

    let status: 'REVIEW_REQUIRED' | 'IN_PROGRESS' | 'REVIEW_COMPLETE' = 'REVIEW_REQUIRED';
    if (totalItems > 0 && reviewedCount >= totalItems) {
      status = 'REVIEW_COMPLETE';
    } else if (reviewedCount > 0) {
      status = 'IN_PROGRESS';
    }

    return (
      serverProgress || {
        total_review_items: totalItems,
        reviewed_count: reviewedCount,
        pending_count: pendingCount,
        accepted_count: acceptedCount,
        edited_count: editedCount,
        dismissed_count: dismissedCount,
        review_status: status,
      }
    );
  }, [humanDecisions, attentionList.length, allReqs.length, serverProgress]);

  const percentReviewed = useMemo(() => {
    if (!reviewProgress.total_review_items || reviewProgress.total_review_items === 0) return 100;
    return Math.min(100, Math.round((reviewProgress.reviewed_count / reviewProgress.total_review_items) * 100));
  }, [reviewProgress]);

  // Filtered attention list according to reviewFilterTab
  const filteredAttentionList = useMemo(() => {
    if (reviewFilterTab === 'all') return attentionList;
    return attentionList.filter((req) => {
      const dec = humanDecisions[req.id];
      const isReviewed = dec && dec.decision !== 'PENDING';
      return reviewFilterTab === 'reviewed' ? isReviewed : !isReviewed;
    });
  }, [attentionList, reviewFilterTab, humanDecisions]);

  const pendingAttentionCount = useMemo(() => {
    return attentionList.filter((req) => !humanDecisions[req.id] || humanDecisions[req.id].decision === 'PENDING').length;
  }, [attentionList, humanDecisions]);

  const reviewedAttentionCount = useMemo(() => {
    return attentionList.filter((req) => humanDecisions[req.id] && humanDecisions[req.id].decision !== 'PENDING').length;
  }, [attentionList, humanDecisions]);

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

        {/* 2b. Publication Readiness Banner — Direct rendering of backend TenderAuditEngine verdict */}
        <div className={`readiness-banner readiness-banner--${(result.readiness || 'review_required').toLowerCase()}`} style={{
          padding: '14px 20px',
          borderRadius: '10px',
          marginBottom: '20px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
          background: result.readiness === 'READY_FOR_REVIEW' ? '#f0fdf4' : result.readiness === 'INSUFFICIENT_EVIDENCE' ? '#fef2f2' : '#fffdf0',
          border: `1px solid ${result.readiness === 'READY_FOR_REVIEW' ? '#bbf7d0' : result.readiness === 'INSUFFICIENT_EVIDENCE' ? '#fecaca' : '#fed7aa'}`,
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{
                fontWeight: 800,
                fontSize: '0.82rem',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                color: result.readiness === 'READY_FOR_REVIEW' ? '#166534' : result.readiness === 'INSUFFICIENT_EVIDENCE' ? '#991b1b' : '#9a3412',
              }}>
                Publication Readiness:
              </span>
              <span style={{
                fontWeight: 700,
                fontSize: '0.85rem',
                padding: '2px 8px',
                borderRadius: '4px',
                background: result.readiness === 'READY_FOR_REVIEW' ? '#dcfce7' : result.readiness === 'INSUFFICIENT_EVIDENCE' ? '#fee2e2' : '#ffedd5',
                color: result.readiness === 'READY_FOR_REVIEW' ? '#15803d' : result.readiness === 'INSUFFICIENT_EVIDENCE' ? '#b91c1c' : '#c2410c',
              }}>
                {result.readiness === 'READY_FOR_REVIEW' ? 'READY FOR REVIEW' : result.readiness === 'INSUFFICIENT_EVIDENCE' ? 'INSUFFICIENT EVIDENCE' : 'REVIEW REQUIRED'}
              </span>
            </div>
            {result.readiness_reasons && result.readiness_reasons.length > 0 && (
              <ul style={{ margin: '6px 0 0 0', paddingLeft: '20px', fontSize: '0.82rem', color: '#475569' }}>
                {result.readiness_reasons.map((reason, idx) => (
                  <li key={idx}>{reason}</li>
                ))}
              </ul>
            )}
          </div>
          <span style={{ fontSize: '0.78rem', color: '#64748b', fontStyle: 'italic' }}>
            Authoritative audit verdict from TenderAuditEngine
          </span>
        </div>

        {/* 2c. Human Review & Decision Progress Workflow */}
        <section
          className="review-progress-card"
          aria-label="Human Review and Decision Progress"
          style={{
            background: '#ffffff',
            border: '1px solid #e2e8f0',
            borderRadius: '12px',
            padding: '16px 20px',
            marginBottom: '20px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.02)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px', flexWrap: 'wrap', gap: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ fontSize: '0.82rem', fontWeight: 800, color: '#1e293b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Human Review & Decision Workflow
              </span>
              <span
                style={{
                  fontWeight: 700,
                  fontSize: '0.78rem',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  background:
                    reviewProgress.review_status === 'REVIEW_COMPLETE'
                      ? '#dcfce7'
                      : reviewProgress.review_status === 'IN_PROGRESS'
                      ? '#dbeafe'
                      : '#fef3c7',
                  color:
                    reviewProgress.review_status === 'REVIEW_COMPLETE'
                      ? '#15803d'
                      : reviewProgress.review_status === 'IN_PROGRESS'
                      ? '#1d4ed8'
                      : '#b45309',
                }}
              >
                {reviewProgress.review_status === 'REVIEW_COMPLETE'
                  ? 'REVIEW COMPLETE'
                  : reviewProgress.review_status === 'IN_PROGRESS'
                  ? 'REVIEW IN PROGRESS'
                  : 'REVIEW REQUIRED'}
              </span>
            </div>
            <span style={{ fontSize: '0.82rem', fontWeight: 700, color: '#334155' }}>
              {reviewProgress.reviewed_count} / {reviewProgress.total_review_items} Reviewed ({percentReviewed}%)
            </span>
          </div>

          {/* Progress bar meter */}
          <div
            style={{
              height: '8px',
              background: '#f1f5f9',
              borderRadius: '999px',
              overflow: 'hidden',
              marginBottom: '14px',
              display: 'flex',
            }}
          >
            <div
              style={{
                width: `${percentReviewed}%`,
                background: reviewProgress.review_status === 'REVIEW_COMPLETE' ? '#16a34a' : '#2563eb',
                transition: 'width 250ms ease',
              }}
            />
          </div>

          {/* Stat pills breakdown */}
          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center' }}>
            <div style={{ fontSize: '0.78rem', background: '#fffbeb', border: '1px solid #fde68a', color: '#92400e', padding: '3px 10px', borderRadius: '6px', fontWeight: 600 }}>
              Pending: <strong>{reviewProgress.pending_count}</strong>
            </div>
            <div style={{ fontSize: '0.78rem', background: '#ecfdf5', border: '1px solid #a7f3d0', color: '#065f46', padding: '3px 10px', borderRadius: '6px', fontWeight: 600 }}>
              Accepted: <strong>{reviewProgress.accepted_count}</strong>
            </div>
            <div style={{ fontSize: '0.78rem', background: '#eff6ff', border: '1px solid #bfdbfe', color: '#1e40af', padding: '3px 10px', borderRadius: '6px', fontWeight: 600 }}>
              Edited: <strong>{reviewProgress.edited_count}</strong>
            </div>
            <div style={{ fontSize: '0.78rem', background: '#f8fafc', border: '1px solid #cbd5e1', color: '#475569', padding: '3px 10px', borderRadius: '6px', fontWeight: 600 }}>
              Dismissed: <strong>{reviewProgress.dismissed_count}</strong>
            </div>
            <span style={{ fontSize: '0.72rem', color: '#64748b', fontStyle: 'italic', marginLeft: 'auto' }}>
              "Review Complete" indicates all identified review items have received a decision.
            </span>
          </div>
        </section>

        {/* Verification Tiers Executive Summary (Phase 28) */}
        <div className="verification-tiers-bar" aria-label="Verification Tiers Summary">
          <div className="verification-tiers-header">
            <div>
              <span style={{ fontSize: '0.82rem', fontWeight: 800, color: '#1e293b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Verification Tier Distribution (Tender-Wide)
              </span>
              <span style={{ fontSize: '0.76rem', color: '#64748b', display: 'block', marginTop: '2px' }}>
                Audit evidence grounding classification across all evaluated requirements
              </span>
            </div>
            <span style={{ fontSize: '0.78rem', color: '#475569', fontWeight: 600 }}>
              {allReqs.length} Total Requirement{allReqs.length === 1 ? '' : 's'}
            </span>
          </div>
          <div className="verification-tiers-grid">
            <div className="verification-tier-card verification-tier-card--verified">
              <div className="verification-tier-card__count verification-tier-card__count--verified">
                {tierCounts.clause_verified}
              </div>
              <div className="verification-tier-card__label verification-tier-card__label--verified">
                ✓ Clause-Verified
              </div>
              <p className="verification-tier-card__desc">
                Supporting local normative evidence is available for the identified standard and edition.
              </p>
            </div>

            <div className="verification-tier-card verification-tier-card--catalogue">
              <div className="verification-tier-card__count verification-tier-card__count--catalogue">
                {tierCounts.catalogue_discovered}
              </div>
              <div className="verification-tier-card__label verification-tier-card__label--catalogue">
                🔍 Catalogue-Discovered
              </div>
              <p className="verification-tier-card__desc">
                Discovered in national catalogue metadata; technical evaluation remains pending.
              </p>
            </div>

            <div className="verification-tier-card verification-tier-card--abstain">
              <div className="verification-tier-card__count verification-tier-card__count--abstain">
                {tierCounts.safe_abstention}
              </div>
              <div className="verification-tier-card__label verification-tier-card__label--abstain">
                🛡️ Safe Abstentions
              </div>
              <p className="verification-tier-card__desc">
                Deliberately withheld because requirements are administrative, commercial, or non-engineering.
              </p>
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

        {/* Multi-Package Navigation (Phase 28) */}
        {packageSummaries.length > 0 && (
          <section className="package-nav-section" aria-label="Tender packages filter">
            <div className="package-nav-header">
              <div>
                <span className="package-nav-title">Package-Level Navigation</span>
                <span className="package-nav-subtitle" style={{ marginLeft: '8px' }}>
                  Filter requirements by procurement package
                </span>
              </div>
              <span style={{ fontSize: '0.76rem', color: '#64748b' }}>
                {packageSummaries.length} package{packageSummaries.length === 1 ? '' : 's'} detected
              </span>
            </div>

            <div className="package-tab-bar" role="tablist">
              <button
                type="button"
                role="tab"
                aria-selected={selectedPackage === 'ALL'}
                className={`package-tab ${selectedPackage === 'ALL' ? 'package-tab--active' : ''}`}
                onClick={() => setSelectedPackage('ALL')}
              >
                <span>🌐 All Packages</span>
                <span className="package-tab-count">{allReqs.length}</span>
              </button>

              {packageSummaries.map((pkg) => (
                <button
                  key={pkg.package_id}
                  type="button"
                  role="tab"
                  aria-selected={selectedPackage === pkg.package_id}
                  className={`package-tab ${selectedPackage === pkg.package_id ? 'package-tab--active' : ''}`}
                  onClick={() => setSelectedPackage(pkg.package_id)}
                >
                  <span>{pkg.is_general_conditions ? '📋' : '📦'} {pkg.package_name || pkg.package_id}</span>
                  <span className="package-tab-count">{pkg.requirement_count}</span>
                </button>
              ))}
            </div>

            {/* Selected Package Details Banner */}
            {activePackageSummary && (
              <div className="package-summary-banner">
                <div>
                  <h4 className="package-summary-title">
                    {activePackageSummary.is_general_conditions ? '📋 General & Commercial Conditions' : `📦 Package: ${activePackageSummary.package_name}`}
                  </h4>
                  <p className="package-summary-meta">
                    Domain: <strong>{activePackageSummary.domains.join(', ')}</strong> · Requirements: <strong>{activePackageSummary.requirement_count}</strong> · Active Standards: <strong>{activePackageSummary.standards.length}</strong>
                  </p>
                </div>
                <div className="package-tier-distribution">
                  <span className="package-tier-chip package-tier-chip--verified" title="Clause-verified in this package">
                    ✓ Verified: {activePackageSummary.clause_verified_count}
                  </span>
                  <span className="package-tier-chip package-tier-chip--catalogue" title="Catalogue-discovered in this package">
                    🔍 Catalogue: {activePackageSummary.catalogue_discovered_count}
                  </span>
                  <span className="package-tier-chip package-tier-chip--abstain" title="Safely abstained in this package">
                    🛡️ Abstained: {activePackageSummary.safe_abstention_count}
                  </span>
                </div>
              </div>
            )}
          </section>
        )}

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
                  currentDecision={humanDecisions[req.id]}
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

            {/* Filter Tabs for Review Queue */}
            <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', flexWrap: 'wrap' }}>
              <button
                type="button"
                onClick={() => setReviewFilterTab('all')}
                style={{
                  padding: '6px 14px',
                  borderRadius: '6px',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  background: reviewFilterTab === 'all' ? '#1e293b' : '#f1f5f9',
                  color: reviewFilterTab === 'all' ? '#ffffff' : '#475569',
                  border: 'none',
                  cursor: 'pointer',
                  transition: 'background 150ms ease',
                }}
              >
                All ({attentionList.length})
              </button>
              <button
                type="button"
                onClick={() => setReviewFilterTab('pending')}
                style={{
                  padding: '6px 14px',
                  borderRadius: '6px',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  background: reviewFilterTab === 'pending' ? '#d97706' : '#fef3c7',
                  color: reviewFilterTab === 'pending' ? '#ffffff' : '#92400e',
                  border: 'none',
                  cursor: 'pointer',
                  transition: 'background 150ms ease',
                }}
              >
                Pending Review ({pendingAttentionCount})
              </button>
              <button
                type="button"
                onClick={() => setReviewFilterTab('reviewed')}
                style={{
                  padding: '6px 14px',
                  borderRadius: '6px',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  background: reviewFilterTab === 'reviewed' ? '#16a34a' : '#dcfce7',
                  color: reviewFilterTab === 'reviewed' ? '#ffffff' : '#166534',
                  border: 'none',
                  cursor: 'pointer',
                  transition: 'background 150ms ease',
                }}
              >
                Reviewed ({reviewedAttentionCount})
              </button>
            </div>

            <div className="attention-list">
              {filteredAttentionList.length > 0 ? (
                filteredAttentionList.map((req, i) => (
                  <AttentionCard
                    key={req.id || i}
                    req={req}
                    onOpenEvidence={setActiveEvidenceReq}
                    currentDecision={humanDecisions[req.id]}
                  />
                ))
              ) : (
                <div style={{ padding: '20px', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0', textAlign: 'center', color: '#64748b', fontSize: '0.85rem' }}>
                  No items match the selected filter.
                </div>
              )}
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
                  currentDecision={humanDecisions[req.id]}
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

        {/* 6b. TENDER-WIDE FINDINGS: COMPLEMENTARY ENGINEERING SUITES (Phase 28) */}
        {result.summary?.complementary_standards && result.summary.complementary_standards.length > 0 && (
          <section className="tender-wide-card" aria-label="Complementary engineering standards suites">
            <div className="tender-wide-card__head">
              <div>
                <h3 className="tender-wide-card__title">COMPLEMENTARY ENGINEERING SUITES</h3>
                <p className="tender-wide-card__desc">
                  Engineering suites identified across multi-package requirements. These represent potential cross-discipline dependencies requiring technical review, not automatically mandatory additions.
                </p>
              </div>
              <span className="section-badge section-badge--neutral">
                {result.summary.complementary_standards.length} suite{result.summary.complementary_standards.length === 1 ? '' : 's'}
              </span>
            </div>

            <div className="complementary-suites-list">
              {result.summary.complementary_standards.map((suite, idx) => (
                <div key={idx} className="complementary-suite-item">
                  <div className="suite-title-row">
                    <span className="suite-name">{suite.suite_name}</span>
                    <span style={{ fontSize: '0.74rem', color: '#475569' }}>
                      Primary Trigger: <strong>{suite.primary_standard}</strong>
                    </span>
                  </div>
                  {suite.packages_involved && suite.packages_involved.length > 0 && (
                    <div style={{ fontSize: '0.76rem', color: '#475569', marginBottom: '6px' }}>
                      Applicable in Packages: {suite.packages_involved.join(', ')}
                    </div>
                  )}
                  {suite.allied_standards && suite.allied_standards.length > 0 && (
                    <div className="suite-allied-wrap">
                      {suite.allied_standards.map((allied, aIdx) => (
                        <span key={aIdx} className="suite-allied-badge" title={allied}>
                          <strong>{allied}</strong>
                        </span>
                      ))}
                    </div>
                  )}
                  <div style={{ fontSize: '0.74rem', color: '#64748b', fontStyle: 'italic', marginTop: '6px' }}>
                    Note: Cross-discipline advisory; inspect tender specifications to confirm whether these suites are required for site execution.
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* 6c. TENDER-WIDE FINDINGS: UNCOVERED TENDER DEPENDENCIES (Phase 28) */}
        {result.summary?.uncovered_tender_dependencies && result.summary.uncovered_tender_dependencies.length > 0 && (
          <section className="tender-wide-card" aria-label="Uncovered tender dependencies">
            <div className="tender-wide-card__head">
              <div>
                <h3 className="tender-wide-card__title">UNCOVERED TENDER DEPENDENCIES</h3>
                <p className="tender-wide-card__desc">
                  Identified tender-wide dependencies between primary specifications and allied codes of practice. Review for missing specification coverage.
                </p>
              </div>
              <span className="section-badge section-badge--warning">
                {result.summary.uncovered_tender_dependencies.length} dependenc{result.summary.uncovered_tender_dependencies.length === 1 ? 'y' : 'ies'}
              </span>
            </div>

            <div className="uncovered-deps-list">
              {result.summary.uncovered_tender_dependencies.map((dep, idx) => (
                <div key={idx} className="uncovered-dep-item">
                  <div className="uncovered-dep-title">
                    ⚠️ {dep.primary_standard} requires review of {dep.missing_dependency || 'Allied Standard'}
                  </div>
                  <p className="uncovered-dep-desc">
                    <strong>Missing Reference:</strong> {dep.missing_dependency}
                    {dep.dependency_title ? ` (${dep.dependency_title})` : ''}
                    {dep.domain ? ` · Domain: ${dep.domain}` : ''}
                  </p>
                  {dep.message && (
                    <p style={{ margin: '3px 0 0 0', fontSize: '0.78rem', color: '#78350f' }}>
                      {dep.message}
                    </p>
                  )}
                  <p style={{ margin: '4px 0 0 0', fontSize: '0.74rem', color: '#92400e', fontStyle: 'italic' }}>
                    Advisory note: Never legally or normatively mandatory unless verified by returned tender specifications or explicit contract condition.
                  </p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* 6d. TENDER-WIDE FINDINGS: SAFELY ABSTAINED CONDITIONS (Phase 28) */}
        {tierCounts.safe_abstention > 0 && (
          <section className="tender-wide-card" aria-label="Safely abstained administrative conditions">
            <div className="tender-wide-card__head">
              <div>
                <h3 className="tender-wide-card__title">ADMINISTRATIVE & COMMERCIAL CONDITIONS (SAFE ABSTENTIONS)</h3>
                <p className="tender-wide-card__desc">
                  The system safely withheld standard recommendations for non-engineering clauses ({tierCounts.safe_abstention} condition{tierCounts.safe_abstention === 1 ? '' : 's'}).
                </p>
              </div>
              <span className="rec-badge rec-badge--tier-abstain">
                {tierCounts.safe_abstention} Safely Abstained
              </span>
            </div>
            <p style={{ fontSize: '0.82rem', color: '#475569', lineHeight: '1.45', margin: 0 }}>
              Administrative provisions (such as Earnest Money Deposits, bidder turnover criteria, delivery schedules, liquidated damages, or warranty clauses) are commercial requirements outside the scope of Indian Standards product specifications. The absence of a recommendation is an intentional safety gate to prevent false attribution.
            </p>
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
          currentDecision={humanDecisions[activeEvidenceReq.id]}
          onSaveDecision={handleSaveDecision}
        />
      )}
    </div>
  );
}
