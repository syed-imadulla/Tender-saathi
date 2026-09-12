// api.ts — TenderSaathi API client
// All requests go through /api (proxied to Flask on :5000 by Vite)
// No API keys ever stored here.

import type { AnalysisResult } from './types';

const BASE = '/api';

async function handleResponse<T>(res: Response): Promise<T> {
  const contentType = res.headers.get('Content-Type') || '';
  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      msg = body.error || msg;
    } catch {
      // ignore parse error
    }
    throw new Error(msg);
  }
  if (contentType.includes('application/json')) {
    return res.json() as Promise<T>;
  }
  return res.blob() as unknown as T;
}

export async function analyzeText(text: string): Promise<AnalysisResult> {
  const res = await fetch(`${BASE}/analyze/text`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
  return handleResponse<AnalysisResult>(res);
}

export async function analyzePdf(file: File): Promise<AnalysisResult> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${BASE}/analyze/pdf`, {
    method: 'POST',
    body: form,
  });
  return handleResponse<AnalysisResult>(res);
}

export async function analyzeSample(
  demo: 'cpvc' | 'valve' | 'superseded'
): Promise<AnalysisResult> {
  const res = await fetch(`${BASE}/analyze/sample/${demo}`);
  return handleResponse<AnalysisResult>(res);
}

export async function analyzeImages(files: File[]): Promise<AnalysisResult> {
  if (files.length === 0) throw new Error('No images selected.');
  const form = new FormData();
  for (const file of files) {
    form.append('files[]', file);
  }
  const res = await fetch(`${BASE}/analyze/image`, {
    method: 'POST',
    body: form,
  });
  return handleResponse<AnalysisResult>(res);
}

export async function downloadReport(
  tenderId: string,
  format: 'json' | 'markdown'
): Promise<Blob> {
  const ext = format === 'json' ? 'json' : 'markdown';
  const res = await fetch(`${BASE}/report/${tenderId}/${ext}`);
  if (!res.ok) {
    let msg = `Download failed (${res.status})`;
    try {
      const b = await res.json();
      msg = b.error || msg;
    } catch {
      // ignore
    }
    throw new Error(msg);
  }
  return res.blob();
}

export function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
