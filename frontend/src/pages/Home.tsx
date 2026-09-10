// Home.tsx — Landing / Upload page (State 1)
import { useRef, useState, useCallback } from 'react';
import './Home.css';
import Header from '../components/Header';
import { analyzeText, analyzePdf, analyzeSample } from '../api';
import type { AnalysisResult } from '../types';

interface HomeProps {
  onStartAnalyzing: () => void;
  onDone: (result: AnalysisResult) => void;
  onError: (message: string) => void;
  errorMessage: string | null;
}

const SAMPLE_LABELS = {
  cpvc: 'CPVC Pipes',
  valve: 'Valve Replacement',
  superseded: 'IS 10611 (Superseded)',
} as const;

const MAX_SIZE_BYTES = 25 * 1024 * 1024;

export default function Home({ onStartAnalyzing, onDone, onError, errorMessage }: HomeProps) {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Store pending file/text to pass to Analyzing state
  const pendingRef = useRef<
    { type: 'text'; value: string } | { type: 'file'; value: File } | { type: 'sample'; value: string } | null
  >(null);

  const runAnalysis = useCallback(async () => {
    setLoading(true);
    onStartAnalyzing();

    // Slight delay so UI transitions to Analyzing state
    await new Promise((r) => setTimeout(r, 300));

    try {
      let result: AnalysisResult;
      const p = pendingRef.current;
      if (!p) throw new Error('No input provided.');

      if (p.type === 'text') {
        result = await analyzeText(p.value);
      } else if (p.type === 'file') {
        result = await analyzePdf(p.value);
      } else {
        result = await analyzeSample(p.value as 'cpvc' | 'valve' | 'superseded');
      }

      onDone(result);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Analysis failed. Please try again.';
      onError(msg);
    } finally {
      setLoading(false);
    }
  }, [onStartAnalyzing, onDone, onError]);

  const handleTextSubmit = useCallback(() => {
    const trimmed = text.trim();
    if (!trimmed) return;
    pendingRef.current = { type: 'text', value: trimmed };
    runAnalysis();
  }, [text, runAnalysis]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleTextSubmit();
    }
  }, [handleTextSubmit]);

  const handleFile = useCallback((file: File) => {
    if (!file.name.match(/\.(pdf|docx)$/i)) {
      onError('Unsupported file type. Please upload a PDF or DOCX file.');
      return;
    }
    if (file.size > MAX_SIZE_BYTES) {
      onError('File too large. Maximum size is 25 MB.');
      return;
    }
    pendingRef.current = { type: 'file', value: file };
    runAnalysis();
  }, [runAnalysis, onError]);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const handleSample = useCallback((demo: string) => {
    pendingRef.current = { type: 'sample', value: demo };
    runAnalysis();
  }, [runAnalysis]);

  return (
    <div className="home" id="home">
      <Header />

      <main className="home__hero" role="main">
        <p className="home__eyebrow">Indian Standards for Better Procurement</p>

        <h1 className="home__headline">
          Check your tender
          <span className="home__headline--accent">before you publish.</span>
        </h1>

        <p className="home__subtext">
          Upload your tender or type a requirement and TenderSaathi will find relevant
          Indian Standards, check outdated references, and show what needs your review.
        </p>

        {/* Upload / Input bar */}
        <div className="home__upload-wrap">
          <div
            className={`home__upload-bar${loading ? ' home__upload-bar--loading' : ''}${dragOver ? ' home__upload-bar--drag' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            role="region"
            aria-label="Upload or type requirement"
          >
            {/* Attach button */}
            <button
              className="home__attach-btn"
              type="button"
              aria-label="Attach PDF or DOCX"
              onClick={() => fileInputRef.current?.click()}
              disabled={loading}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" />
              </svg>
            </button>

            {/* Text input */}
            <textarea
              className="home__input"
              id="requirement-input"
              placeholder="Upload a tender (PDF, DOCX) or type a requirement..."
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
              disabled={loading}
              aria-label="Type a procurement requirement or upload a tender document"
              style={{ resize: 'none', overflow: 'hidden' }}
              onInput={(e) => {
                const t = e.currentTarget;
                t.style.height = 'auto';
                t.style.height = Math.min(t.scrollHeight, 120) + 'px';
              }}
            />

            {/* Submit */}
            <button
              className="home__submit-btn"
              type="button"
              aria-label="Submit requirement for analysis"
              onClick={handleTextSubmit}
              disabled={loading || !text.trim()}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="12" y1="19" x2="12" y2="5" />
                <polyline points="5 12 12 5 19 12" />
              </svg>
            </button>
          </div>

          {/* Hint */}
          <p className="home__hint">
            <span>PDF, DOCX</span>
            <span className="home__hint-sep">·</span>
            <span>Up to 25 MB</span>
          </p>

          {/* Error */}
          {errorMessage && (
            <div className="home__error" role="alert">
              {errorMessage}
            </div>
          )}
        </div>

        {/* Samples */}
        <div className="home__samples" aria-label="Try a sample analysis">
          <span className="home__sample-label">Try a sample:</span>
          {Object.entries(SAMPLE_LABELS).map(([key, label]) => (
            <button
              key={key}
              className="home__sample-btn"
              type="button"
              onClick={() => handleSample(key)}
              disabled={loading}
            >
              {label}
            </button>
          ))}
        </div>
      </main>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx"
        className="home__file-input"
        onChange={handleFileChange}
        aria-hidden="true"
      />

      <footer className="home__footer">
        <p>
          TenderSaathi is a standards-review aid. It does not constitute legal compliance certification.
          &nbsp;·&nbsp;SIH 2026 PS SIH26108
        </p>
      </footer>
    </div>
  );
}
