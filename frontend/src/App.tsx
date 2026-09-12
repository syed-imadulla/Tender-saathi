// App.tsx — Root component managing the 3 primary application states
import { useState, useCallback } from 'react';
import type { AnalysisResult, AppState, InputMode } from './types';
import Home from './pages/Home';
import Analyzing, { OCR_STEPS } from './pages/Analyzing';
import Results from './pages/Results';

export default function App() {
  const [state, setState] = useState<AppState>('home');
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeMode, setActiveMode] = useState<InputMode>('text');

  const handleStartAnalysis = useCallback(
    (promise: Promise<AnalysisResult>, mode?: InputMode) => {
      setState('analyzing');
      setError(null);
      if (mode) setActiveMode(mode);
      promise
        .then((res) => {
          setResult(res);
          setState('results');
        })
        .catch((err) => {
          setError(err instanceof Error ? err.message : 'Analysis failed. Please try again.');
          setState('home');
        });
    },
    []
  );

  // Home passes the mode alongside the promise so Analyzing can pick the right step sequence
  const handleStartAnalysisWithMode = useCallback(
    (promise: Promise<AnalysisResult>, mode: InputMode = 'text') => {
      handleStartAnalysis(promise, mode);
    },
    [handleStartAnalysis]
  );

  const handleNewCheck = useCallback(() => {
    setState('home');
    setResult(null);
    setError(null);
  }, []);

  return (
    <>
      {state === 'home' && (
        <Home
          onStartAnalysis={(promise, mode) => handleStartAnalysisWithMode(promise, mode || activeMode)}
          errorMessage={error}
        />
      )}
      {state === 'analyzing' && (
        <Analyzing steps={activeMode === 'image' ? OCR_STEPS : undefined} />
      )}
      {state === 'results' && result && (
        <Results
          result={result}
          onNewCheck={handleNewCheck}
        />
      )}
    </>
  );
}
