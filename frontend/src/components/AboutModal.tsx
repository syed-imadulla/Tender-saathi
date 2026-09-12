// AboutModal.tsx — Explains TenderSaathi mission, methodology, and prototype scope
import { useEffect, useRef } from 'react';
import './AboutModal.css';

interface AboutModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface ScopeMetric {
  value: string;
  label: string;
}

const SCOPE_METRICS: ScopeMetric[] = [
  { value: '502', label: 'Catalogue records' },
  { value: '90', label: 'Core standards' },
  { value: '20', label: 'Govt tender PDFs tested' },
  { value: '40', label: 'Multilingual benchmarks' },
  { value: '319/319', label: 'Validation tests passing' },
];

export default function AboutModal({ isOpen, onClose }: AboutModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    document.body.style.overflow = 'hidden';

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="modal-overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      role="presentation"
    >
      <div
        className="about-modal"
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="about-modal-title"
      >
        <header className="about-modal__header">
          <div>
            <span className="about-modal__badge">PROCUREMENT DECISION SUPPORT</span>
            <h2 id="about-modal-title" className="about-modal__title">
              About TenderSaathi
            </h2>
          </div>
          <button
            type="button"
            className="modal-close-btn"
            onClick={onClose}
            aria-label="Close dialog"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </header>

        <div className="about-modal__body">
          {/* Mission summary */}
          <section className="about-modal__section">
            <p className="about-modal__lead">
              TenderSaathi helps procurement teams review tender specifications before publication. It identifies potentially relevant Indian Standards, checks applicability, examines lifecycle and related dependencies, and shows the evidence behind every finding.
            </p>
          </section>

          {/* Core Differentiation / USP */}
          <section className="about-modal__usp-box">
            <h3 className="about-modal__usp-quote">
              “We don’t just recommend standards.<br />
              We audit the tender against the standards it should contain.”
            </h3>
            <p className="about-modal__usp-sub">
              Every finding is anchored in verified BIS evidence. Uncertainty is surfaced openly, and unsupported conclusions are deliberately abstained from.
            </p>
          </section>

          {/* Philosophy Banner */}
          <div className="about-modal__pillars">
            <div className="pillar-item">AI interprets.</div>
            <div className="pillar-dot">·</div>
            <div className="pillar-item">Rules validate.</div>
            <div className="pillar-dot">·</div>
            <div className="pillar-item">Evidence supports.</div>
            <div className="pillar-dot">·</div>
            <div className="pillar-item pillar-item--accent">Humans decide.</div>
          </div>

          {/* Prototype Scope Metrics */}
          <section className="about-modal__scope">
            <div className="about-modal__scope-header">
              <span className="about-modal__scope-title">CURRENT VERIFIED PROTOTYPE SCOPE</span>
              <span className="about-modal__scope-tag">SIH 2026</span>
            </div>
            <div className="about-modal__metrics-grid">
              {SCOPE_METRICS.map((metric) => (
                <div key={metric.label} className="metric-box">
                  <span className="metric-box__value">{metric.value}</span>
                  <span className="metric-box__label">{metric.label}</span>
                </div>
              ))}
            </div>
            <p className="about-modal__disclaimer">
              TenderSaathi is a standards-review aid designed for pre-publication checks. It does not replace statutory authority approval or certify autonomous compliance.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
