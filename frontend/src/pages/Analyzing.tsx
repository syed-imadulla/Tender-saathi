// Analyzing.tsx — State 2: In-place analyzing animation
// Note: The actual analysis is triggered in Home.tsx before transitioning here.
// This component is purely presentational — it shows progress while analysis runs.
import { useEffect, useState } from 'react';
import './Analyzing.css';
import Header from '../components/Header';
import type { AnalysisResult } from '../types';

interface AnalyzingProps {
  onDone: (result: AnalysisResult) => void;
  onError: (message: string) => void;
}

const STEPS = [
  { label: 'Reading document', durationMs: 600 },
  { label: 'Understanding requirements', durationMs: 1200 },
  { label: 'Finding Indian Standards', durationMs: 2000 },
  { label: 'Checking evidence and lifecycle', durationMs: 1600 },
  { label: 'Preparing review', durationMs: 800 },
];

// Analyzing component just shows the progress steps.
// The App component handles the actual API call and passes result up.
export default function Analyzing(_props: AnalyzingProps) {
  const [activeStep, setActiveStep] = useState(0);

  // Animate steps purely as UX — actual backend decides timing
  useEffect(() => {
    let idx = 0;
    const advance = () => {
      if (idx < STEPS.length - 1) {
        idx++;
        setActiveStep(idx);
        setTimeout(advance, STEPS[idx].durationMs);
      }
    };
    const t = setTimeout(advance, STEPS[0].durationMs);
    return () => clearTimeout(t);
  }, []);

  return (
    <div className="analyzing">
      <Header />
      <main className="analyzing__body" role="main" aria-live="polite" aria-label="Analysis in progress">
        <div className="analyzing__card">
          <h2 className="analyzing__title">
            <span className="analyzing__spinner" aria-hidden="true" />
            Analyzing your tender...
          </h2>

          <ol className="analyzing__steps">
            {STEPS.map((step, i) => {
              const isDone = i < activeStep;
              const isActive = i === activeStep;
              return (
                <li
                  key={step.label}
                  className={`analyzing__step${isDone ? ' analyzing__step--done' : ''}${isActive ? ' analyzing__step--active' : ''}`}
                  aria-current={isActive ? 'step' : undefined}
                >
                  <span
                    className={`analyzing__step-icon${isDone ? ' analyzing__step-icon--done' : ''}${isActive ? ' analyzing__step-icon--active' : ''}${!isDone && !isActive ? ' analyzing__step-icon--pending' : ''}`}
                    aria-hidden="true"
                  >
                    {isDone ? '✓' : ''}
                  </span>
                  {step.label}
                </li>
              );
            })}
          </ol>

          <p className="analyzing__note">
            This may take a few seconds. TenderSaathi is checking Indian Standards evidence
            and cross-referencing the lifecycle database.
          </p>
        </div>
      </main>
    </div>
  );
}
