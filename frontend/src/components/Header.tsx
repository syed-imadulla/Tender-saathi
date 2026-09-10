// Header.tsx — Floating pill navigation header matching reference images
import './Header.css';

interface HeaderProps {
  onLogoClick?: () => void;
}

export default function Header({ onLogoClick }: HeaderProps) {
  return (
    <div className="header-wrapper">
      <header className="header" role="banner">
        {/* Logo */}
        <div
          className="header__logo"
          onClick={onLogoClick}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && onLogoClick?.()}
          aria-label="TenderSaathi home"
        >
          <span className="header__wordmark">
            Tender<span>Saathi</span>
          </span>
        </div>

        {/* Navigation */}
        <nav aria-label="Main navigation">
          <ul className="header__nav">
            <li>
              <a href="#home" className="nav-pill active" onClick={(e) => { e.preventDefault(); onLogoClick?.(); }}>
                Home
              </a>
            </li>
            <li className="nav-hide-mobile">
              <a href="#how-it-works" className="nav-pill">
                How it works
              </a>
            </li>
            <li className="nav-hide-mobile">
              <a href="#about" className="nav-pill">
                About
              </a>
            </li>
            <li>
              <button className="header__signin" aria-label="Sign in (demo placeholder)" type="button">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
                Sign in
              </button>
            </li>
          </ul>
        </nav>
      </header>
    </div>
  );
}
