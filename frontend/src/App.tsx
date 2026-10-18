// App.tsx — Root component managing primary application states & views
import { useState, useCallback } from 'react';
import type { AnalysisResult, AppState, InputMode } from './types';
import Home from './pages/Home';
import Analyzing, { OCR_STEPS } from './pages/Analyzing';
import Results from './pages/Results';
import StandardsGraph from './pages/StandardsGraph';

export default function App() {
  const [currentView, setCurrentView] = useState<'audit' | 'graph'>('audit');
  const [graphStandard, setGraphStandard] = useState<string | undefined>(undefined);
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

  const handleOpenGraph = useCallback((standardId?: string) => {
    setGraphStandard(standardId);
    setCurrentView('graph');
  }, []);

  const handleNavigateToAudit = useCallback(() => {
    setCurrentView('audit');
  }, []);

  if (currentView === 'graph') {
    return (
      <StandardsGraph
        onNavigateToAudit={handleNavigateToAudit}
        initialStandardId={graphStandard || 'IS-15778-2007'}
      />
    );
  }

  return (
    <>
      {state === 'home' && (
        <Home
          onStartAnalysis={(promise, mode) => handleStartAnalysisWithMode(promise, mode || activeMode)}
          errorMessage={error}
          onOpenGraph={() => handleOpenGraph()}
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

