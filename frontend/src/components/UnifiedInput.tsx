// UnifiedInput.tsx — Single unified AI-style input bar for TenderSaathi
// Supports Text typing, PDF upload, Image/Photos upload, and Camera capture.
import { useState, useRef, useEffect, useCallback, type KeyboardEvent } from 'react';
import './UnifiedInput.css';

export interface UploadedImage {
  id: string;
  file: File;
  previewUrl: string;
}

interface UnifiedInputProps {
  onAnalyzeText: (text: string) => void;
  onAnalyzePdf: (file: File) => void;
  onAnalyzeImages: (files: File[]) => void;
  disabled?: boolean;
}

const MAX_PDF_BYTES = 25 * 1024 * 1024; // 25 MB
const MAX_IMG_BYTES = 10 * 1024 * 1024; // 10 MB per image
const MAX_IMAGES = 5;

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function UnifiedInput({
  onAnalyzeText,
  onAnalyzePdf,
  onAnalyzeImages,
  disabled = false,
}: UnifiedInputProps) {
  const [text, setText] = useState('');
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [images, setImages] = useState<UploadedImage[]>([]);
  const [isPlusMenuOpen, setIsPlusMenuOpen] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [inputError, setInputError] = useState<string | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const plusMenuRef = useRef<HTMLDivElement>(null);
  const plusButtonRef = useRef<HTMLButtonElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const pdfInputRef = useRef<HTMLInputElement>(null);
  const imagesInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  // Close plus menu on outside click or Escape
  useEffect(() => {
    if (!isPlusMenuOpen) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (
        plusMenuRef.current &&
        !plusMenuRef.current.contains(e.target as Node) &&
        plusButtonRef.current &&
        !plusButtonRef.current.contains(e.target as Node)
      ) {
        setIsPlusMenuOpen(false);
      }
    };

    const handleKeyDown = (e: globalThis.KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsPlusMenuOpen(false);
        plusButtonRef.current?.focus();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isPlusMenuOpen]);

  // Clean up object URLs on unmount
  useEffect(() => {
    return () => {
      images.forEach((img) => URL.revokeObjectURL(img.previewUrl));
    };
  }, [images]);

  // ── Handlers ─────────────────────────────────────────────────────────

  const handlePdfSelected = (file: File) => {
    if (!file.name.match(/\.(pdf|docx)$/i)) {
      setInputError('Please select a valid PDF or DOCX file.');
      return;
    }
    if (file.size > MAX_PDF_BYTES) {
      setInputError(`File exceeds maximum size of 25 MB (${formatBytes(file.size)}).`);
      return;
    }

    // Clear previous images if attaching PDF
    images.forEach((img) => URL.revokeObjectURL(img.previewUrl));
    setImages([]);
    setPdfFile(file);
    setInputError(null);
    setIsPlusMenuOpen(false);
  };

  const handleImagesSelected = (fileList: FileList | File[]) => {
    const rawFiles = Array.from(fileList);
    const valid: UploadedImage[] = [];
    let err: string | null = null;

    const availableSlots = MAX_IMAGES - images.length;
    if (availableSlots <= 0) {
      setInputError(`Maximum of ${MAX_IMAGES} images reached.`);
      return;
    }

    const toProcess = rawFiles.slice(0, availableSlots);

    for (const f of toProcess) {
      if (!f.type.startsWith('image/')) {
        err = `"${f.name}" is not an image. Supported formats: PNG, JPG, WEBP.`;
        continue;
      }
      if (f.size > MAX_IMG_BYTES) {
        err = `"${f.name}" exceeds 10 MB limit (${formatBytes(f.size)}).`;
        continue;
      }
      valid.push({
        id: `${f.name}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
        file: f,
        previewUrl: URL.createObjectURL(f),
      });
    }

    if (valid.length > 0) {
      setPdfFile(null); // Clear PDF if adding images
      setImages((prev) => [...prev, ...valid]);
    }
    if (err) {
      setInputError(err);
    } else {
      setInputError(null);
    }
    setIsPlusMenuOpen(false);
  };

  const removePdf = () => {
    setPdfFile(null);
    setInputError(null);
  };

  const removeImage = (id: string) => {
    setImages((prev) => {
      const target = prev.find((img) => img.id === id);
      if (target) URL.revokeObjectURL(target.previewUrl);
      return prev.filter((img) => img.id !== id);
    });
  };

  const moveImage = (index: number, direction: 'left' | 'right') => {
    setImages((prev) => {
      const next = [...prev];
      const targetIndex = direction === 'left' ? index - 1 : index + 1;
      if (targetIndex < 0 || targetIndex >= next.length) return prev;
      const temp = next[index];
      next[index] = next[targetIndex];
      next[targetIndex] = temp;
      return next;
    });
  };

  // ── Drag & Drop ───────────────────────────────────────────────────────
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    if (!containerRef.current?.contains(e.relatedTarget as Node)) {
      setDragOver(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const files = e.dataTransfer.files;
    if (!files || files.length === 0) return;

    const first = files[0];
    if (first.name.match(/\.(pdf|docx)$/i)) {
      handlePdfSelected(first);
    } else if (first.type.startsWith('image/')) {
      handleImagesSelected(files);
    } else {
      setInputError('Unsupported file type. Please drop a PDF document or image file.');
    }
  };

  // ── Submit logic ──────────────────────────────────────────────────────
  const canSubmit = Boolean(
    !disabled && (pdfFile || images.length > 0 || text.trim().length > 0)
  );

  const handleSubmit = useCallback(() => {
    if (!canSubmit) return;

    if (pdfFile) {
      onAnalyzePdf(pdfFile);
    } else if (images.length > 0) {
      onAnalyzeImages(images.map((img) => img.file));
    } else if (text.trim()) {
      onAnalyzeText(text.trim());
    }
  }, [canSubmit, pdfFile, images, text, onAnalyzePdf, onAnalyzeImages, onAnalyzeText]);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const autoResizeTextarea = (el: HTMLTextAreaElement) => {
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
  };

  const hasAttachments = Boolean(pdfFile || images.length > 0);

  return (
    <div className="unified-input-wrapper">
      <div
        ref={containerRef}
        className={`unified-input-container${
          hasAttachments ? ' unified-input-container--has-attachments' : ''
        }${dragOver ? ' unified-input-container--dragover' : ''}${
          disabled ? ' unified-input-container--disabled' : ''
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        role="region"
        aria-label="Tender specification input"
      >
        {/* Attachments Area (inside input bar) */}
        {hasAttachments && (
          <div className="unified-input__attachments">
            {/* PDF Attachment Pill */}
            {pdfFile && (
              <div className="attachment-chip attachment-chip--pdf">
                <span className="attachment-chip__icon" aria-hidden="true">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                    <line x1="16" y1="13" x2="8" y2="13" />
                    <line x1="16" y1="17" x2="8" y2="17" />
                  </svg>
                </span>
                <div className="attachment-chip__info">
                  <span className="attachment-chip__name" title={pdfFile.name}>
                    {pdfFile.name}
                  </span>
                  <span className="attachment-chip__size">
                    {formatBytes(pdfFile.size)} · PDF Ready
                  </span>
                </div>
                <button
                  type="button"
                  className="attachment-chip__remove"
                  onClick={removePdf}
                  aria-label="Remove attached PDF"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              </div>
            )}

            {/* Images Attachment List */}
            {images.length > 0 && (
              <div className="attachment-images-row">
                {images.map((img, idx) => (
                  <div key={img.id} className="image-thumb-card">
                    <img
                      src={img.previewUrl}
                      alt={`Attached page ${idx + 1}`}
                      className="image-thumb-card__preview"
                    />
                    <div className="image-thumb-card__overlay">
                      {idx > 0 && (
                        <button
                          type="button"
                          className="image-thumb-btn"
                          onClick={() => moveImage(idx, 'left')}
                          aria-label="Move left"
                          title="Move left"
                        >
                          ‹
                        </button>
                      )}
                      <button
                        type="button"
                        className="image-thumb-btn image-thumb-btn--delete"
                        onClick={() => removeImage(img.id)}
                        aria-label={`Remove image ${idx + 1}`}
                        title="Remove"
                      >
                        ×
                      </button>
                      {idx < images.length - 1 && (
                        <button
                          type="button"
                          className="image-thumb-btn"
                          onClick={() => moveImage(idx, 'right')}
                          aria-label="Move right"
                          title="Move right"
                        >
                          ›
                        </button>
                      )}
                    </div>
                  </div>
                ))}

                {images.length < MAX_IMAGES && (
                  <button
                    type="button"
                    className="image-thumb-add-btn"
                    onClick={() => imagesInputRef.current?.click()}
                    aria-label="Add another image"
                    title="Add another image"
                  >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="12" y1="5" x2="12" y2="19" />
                      <line x1="5" y1="12" x2="19" y2="12" />
                    </svg>
                    <span>Add</span>
                  </button>
                )}

                <span className="attachment-images__badge">
                  OCR-assisted ({images.length}/{MAX_IMAGES})
                </span>
              </div>
            )}
          </div>
        )}

        {/* Primary Input Line */}
        <div className="unified-input__main-row">
          {/* Plus / Attach Button */}
          <div className="unified-input__plus-wrapper">
            <button
              ref={plusButtonRef}
              type="button"
              className={`unified-input__plus-btn${isPlusMenuOpen ? ' unified-input__plus-btn--active' : ''}`}
              onClick={() => setIsPlusMenuOpen((prev) => !prev)}
              aria-label="Attach documents or photos"
              aria-haspopup="menu"
              aria-expanded={isPlusMenuOpen}
              disabled={disabled}
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.4"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="plus-icon"
              >
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
            </button>

            {/* Plus Popover Menu */}
            {isPlusMenuOpen && (
              <div
                ref={plusMenuRef}
                className="plus-menu-popover"
                role="menu"
                aria-label="Upload document options"
              >
                <button
                  type="button"
                  className="plus-menu-item"
                  role="menuitem"
                  onClick={() => {
                    pdfInputRef.current?.click();
                  }}
                >
                  <span className="plus-menu-icon" aria-hidden="true">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                      <polyline points="14 2 14 8 20 8" />
                      <line x1="16" y1="13" x2="8" y2="13" />
                      <line x1="16" y1="17" x2="8" y2="17" />
                    </svg>
                  </span>
                  <div className="plus-menu-text">
                    <span className="plus-menu-title">Upload PDF</span>
                    <span className="plus-menu-desc">Tender documents, NITs, specs</span>
                  </div>
                </button>

                <button
                  type="button"
                  className="plus-menu-item"
                  role="menuitem"
                  onClick={() => {
                    imagesInputRef.current?.click();
                  }}
                >
                  <span className="plus-menu-icon" aria-hidden="true">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="3" y="3" width="18" height="18" rx="2" />
                      <circle cx="8.5" cy="8.5" r="1.5" />
                      <polyline points="21 15 16 10 5 21" />
                    </svg>
                  </span>
                  <div className="plus-menu-text">
                    <span className="plus-menu-title">Upload images</span>
                    <span className="plus-menu-desc">Scanned pages &amp; photos (OCR)</span>
                  </div>
                </button>

                <button
                  type="button"
                  className="plus-menu-item"
                  role="menuitem"
                  onClick={() => {
                    cameraInputRef.current?.click();
                  }}
                >
                  <span className="plus-menu-icon" aria-hidden="true">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
                      <circle cx="12" cy="13" r="4" />
                    </svg>
                  </span>
                  <div className="plus-menu-text">
                    <span className="plus-menu-title">Take a photo</span>
                    <span className="plus-menu-desc">Camera capture for documents</span>
                  </div>
                </button>
              </div>
            )}
          </div>

          {/* Text Input Area */}
          <div className="unified-input__field-wrap">
            <textarea
              ref={textareaRef}
              id="unified-tender-input"
              className="unified-input__textarea"
              placeholder={
                pdfFile
                  ? 'PDF attached. Press ↑ to analyze or add notes...'
                  : images.length > 0
                  ? `${images.length} image(s) ready. Press ↑ to analyze...`
                  : 'Tell us what you need to check...'
              }
              value={text}
              onChange={(e) => {
                setText(e.target.value);
                autoResizeTextarea(e.target);
              }}
              onKeyDown={handleKeyDown}
              rows={1}
              aria-label="Tender requirement or description"
              disabled={disabled}
            />
          </div>

          {/* Submit / Arrow Button */}
          <button
            type="button"
            className={`unified-input__submit-btn${canSubmit ? ' unified-input__submit-btn--ready' : ''}`}
            onClick={handleSubmit}
            aria-label="Start analysis"
            title={canSubmit ? 'Start analysis (Enter)' : 'Type requirement or attach document'}
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.6"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <line x1="12" y1="19" x2="12" y2="5" />
              <polyline points="5 12 12 5 19 12" />
            </svg>
          </button>
        </div>

        {/* Hidden File Inputs */}
        <input
          ref={pdfInputRef}
          type="file"
          accept=".pdf,.docx"
          style={{ display: 'none' }}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) handlePdfSelected(f);
            e.target.value = '';
          }}
          aria-hidden="true"
        />
        <input
          ref={imagesInputRef}
          type="file"
          accept="image/png,image/jpeg,image/webp"
          multiple
          style={{ display: 'none' }}
          onChange={(e) => {
            if (e.target.files && e.target.files.length > 0) {
              handleImagesSelected(e.target.files);
            }
            e.target.value = '';
          }}
          aria-hidden="true"
        />
        <input
          ref={cameraInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          style={{ display: 'none' }}
          onChange={(e) => {
            if (e.target.files && e.target.files.length > 0) {
              handleImagesSelected(e.target.files);
            }
            e.target.value = '';
          }}
          aria-hidden="true"
        />
      </div>

      {/* Inline Validation Error if any */}
      {inputError && (
        <div className="unified-input__error" role="alert">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <span>{inputError}</span>
        </div>
      )}
    </div>
  );
}
