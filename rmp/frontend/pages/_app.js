import '../styles/globals.css'
import { AuthProvider } from '../context/AuthContext'
import Head from 'next/head'
import { useRouter } from 'next/router'
import NavBar from '../components/NavBar'

export default function MyApp({ Component, pageProps }) {
  const router = useRouter()
  const isLandingPage = router.pathname === '/'

  const getExperience = (pathname) => {
    if (['/login', '/register', '/create-account', '/forgot-password', '/reset-password'].includes(pathname)) return 'auth'
    if (pathname === '/offline') return 'utility'
    if (pathname.startsWith('/admin')) return 'admin'
    if (pathname.includes('/messages') || pathname === '/message-board') return 'community'
    if (pathname.includes('/entries')) return 'entries'
    if (pathname === '/create-league' || pathname === '/create-pool') return 'setup'
    if (pathname.startsWith('/pool/') || pathname.startsWith('/league/')) return 'competition'
    if (pathname === '/profile') return 'account'
    return 'dashboard'
  }

  const experience = getExperience(router.pathname)
  const showProductNav = !isLandingPage && !['auth', 'utility'].includes(experience)

  return (
    <>
      <Head>
        <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
        <meta name="theme-color" content="#080d0f" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
        <meta name="apple-mobile-web-app-title" content="Run My Pool" />
        
        {/* Prevent automatic phone number detection */}
        <meta name="format-detection" content="telephone=no" />
        
        {/* Optimize touch interactions */}
        <meta name="msapplication-tap-highlight" content="no" />
        
        {/* SEO and responsive meta tags */}
        <meta name="description" content="Professional football pick pool management system. Create, manage, and track your NFL pools with ease." />
        <meta name="keywords" content="NFL, football, pool, picks, league, fantasy, sports betting" />
        
        {/* Favicon and app icons */}
        <link rel="icon" href="/favicon.ico" />
        <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
        <link rel="manifest" href="/manifest.json" />
        
        <title>Run My Pool - NFL Pick Pool Management</title>
      </Head>
      <AuthProvider>
        <div
          className={isLandingPage ? '' : `broadcast-v2 broadcast-v2--${experience}`}
          data-route={router.pathname}
        >
          {showProductNav && <NavBar />}
          <Component {...pageProps} />
        </div>
      </AuthProvider>
    </>
  )
}
