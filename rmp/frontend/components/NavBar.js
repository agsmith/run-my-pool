import Link from 'next/link';
import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';

export default function NavBar() {
  const MOBILE_NAV_BREAKPOINT = 960;
  const { user, logout } = useAuth();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkDevice = () => {
      setIsMobile(window.innerWidth <= MOBILE_NAV_BREAKPOINT);
    };
    
    checkDevice();
    window.addEventListener('resize', checkDevice);
    return () => window.removeEventListener('resize', checkDevice);
  }, []);

  const toggleMobileMenu = () => {
    setIsMobileMenuOpen(!isMobileMenuOpen);
  };

  const closeMobileMenu = () => {
    setIsMobileMenuOpen(false);
  };

  const navStyles = {
    brand: {
      fontSize: '1.25rem',
      fontWeight: '800',
      color: '#fff',
      textDecoration: 'none',
      marginRight: '2rem',
      fontStyle: 'italic',
      letterSpacing: '0.04em'
    },
    menuToggle: {
      display: isMobile ? 'block' : 'none',
      background: 'none',
      border: 'none',
      color: '#fff',
      fontSize: '1.5rem',
      cursor: 'pointer',
      padding: '0.5rem',
      borderRadius: '4px',
      transition: 'background-color 0.2s ease'
    },
    menuContainer: {
      display: isMobile ? (isMobileMenuOpen ? 'flex' : 'none') : 'flex',
      width: isMobile ? '100%' : 'auto',
      flexDirection: isMobile ? 'column' : 'row',
      alignItems: isMobile ? 'stretch' : 'center',
      marginTop: isMobile ? '1rem' : '0',
      gap: isMobile ? '0' : '1rem'
    },
    navLink: {
      color: '#b8c5c6',
      textDecoration: 'none',
      padding: isMobile ? '0.75rem 0' : '0.5rem 1rem',
      borderRadius: '999px',
      transition: 'background-color 0.2s ease',
      fontSize: isMobile ? '1rem' : '0.9rem',
      fontWeight: '700',
      letterSpacing: '0.02em',
      borderBottom: isMobile ? '1px solid #444' : 'none'
    },
    logoutButton: {
      color: '#fff',
      background: 'none',
      border: 'none',
      cursor: 'pointer',
      padding: isMobile ? '0.75rem 0' : '0.5rem 1rem',
      borderRadius: '4px',
      transition: 'background-color 0.2s ease',
      fontSize: isMobile ? '1rem' : '0.9rem',
      fontWeight: '500',
      textAlign: 'left',
      width: isMobile ? '100%' : 'auto',
      whiteSpace: 'nowrap'
    }
  };

  const handleLinkHover = (e) => {
    e.currentTarget.style.backgroundColor = '#1b282c';
    e.currentTarget.style.color = '#d7ff3f';
  };

  const handleLinkLeave = (e) => {
    e.currentTarget.style.backgroundColor = 'transparent';
    e.currentTarget.style.color = '#b8c5c6';
  };

  return (
    <nav className="broadcast-nav">
      <div style={{ display: 'flex', alignItems: 'center', width: isMobile ? '100%' : 'auto', justifyContent: isMobile ? 'space-between' : 'flex-start' }}>
        <Link href="/" className="broadcast-nav__brand" style={navStyles.brand} onClick={closeMobileMenu}>
          <span className="product-football-mark" aria-hidden="true"><i /><i /><i /></span>
          <span>RUN MY <b>POOL</b></span>
        </Link>
        
        <button 
          style={navStyles.menuToggle}
          onClick={toggleMobileMenu}
          aria-label="Toggle navigation menu"
          aria-expanded={isMobileMenuOpen}
          onMouseEnter={handleLinkHover}
          onMouseLeave={handleLinkLeave}
        >
          {isMobileMenuOpen ? '✕' : '☰'}
        </button>
      </div>

      <div style={navStyles.menuContainer}>
        <Link 
          href="/dashboard" 
          style={navStyles.navLink}
          onClick={closeMobileMenu}
          onMouseEnter={handleLinkHover}
          onMouseLeave={handleLinkLeave}
        >
          Dashboard
        </Link>
        <Link 
          href="/leagues" 
          style={navStyles.navLink}
          onClick={closeMobileMenu}
          onMouseEnter={handleLinkHover}
          onMouseLeave={handleLinkLeave}
        >
          Leagues
        </Link>
        <Link
          href="/install"
          style={navStyles.navLink}
          onClick={closeMobileMenu}
          onMouseEnter={handleLinkHover}
          onMouseLeave={handleLinkLeave}
        >
          Install App
        </Link>
        {user ? (
          <>
            <Link 
              href="/profile" 
              style={navStyles.navLink}
              onClick={closeMobileMenu}
              onMouseEnter={handleLinkHover}
              onMouseLeave={handleLinkLeave}
            >
              Profile
            </Link>
            <button 
              onClick={() => {
                logout();
                closeMobileMenu();
              }} 
              style={navStyles.logoutButton}
              onMouseEnter={handleLinkHover}
              onMouseLeave={handleLinkLeave}
            >
              Logout
            </button>
          </>
        ) : (
          <>
            <Link 
              href="/login" 
              style={navStyles.navLink}
              onClick={closeMobileMenu}
              onMouseEnter={handleLinkHover}
              onMouseLeave={handleLinkLeave}
            >
              Login
            </Link>
            <Link 
              href="/register" 
              style={navStyles.navLink}
              onClick={closeMobileMenu}
              onMouseEnter={handleLinkHover}
              onMouseLeave={handleLinkLeave}
            >
              Register
            </Link>
          </>
        )}
      </div>
    </nav>
  );
}
