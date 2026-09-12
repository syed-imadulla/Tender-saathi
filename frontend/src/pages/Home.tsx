// Home.tsx — Landing / Upload page with Text · PDF · Image tab switcher
// All existing Text + PDF logic is preserved unchanged.
// Image upload is an additive extension.
import { useRef, useState, useCallback } from 'react';
import './Home.css';
import Header from '../components/Header';
import ImageUpload, { type UploadedImage } from '../components/ImageUpload';
import ConnectionStatus from '../components/ConnectionStatus';
import { analyzeText, analyzePdf, analyzeSample, analyzeImages } from '../api';
import type { AnalysisResult, InputMode } from '../types';

interface HomeProps {
  onStartAnalysis: (promise: Promise<AnalysisResult>, mode: InputMode) => void;
  errorMessage: string | null;
}

const SAMPLE_LABELS: Record<'cpvc' | 'valve' | 'superseded', string> = {
  cpvc: 'CPVC Pipes',
  valve: 'Valve Replacement',
  superseded: 'IS 10611 (Superseded)',
};

const MAX_SIZE_BYTES = 25 * 1024 * 1024;

export default function Home({ onStartAnalysis, errorMessage }: HomeProps) {
  const [mode, setMode] = useState<InputMode>('text');
  const [text, setText] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const [images, setImages] = useState<UploadedImage[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── Text mode ────────────────────────────────────────────────────────
  const handleTextSubmit = useCallback(() => {
    const trimmed = text.trim();
    if (!trimmed) return;
    onStartAnalysis(analyzeText(trimmed), 'text');
  }, [text, onStartAnalysis]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleTextSubmit();
    }
  }, [handleTextSubmit]);

  // ── PDF mode ─────────────────────────────────────────────────────────
  const handleFile = useCallback((file: File) => {
    if (!file.name.match(/\.(pdf|docx)$/i)) {
      alert('Unsupported file type. Please upload a PDF or DOCX file.');
      return;
    }
    if (file.size > MAX_SIZE_BYTES) {
      alert('File too large. Maximum size is 25 MB.');
      return;
    }
    onStartAnalysis(analyzePdf(file), 'pdf');
  }, [onStartAnalysis]);

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

  // ── Image mode ───────────────────────────────────────────────────────
  const handleImageAnalyze = useCallback(() => {
    if (images.length === 0) return;
    const files = images.map((img) => img.file);
    onStartAnalysis(analyzeImages(files), 'image');
  }, [images, onStartAnalysis]);

  // ── Samples ──────────────────────────────────────────────────────────
  const handleSample = useCallback((demo: 'cpvc' | 'valve' | 'superseded') => {
    onStartAnalysis(analyzeSample(demo), 'text');
  }, [onStartAnalysis]);

  return (
    <div className="home" id="home">
      <ConnectionStatus />
      <Header />

      <main className="home__hero" role="main">
        <p className="home__eyebrow">INDIAN STANDARDS FOR BETTER PROCUREMENT</p>

        <h1 className="home__headline">
          Check your tender
          <span className="home__headline--accent">before you publish.</span>
        </h1>

        <p className="home__subtext">
          Upload your tender or type a requirement and TenderSaathi will find relevant
          Indian Standards, check outdated references, and show what needs your review.
        </p>

        {/* Input mode tabs */}
        <div className="home__tabs" role="tablist" aria-label="Input mode">
          {(['text', 'pdf', 'image'] as InputMode[]).map((m) => (
            <button
              key={m}
              role="tab"
              aria-selected={mode === m}
              className={`home__tab${mode === m ? ' home__tab--active' : ''}`}
              onClick={() => setMode(m)}
              type="button"
            >
              {m === 'text' && (
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <line x1="17" y1="10" x2="3" y2="10" /><line x1="21" y1="6" x2="3" y2="6" /><line x1="21" y1="14" x2="3" y2="14" /><line x1="17" y1="18" x2="3" y2="18" />
                </svg>
              )}
              {m === 'pdf' && (
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" />
                </svg>
              )}
              {m === 'image' && (
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <rect x="3" y="3" width="18" height="18" rx="2" /><circle cx="8.5" cy="8.5" r="1.5" /><polyline points="21 15 16 10 5 21" />
                </svg>
              )}
              {m === 'text' ? 'Text' : m === 'pdf' ? 'PDF' : 'Image'}
            </button>
          ))}
        </div>

        {/* ── Tab panels ───────────────────────────────────────────────── */}

        {/* TEXT panel */}
        {mode === 'text' && (
          <div className="home__upload-wrap" role="tabpanel" aria-label="Text input">
            <div
              className="home__upload-bar"
              role="region"
              aria-label="Type a requirement"
            >
              <textarea
                className="home__input"
                id="requirement-input"
                placeholder="Type a procurement requirement..."
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={handleKeyDown}
                rows={1}
                aria-label="Type a procurement requirement"
                style={{ resize: 'none', overflow: 'hidden' }}
                onInput={(e) => {
                  const t = e.currentTarget;
                  t.style.height = 'auto';
                  t.style.height = Math.min(t.scrollHeight, 120) + 'px';
                }}
              />
              <button
                className="home__submit-btn"
                type="button"
                aria-label="Analyze requirement"
                onClick={handleTextSubmit}
                disabled={!text.trim()}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <line x1="12" y1="19" x2="12" y2="5" /><polyline points="5 12 12 5 19 12" />
                </svg>
              </button>
            </div>
            <p className="home__hint">
              <span>Press Enter to analyze</span>
              <span className="home__hint-sep">·</span>
              <span>Up to 10,000 characters</span>
            </p>
            {errorMessage && (
              <div className="home__error" role="alert">{errorMessage}</div>
            )}
          </div>
        )}

        {/* PDF panel */}
        {mode === 'pdf' && (
          <div className="home__upload-wrap" role="tabpanel" aria-label="PDF upload">
            <div
              className={`home__upload-bar home__upload-bar--pdf${dragOver ? ' home__upload-bar--drag' : ''}`}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              role="region"
              aria-label="Upload PDF"
            >
              <button
                className="home__attach-btn"
                type="button"
                aria-label="Attach PDF or DOCX"
                onClick={() => fileInputRef.current?.click()}
              >
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" />
                </svg>
              </button>
              <span className="home__pdf-hint">
                Drag &amp; drop a PDF or{' '}
                <button
                  type="button"
                  className="home__pdf-browse"
                  onClick={() => fileInputRef.current?.click()}
                >
                  browse
                </button>
              </span>
            </div>
            <p className="home__hint">
              <span>PDF, DOCX</span>
              <span className="home__hint-sep">·</span>
              <span>Up to 25 MB</span>
            </p>
            {errorMessage && (
              <div className="home__error" role="alert">{errorMessage}</div>
            )}
            {/* Hidden PDF file input */}
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx"
              className="home__file-input"
              onChange={handleFileChange}
              aria-hidden="true"
            />
          </div>
        )}

        {/* IMAGE panel */}
        {mode === 'image' && (
          <div className="home__upload-wrap" role="tabpanel" aria-label="Image upload">
            <ImageUpload
              images={images}
              onChange={setImages}
              maxImages={5}
              maxSizeMb={10}
            />
            {images.length > 0 && (
              <button
                className="home__image-analyze-btn"
                type="button"
                onClick={handleImageAnalyze}
              >
                Analyze {images.length} image{images.length > 1 ? 's' : ''}
              </button>
            )}
            {errorMessage && (
              <div className="home__error" role="alert">{errorMessage}</div>
            )}
          </div>
        )}

        {/* Samples — always visible */}
        <div className="home__samples" aria-label="Try a sample analysis">
          <span className="home__sample-label">Try a sample:</span>
          {(['cpvc', 'valve', 'superseded'] as const).map((key) => (
            <button
              key={key}
              className="home__sample-btn"
              type="button"
              onClick={() => handleSample(key)}
            >
              {SAMPLE_LABELS[key]}
            </button>
          ))}
        </div>
      </main>

      <footer className="home__footer">
        <p>
          TenderSaathi is a standards-review aid. It does not constitute legal compliance certification.
          &nbsp;·&nbsp;SIH 2026 PS SIH26108
        </p>
      </footer>
    </div>
  );
}
