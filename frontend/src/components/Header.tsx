// Header.tsx — Minimal floating pill navigation with functional modals
import { useState } from 'react';
import './Header.css';

interface HeaderProps {
  onLogoClick?: () => void;
  onOpenHowItWorks?: () => void;
  onOpenAbout?: () => void;
}

export default function Header({
  onLogoClick,
  onOpenHowItWorks,
  onOpenAbout,
}: HeaderProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleHowItWorks = (e: React.MouseEvent) => {
    e.preventDefault();
    setMobileMenuOpen(false);
    onOpenHowItWorks?.();
  };

  const handleAbout = (e: React.MouseEvent) => {
    e.preventDefault();
    setMobileMenuOpen(false);
    onOpenAbout?.();
  };

  return (
    <div className="header-wrapper">
      <header className="header" role="banner">
        {/* Brand Logo */}
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

        {/* Desktop Navigation */}
        <nav aria-label="Main navigation" className="header__nav-desktop">
          <ul className="header__nav">
            <li>
              <button
                type="button"
                className="nav-link-btn"
                onClick={handleHowItWorks}
              >
                How it works
              </button>
            </li>
            <li>
              <button
                type="button"
                className="nav-link-btn"
                onClick={handleAbout}
              >
                About
              </button>
            </li>
            <li>
              <button
                type="button"
                className="header__info-btn"
                onClick={handleAbout}
                aria-label="About TenderSaathi"
                title="System information"
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="16" x2="12" y2="12" />
                  <line x1="12" y1="8" x2="12.01" y2="8" />
                </svg>
              </button>
            </li>
          </ul>
        </nav>

        {/* Mobile Hamburger Toggle */}
        <button
          type="button"
          className="header__mobile-toggle"
          onClick={() => setMobileMenuOpen((prev) => !prev)}
          aria-label={mobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
          aria-expanded={mobileMenuOpen}
        >
          {mobileMenuOpen ? (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          ) : (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          )}
        </button>

        {/* Mobile Dropdown Menu */}
        {mobileMenuOpen && (
          <div className="header__mobile-menu" role="menu">
            <button
              type="button"
              className="header__mobile-item"
              onClick={handleHowItWorks}
              role="menuitem"
            >
              How it works
            </button>
            <button
              type="button"
              className="header__mobile-item"
              onClick={handleAbout}
              role="menuitem"
            >
              About
            </button>
          </div>
        )}
      </header>
    </div>
  );
}
