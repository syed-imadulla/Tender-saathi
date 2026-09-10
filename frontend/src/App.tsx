// App.tsx — Root component managing the 3 primary application states
import { useState, useCallback } from 'react';
import type { AnalysisResult, AppState } from './types';
import Home from './pages/Home';
import Analyzing from './pages/Analyzing';
import Results from './pages/Results';

export default function App() {
  const [state, setState] = useState<AppState>('home');
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleAnalysisDone = useCallback((r: AnalysisResult) => {
    setResult(r);
    setError(null);
    setState('results');
  }, []);

  const handleAnalysisError = useCallback((msg: string) => {
    setError(msg);
    setState('home');
  }, []);

  const handleNewCheck = useCallback(() => {
    setState('home');
    setResult(null);
    setError(null);
  }, []);

  const handleStartAnalyzing = useCallback(() => {
    setState('analyzing');
  }, []);

  return (
    <>
      {state === 'home' && (
        <Home
          onStartAnalyzing={handleStartAnalyzing}
          onDone={handleAnalysisDone}
          onError={handleAnalysisError}
          errorMessage={error}
        />
      )}
      {state === 'analyzing' && (
        <Analyzing
          onDone={handleAnalysisDone}
          onError={handleAnalysisError}
        />
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
