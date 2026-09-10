// Header.tsx — Persistent navigation header
import './Header.css';

interface HeaderProps {
  onLogoClick?: () => void;
}

export default function Header({ onLogoClick }: HeaderProps) {
  return (
    <header className="header" role="banner">
      <div className="header__inner">
        {/* Logo */}
        <div className="header__logo" onClick={onLogoClick} role="button" tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && onLogoClick?.()}>
          <div className="header__logo-mark" aria-hidden="true">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 12l2 2 4-4" />
              <path d="M21 12c0 1.2-.504 2.3-1.312 3.1l-6.376 6.376A2.5 2.5 0 0111.5 22.2H6.5a2.5 2.5 0 01-2.5-2.5v-5a2.5 2.5 0 01.724-1.812l6.376-6.376A4.5 4.5 0 0121 12z" />
            </svg>
          </div>
          <span className="header__wordmark">Tender<span>Saathi</span></span>
        </div>

        {/* Navigation */}
        <nav aria-label="Main navigation">
          <ul className="header__nav">
            <li className="nav-hide-mobile"><a href="#home">Home</a></li>
            <li className="nav-hide-mobile"><a href="#how-it-works">How it works</a></li>
            <li className="nav-hide-mobile"><a href="#about">About</a></li>
            <li>
              <button className="header__signin" aria-label="Sign in (coming soon)">
                Sign in
              </button>
            </li>
          </ul>
        </nav>
      </div>
    </header>
  );
}
