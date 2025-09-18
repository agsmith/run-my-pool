import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '../context/AuthContext';
import { mobileStyles, getResponsiveStyle, touchStyles } from '../styles/globalStyles';

export default function Home() {
  const { user } = useAuth();
  const router = useRouter();
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    // If user is logged in, redirect to dashboard
    if (user) {
      router.push('/dashboard');
    }
  }, [user, router]);

  useEffect(() => {
    const checkDevice = () => {
      setIsMobile(window.innerWidth <= 767);
    };
    
    checkDevice();
    window.addEventListener('resize', checkDevice);
    return () => window.removeEventListener('resize', checkDevice);
  }, []);

  // Don't render the landing page if user is logged in (will redirect)
  if (user) {
    return <div>Redirecting...</div>;
  }

  const responsiveStyles = {
    container: {
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      display: 'flex',
      flexDirection: 'column'
    },
    header: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: isMobile ? '1rem' : '1.5rem 2rem',
      background: 'rgba(255, 255, 255, 0.1)',
      backdropFilter: 'blur(10px)',
      flexWrap: 'wrap',
      gap: isMobile ? '1rem' : '0'
    },
    brandTitle: {
      color: 'white',
      fontSize: isMobile ? '1.25rem' : '1.5rem',
      fontWeight: '700',
      textDecoration: 'none'
    },
    loginButton: {
      fontWeight: '600',
      color: '#667eea',
      textDecoration: 'none',
      border: 'none',
      borderRadius: '8px',
      padding: isMobile ? '0.75rem 1.5rem' : '0.75rem 2rem',
      background: 'white',
      transition: 'all 0.2s ease',
      boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
      fontSize: isMobile ? '0.9rem' : '1rem',
      minHeight: isMobile ? '48px' : '44px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center'
    },
    main: {
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      textAlign: 'center',
      padding: isMobile ? '1rem' : '2rem',
      background: 'transparent'
    },
    heroTitle: {
      fontSize: isMobile ? '2.5rem' : '4rem',
      fontWeight: '800',
      marginBottom: '1rem',
      color: 'white',
      textShadow: '0 4px 8px rgba(0, 0, 0, 0.5)',
      lineHeight: '1.1',
      zIndex: 10
    },
    heroSubtitle: {
      fontSize: isMobile ? '1.25rem' : '1.8rem',
      fontWeight: '400',
      marginBottom: '1rem',
      color: 'white',
      maxWidth: '800px',
      textShadow: '0 2px 4px rgba(0, 0, 0, 0.5)',
      zIndex: 10,
      lineHeight: '1.3'
    },
    heroDescription: {
      maxWidth: isMobile ? '100%' : '700px',
      fontSize: isMobile ? '1rem' : '1.25rem',
      color: 'white',
      marginBottom: '3rem',
      fontWeight: '300',
      textShadow: '0 2px 4px rgba(0, 0, 0, 0.5)',
      zIndex: 10,
      lineHeight: '1.5',
      padding: isMobile ? '0 1rem' : '0'
    }
  };
  return (
    <div style={responsiveStyles.container}>
      {/* Header */}
      <header style={responsiveStyles.header}>
        <Link href="/" style={responsiveStyles.brandTitle}>
          🏈 Run My Pool
        </Link>
        <Link 
          href="/login" 
          style={responsiveStyles.loginButton}
          onMouseEnter={(e) => {
            if (!isMobile) {
              e.target.style.transform = 'translateY(-2px)';
              e.target.style.boxShadow = '0 6px 20px rgba(0, 0, 0, 0.2)';
            }
          }}
          onMouseLeave={(e) => {
            if (!isMobile) {
              e.target.style.transform = 'translateY(0)';
              e.target.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.15)';
            }
          }}
        >
          Login
        </Link>
      </header>

      {/* Hero Section */}
      <main style={responsiveStyles.main}>
        <h1 style={responsiveStyles.heroTitle}>
          🏈 Run My Pool
        </h1>
        <h2 style={responsiveStyles.heroSubtitle}>
          Highly Configurable, Affordable, Scalable Pool Management System
        </h2>
        <p style={responsiveStyles.heroDescription}>
          🏈 Your pool, your way. Complete football-themed pool management with mobile app support. Create and manage professional football pick pools with ease. Support for multiple game types, custom scoring, and comprehensive league management. 🏈
        </p>
        
        <Link 
          href="/create-account" 
          style={{ 
            fontSize: '1.2rem',
            fontWeight: '700', 
            color: '#667eea', 
            textDecoration: 'none', 
            border: 'none', 
            borderRadius: '12px', 
            padding: '1rem 3rem', 
            background: 'white', 
            transition: 'all 0.3s ease',
            boxShadow: '0 8px 25px rgba(0, 0, 0, 0.2)',
            marginBottom: '4rem'
          }}
          onMouseEnter={(e) => {
            e.target.style.transform = 'translateY(-3px)';
            e.target.style.boxShadow = '0 12px 35px rgba(0, 0, 0, 0.3)';
          }}
          onMouseLeave={(e) => {
            e.target.style.transform = 'translateY(0)';
            e.target.style.boxShadow = '0 8px 25px rgba(0, 0, 0, 0.2)';
          }}
        >
          Get Started Free
        </Link>

        {/* Features Section */}
        <div style={{ 
          background: 'white', 
          borderRadius: '20px', 
          padding: '3rem 2rem',
          maxWidth: '1200px',
          width: '100%',
          boxShadow: '0 20px 40px rgba(0, 0, 0, 0.15)',
          border: '1px solid rgba(255, 255, 255, 0.2)'
        }}>
          <h3 style={{ 
            fontSize: '2.5rem', 
            fontWeight: '700', 
            marginBottom: '3rem', 
            color: '#1a202c',
            textAlign: 'center'
          }}>
            Why Choose Run My Pool?
          </h3>
          
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', 
            gap: '2.5rem',
            marginBottom: '2rem'
          }}>
            {/* Highly Configurable */}
            <div style={{ textAlign: 'left', padding: '1.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: '1rem', gap: '1rem' }}>
                <div style={{ fontSize: '3rem' }}>⚙️</div>
                <h4 style={{ fontSize: '1.5rem', fontWeight: '700', margin: '0', color: '#1a202c' }}>
                  Highly Configurable
                </h4>
              </div>
              <p style={{ fontSize: '1rem', color: '#4a5568', lineHeight: '1.6' }}>
                Customize every aspect of your pool - from scoring rules to entry limits. Create the perfect pool experience for your group.
              </p>
            </div>

            {/* Affordable */}
            <div style={{ textAlign: 'left', padding: '1.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: '1rem', gap: '1rem' }}>
                <div style={{ fontSize: '3rem' }}>💰</div>
                <h4 style={{ fontSize: '1.5rem', fontWeight: '700', margin: '0', color: '#1a202c' }}>
                  Affordable
                </h4>
              </div>
              <p style={{ fontSize: '1rem', color: '#4a5568', lineHeight: '1.6' }}>
                Premium features at budget-friendly prices. No hidden fees, no surprises. Just great value for pool management excellence.
              </p>
            </div>

            {/* Scalable */}
            <div style={{ textAlign: 'left', padding: '1.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: '1rem', gap: '1rem' }}>
                <div style={{ fontSize: '3rem' }}>📈</div>
                <h4 style={{ fontSize: '1.5rem', fontWeight: '700', margin: '0', color: '#1a202c' }}>
                  Scalable
                </h4>
              </div>
              <h4 style={{ fontSize: '1.5rem', fontWeight: '700', marginBottom: '1rem', color: '#1a202c' }}>
                Scalable
              </h4>
              <p style={{ fontSize: '1rem', color: '#4a5568', lineHeight: '1.6' }}>
                Whether you have 5 friends or 500 participants, our system grows with you. Enterprise-grade reliability at any scale.
              </p>
            </div>

            {/* Mobile App */}
            <div style={{ textAlign: 'left', padding: '1.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: '1rem', gap: '1rem' }}>
                <div style={{ fontSize: '3rem' }}>📱</div>
                <h4 style={{ fontSize: '1.5rem', fontWeight: '700', margin: '0', color: '#1a202c' }}>
                  Mobile App
                </h4>
              </div>
              <p style={{ fontSize: '1rem', color: '#4a5568', lineHeight: '1.6' }}>
                Native mobile app for iOS and Android. Make picks, check standings, and manage your pool from anywhere.
              </p>
            </div>

            {/* Football Themed */}
            <div style={{ textAlign: 'left', padding: '1.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: '1rem', gap: '1rem' }}>
                <div style={{ fontSize: '3rem' }}>🏈</div>
                <h4 style={{ fontSize: '1.5rem', fontWeight: '700', margin: '0', color: '#1a202c' }}>
                  Football Themed
                </h4>
              </div>
              <p style={{ fontSize: '1rem', color: '#4a5568', lineHeight: '1.6' }}>
                Built specifically for football pools with authentic NFL branding, team logos, and real-time game integration.
              </p>
            </div>

            {/* Your Way */}
            <div style={{ textAlign: 'left', padding: '1.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: '1rem', gap: '1rem' }}>
                <div style={{ fontSize: '3rem' }}>🎯</div>
                <h4 style={{ fontSize: '1.5rem', fontWeight: '700', margin: '0', color: '#1a202c' }}>
                  Your Way
                </h4>
              </div>
              <p style={{ fontSize: '1rem', color: '#4a5568', lineHeight: '1.6' }}>
                Survivor pools, pick'em leagues, confidence points - set up any type of football pool with our flexible platform.
              </p>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer style={{ 
        textAlign: 'center', 
        padding: '2rem', 
        background: 'rgba(255, 255, 255, 0.1)',
        backdropFilter: 'blur(10px)',
        color: 'rgba(255, 255, 255, 0.8)',
        fontSize: '1rem'
      }}>
        © 2025 Run My Pool. Built for football fans, by football fans. 🏈
      </footer>
    </div>
  );
}
