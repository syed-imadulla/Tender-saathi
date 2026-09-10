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

  const handleStartAnalysis = useCallback((promise: Promise<AnalysisResult>) => {
    setState('analyzing');
    setError(null);
    promise
      .then((res) => {
        setResult(res);
        setState('results');
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Analysis failed. Please try again.');
        setState('home');
      });
  }, []);

  const handleNewCheck = useCallback(() => {
    setState('home');
    setResult(null);
    setError(null);
  }, []);

  return (
    <>
      {state === 'home' && (
        <Home
          onStartAnalysis={handleStartAnalysis}
          errorMessage={error}
        />
      )}
      {state === 'analyzing' && (
        <Analyzing />
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
