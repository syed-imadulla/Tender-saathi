// ImageUpload.tsx — Reusable image upload component for TenderSaathi
// Supports drag-and-drop, file picker, mobile camera capture,
// per-image preview, removal, and basic reordering.
import { useRef, useState, useCallback, useId } from 'react';
import './ImageUpload.css';

export interface UploadedImage {
  id: string;
  file: File;
  previewUrl: string;
}

interface ImageUploadProps {
  images: UploadedImage[];
  onChange: (images: UploadedImage[]) => void;
  maxImages?: number;
  maxSizeMb?: number;
  disabled?: boolean;
}

const ACCEPTED_TYPES = ['image/png', 'image/jpeg', 'image/webp'];
const ACCEPTED_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.webp'];

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function ImageUpload({
  images,
  onChange,
  maxImages = 5,
  maxSizeMb = 10,
  disabled = false,
}: ImageUploadProps) {
  const [dragOver, setDragOver] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const dropZoneId = useId();

  const maxBytes = maxSizeMb * 1024 * 1024;

  const validateAndAdd = useCallback(
    (rawFiles: FileList | File[]) => {
      const fileArr = Array.from(rawFiles);
      const errs: string[] = [];
      const toAdd: UploadedImage[] = [];

      for (const file of fileArr) {
        // Type check
        const ext = '.' + file.name.split('.').pop()?.toLowerCase();
        if (!ACCEPTED_TYPES.includes(file.type) && !ACCEPTED_EXTENSIONS.includes(ext)) {
          errs.push(`"${file.name}" — unsupported format. Use PNG, JPG, or WEBP.`);
          continue;
        }
        // Size check
        if (file.size > maxBytes) {
          errs.push(`"${file.name}" — too large (${formatBytes(file.size)}). Max is ${maxSizeMb} MB.`);
          continue;
        }
        // Total count check
        if (images.length + toAdd.length >= maxImages) {
          errs.push(`Maximum ${maxImages} images allowed.`);
          break;
        }
        toAdd.push({
          id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
          file,
          previewUrl: URL.createObjectURL(file),
        });
      }

      setErrors(errs);
      if (toAdd.length > 0) {
        onChange([...images, ...toAdd]);
      }
    },
    [images, maxBytes, maxImages, maxSizeMb, onChange]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (disabled) return;
      if (e.dataTransfer.files) validateAndAdd(e.dataTransfer.files);
    },
    [disabled, validateAndAdd]
  );

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files) {
        validateAndAdd(e.target.files);
        // Reset so same file can be re-selected if removed
        e.target.value = '';
      }
    },
    [validateAndAdd]
  );

  const handleRemove = useCallback(
    (id: string) => {
      const updated = images.filter((img) => img.id !== id);
      // Revoke removed preview URL
      const removed = images.find((img) => img.id === id);
      if (removed) URL.revokeObjectURL(removed.previewUrl);
      setErrors([]);
      onChange(updated);
    },
    [images, onChange]
  );

  const handleMove = useCallback(
    (id: string, direction: -1 | 1) => {
      const idx = images.findIndex((img) => img.id === id);
      if (idx < 0) return;
      const newIdx = idx + direction;
      if (newIdx < 0 || newIdx >= images.length) return;
      const updated = [...images];
      [updated[idx], updated[newIdx]] = [updated[newIdx], updated[idx]];
      onChange(updated);
    },
    [images, onChange]
  );

  const canAddMore = images.length < maxImages;

  return (
    <div className="image-upload">
      {/* OCR notice */}
      <div className="image-upload__notice">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
        <span>
          <strong>OCR-assisted extraction.</strong> Text is extracted from images using OCR and passed through the same evidence pipeline. Human review is always required.
        </span>
      </div>

      {/* Drop zone (only shown when more images can be added) */}
      {canAddMore && !disabled && (
        <div
          id={dropZoneId}
          className={`image-upload__dropzone${dragOver ? ' image-upload__dropzone--drag' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          role="region"
          aria-label="Drop images here or click to upload"
        >
          <svg className="image-upload__drop-icon" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
            <circle cx="8.5" cy="8.5" r="1.5" />
            <polyline points="21 15 16 10 5 21" />
          </svg>
          <p className="image-upload__drop-label">
            Drag &amp; drop images here
            <span className="image-upload__drop-sub">PNG, JPG, WEBP · up to {maxSizeMb} MB each</span>
          </p>
          <div className="image-upload__drop-actions">
            <button
              type="button"
              className="image-upload__pick-btn"
              onClick={() => fileInputRef.current?.click()}
              aria-label="Choose images from device"
            >
              Choose files
            </button>
            <button
              type="button"
              className="image-upload__pick-btn image-upload__pick-btn--camera"
              onClick={() => cameraInputRef.current?.click()}
              aria-label="Take a photo with camera"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
                <circle cx="12" cy="13" r="4" />
              </svg>
              Take photo
            </button>
          </div>
          <p className="image-upload__count-hint">
            {images.length} / {maxImages} images
          </p>
        </div>
      )}

      {/* Hidden file inputs */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp"
        multiple
        className="image-upload__hidden-input"
        onChange={handleFileChange}
        aria-hidden="true"
        tabIndex={-1}
      />
      <input
        ref={cameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="image-upload__hidden-input"
        onChange={handleFileChange}
        aria-hidden="true"
        tabIndex={-1}
      />

      {/* Validation errors */}
      {errors.length > 0 && (
        <ul className="image-upload__errors" role="alert">
          {errors.map((err, i) => (
            <li key={i}>{err}</li>
          ))}
        </ul>
      )}

      {/* Image previews */}
      {images.length > 0 && (
        <ul className="image-upload__list" aria-label="Uploaded images">
          {images.map((img, idx) => (
            <li key={img.id} className="image-upload__item">
              <img
                src={img.previewUrl}
                alt={`Preview: ${img.file.name}`}
                className="image-upload__thumb"
              />
              <div className="image-upload__item-info">
                <span className="image-upload__item-name" title={img.file.name}>
                  {img.file.name}
                </span>
                <span className="image-upload__item-size">{formatBytes(img.file.size)}</span>
              </div>
              <div className="image-upload__item-actions">
                <button
                  type="button"
                  className="image-upload__reorder-btn"
                  onClick={() => handleMove(img.id, -1)}
                  disabled={idx === 0}
                  aria-label={`Move ${img.file.name} up`}
                  title="Move up"
                >
                  ↑
                </button>
                <button
                  type="button"
                  className="image-upload__reorder-btn"
                  onClick={() => handleMove(img.id, 1)}
                  disabled={idx === images.length - 1}
                  aria-label={`Move ${img.file.name} down`}
                  title="Move down"
                >
                  ↓
                </button>
                <button
                  type="button"
                  className="image-upload__remove-btn"
                  onClick={() => handleRemove(img.id)}
                  aria-label={`Remove ${img.file.name}`}
                  title="Remove"
                >
                  ✕
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
