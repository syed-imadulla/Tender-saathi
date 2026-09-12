// Home.tsx — Unified AI-style landing page for TenderSaathi
// Consolidates Text, PDF, and Image into a single conversational input experience.
import { useState, useCallback } from 'react';
import './Home.css';
import Header from '../components/Header';
import UnifiedInput from '../components/UnifiedInput';
import HowItWorksModal from '../components/HowItWorksModal';
import AboutModal from '../components/AboutModal';
import ConnectionStatus from '../components/ConnectionStatus';
import { analyzeText, analyzePdf, analyzeSample, analyzeImages } from '../api';
import type { AnalysisResult, InputMode } from '../types';

interface HomeProps {
  onStartAnalysis: (promise: Promise<AnalysisResult>, mode: InputMode) => void;
  errorMessage: string | null;
}

const SAMPLES: Array<{ key: 'cpvc' | 'valve' | 'superseded'; label: string }> = [
  { key: 'cpvc', label: 'CPVC Pipes' },
  { key: 'valve', label: 'Valve Replacement' },
  { key: 'superseded', label: 'IS 10611 (Superseded)' },
];

export default function Home({ onStartAnalysis, errorMessage }: HomeProps) {
  const [isHowItWorksOpen, setIsHowItWorksOpen] = useState(false);
  const [isAboutOpen, setIsAboutOpen] = useState(false);

  // ── Analysis Submissions ──────────────────────────────────────────────
  const handleAnalyzeText = useCallback(
    (text: string) => {
      onStartAnalysis(analyzeText(text), 'text');
    },
    [onStartAnalysis]
  );

  const handleAnalyzePdf = useCallback(
    (file: File) => {
      onStartAnalysis(analyzePdf(file), 'pdf');
    },
    [onStartAnalysis]
  );

  const handleAnalyzeImages = useCallback(
    (files: File[]) => {
      onStartAnalysis(analyzeImages(files), 'image');
    },
    [onStartAnalysis]
  );

  const handleSampleClick = useCallback(
    (key: 'cpvc' | 'valve' | 'superseded') => {
      onStartAnalysis(analyzeSample(key), 'text');
    },
    [onStartAnalysis]
  );

  return (
    <div className="home-unified" id="home">
      <ConnectionStatus />

      <Header
        onOpenHowItWorks={() => setIsHowItWorksOpen(true)}
        onOpenAbout={() => setIsAboutOpen(true)}
      />

      <main className="home-unified__main" role="main">
        <div className="home-unified__hero">
          {/* Eyebrow badge */}
          <span className="home-unified__eyebrow">
            BIS STANDARDS DECISION SUPPORT
          </span>

          {/* Clean 2-line headline */}
          <h1 className="home-unified__title">
            Check your tender
            <span className="home-unified__title--accent">before you publish.</span>
          </h1>

          {/* Subtitle */}
          <p className="home-unified__subtitle">
            Evidence-backed Indian Standards validation for public procurement.
          </p>
        </div>

        {/* Global error if previous analysis failed */}
        {errorMessage && (
          <div className="home-unified__error-banner" role="alert">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Central Unified Input Bar */}
        <section className="home-unified__input-section" aria-label="Tender specification input">
          <UnifiedInput
            onAnalyzeText={handleAnalyzeText}
            onAnalyzePdf={handleAnalyzePdf}
            onAnalyzeImages={handleAnalyzeImages}
          />
        </section>

        {/* Action triggers & Sample shortcuts */}
        <div className="home-unified__footer-actions">
          {/* Sample pills */}
          <div className="home-unified__samples" aria-label="Quick sample tenders">
            <span className="samples-label">Try a sample:</span>
            {SAMPLES.map(({ key, label }) => (
              <button
                key={key}
                type="button"
                className="sample-pill-btn"
                onClick={() => handleSampleClick(key)}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Modals trigger buttons */}
          <div className="home-unified__action-buttons">
            <button
              type="button"
              className="action-link-btn"
              onClick={() => setIsHowItWorksOpen(true)}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <circle cx="12" cy="12" r="3" />
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
              </svg>
              How it works
            </button>
            <span className="action-divider" aria-hidden="true" />
            <button
              type="button"
              className="action-link-btn"
              onClick={() => setIsAboutOpen(true)}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
              </svg>
              About
            </button>
          </div>
        </div>
      </main>

      {/* Subdued Minimal Legal Notice */}
      <footer className="home-unified__disclaimer">
        <p>
          TenderSaathi is an evidence-backed standards review aid. It does not replace statutory authority certification.
        </p>
      </footer>

      {/* Modals */}
      <HowItWorksModal
        isOpen={isHowItWorksOpen}
        onClose={() => setIsHowItWorksOpen(false)}
      />

      <AboutModal
        isOpen={isAboutOpen}
        onClose={() => setIsAboutOpen(false)}
      />
    </div>
  );
}
