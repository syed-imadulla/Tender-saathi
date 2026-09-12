// HowItWorksModal.tsx — Explains the real 8-step TenderSaathi analysis pipeline
import { useEffect, useRef } from 'react';
import './HowItWorksModal.css';

interface HowItWorksModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface PipelineStep {
  number: number;
  title: string;
  desc: string;
  icon: JSX.Element;
}

const PIPELINE_STEPS: PipelineStep[] = [
  {
    number: 1,
    title: 'Read document',
    desc: 'We extract text from your tender, PDF, or scanned image.',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
        <polyline points="10 9 9 9 8 9" />
      </svg>
    ),
  },
  {
    number: 2,
    title: 'Understand requirements',
    desc: 'We break the tender into meaningful technical requirements.',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="16" x2="12" y2="12" />
        <line x1="12" y1="8" x2="12.01" y2="8" />
      </svg>
    ),
  },
  {
    number: 3,
    title: 'Find Indian Standards',
    desc: 'We search the available standards catalogue using lexical and semantic retrieval.',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <circle cx="11" cy="11" r="8" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
      </svg>
    ),
  },
  {
    number: 4,
    title: 'Check applicability',
    desc: 'We reject candidates that conflict with the product or technical context.',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      </svg>
    ),
  },
  {
    number: 5,
    title: 'Verify evidence',
    desc: 'Recommendations are tied to available authoritative evidence.',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M9 11l3 3L22 4" />
        <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
      </svg>
    ),
  },
  {
    number: 6,
    title: 'Check dependencies',
    desc: 'We identify relevant testing, installation, safety, code-of-practice and allied relationships.',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <circle cx="18" cy="5" r="3" />
        <circle cx="6" cy="12" r="3" />
        <circle cx="18" cy="19" r="3" />
        <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
        <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
      </svg>
    ),
  },
  {
    number: 7,
    title: 'Check lifecycle',
    desc: 'We identify known superseded, withdrawn or review-required standards.',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <circle cx="12" cy="12" r="10" />
        <polyline points="12 6 12 12 16 14" />
      </svg>
    ),
  },
  {
    number: 8,
    title: 'Human review',
    desc: 'Uncertain or conflicting cases are surfaced instead of being silently accepted.',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
      </svg>
    ),
  },
];

export default function HowItWorksModal({ isOpen, onClose }: HowItWorksModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    // Prevent body background scrolling when modal is open
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
        className="how-it-works-modal"
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="how-it-works-title"
      >
        <header className="how-it-works-modal__header">
          <div>
            <span className="how-it-works-modal__badge">PIPELINE ARCHITECTURE</span>
            <h2 id="how-it-works-title" className="how-it-works-modal__title">
              How TenderSaathi Works
            </h2>
            <p className="how-it-works-modal__subtitle">
              An evidence-backed standards review and decision-support pipeline for public procurement.
            </p>
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

        <div className="how-it-works-modal__body">
          {/* Top pipeline indicator */}
          <div className="pipeline-flow-pill">
            <span>YOUR TENDER</span>
            <span className="pipeline-flow-arrow">→</span>
            <span>8-STAGE RIGOROUS AUDIT</span>
            <span className="pipeline-flow-arrow">→</span>
            <span>TENDER READINESS</span>
          </div>

          {/* 8 Steps */}
          <div className="how-it-works-modal__grid" role="list">
            {PIPELINE_STEPS.map((step) => (
              <div key={step.number} className="pipeline-step-card" role="listitem">
                <div className="pipeline-step-card__header">
                  <div className="pipeline-step-card__icon-wrap">
                    {step.icon}
                  </div>
                  <span className="pipeline-step-card__num">0{step.number}</span>
                </div>
                <h3 className="pipeline-step-card__title">{step.title}</h3>
                <p className="pipeline-step-card__desc">{step.desc}</p>
              </div>
            ))}
          </div>

          {/* Philosophy Banner */}
          <div className="decision-safety-banner">
            <p className="decision-safety-banner__eyebrow">DECISION SAFETY CORE</p>
            <div className="decision-safety-banner__pillars">
              <span className="pillar-item">AI interprets.</span>
              <span className="pillar-dot">·</span>
              <span className="pillar-item">Rules validate.</span>
              <span className="pillar-dot">·</span>
              <span className="pillar-item">Evidence supports.</span>
              <span className="pillar-dot">·</span>
              <span className="pillar-item pillar-item--accent">Humans decide.</span>
            </div>
            <p className="decision-safety-banner__note">
              TenderSaathi is built for decision support with safe abstention and transparent audit trails — never autonomous compliance sign-off.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
