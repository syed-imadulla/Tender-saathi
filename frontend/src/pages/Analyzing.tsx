// Analyzing.tsx — State 2: In-place analyzing animation
// Accepts an optional `steps` prop so different input modes can show
// different step sequences (e.g., image upload adds an OCR step).
import { useEffect, useState } from 'react';
import './Analyzing.css';
import Header from '../components/Header';

export interface AnalyzingStep {
  label: string;
  durationMs: number;
}

const DEFAULT_STEPS: AnalyzingStep[] = [
  { label: 'Reading document', durationMs: 700 },
  { label: 'Understanding requirements', durationMs: 1400 },
  { label: 'Finding Indian Standards', durationMs: 1800 },
  { label: 'Checking evidence and lifecycle', durationMs: 1500 },
  { label: 'Preparing review', durationMs: 1000 },
];

export const OCR_STEPS: AnalyzingStep[] = [
  { label: 'Reading image', durationMs: 600 },
  { label: 'Extracting text via OCR', durationMs: 1200 },
  { label: 'Understanding requirements', durationMs: 1400 },
  { label: 'Finding Indian Standards', durationMs: 1800 },
  { label: 'Checking evidence and lifecycle', durationMs: 1500 },
  { label: 'Preparing review', durationMs: 1000 },
];

interface AnalyzingProps {
  steps?: AnalyzingStep[];
}

export default function Analyzing({ steps = DEFAULT_STEPS }: AnalyzingProps) {
  const [activeStep, setActiveStep] = useState(0);

  // Progressive checklist animation
  useEffect(() => {
    let idx = 0;
    const advance = () => {
      if (idx < steps.length - 1) {
        idx++;
        setActiveStep(idx);
        setTimeout(advance, steps[idx].durationMs);
      }
    };
    const t = setTimeout(advance, steps[0].durationMs);
    return () => clearTimeout(t);
  }, [steps]);

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
            {steps.map((step, i) => {
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
            This takes a few seconds. TenderSaathi is analyzing procurement clauses against
            the Bureau of Indian Standards (BIS) catalogue.
          </p>
        </div>
      </main>
    </div>
  );
}
