import '../styles/globals.css'
import { AuthProvider } from '../context/AuthContext'
import Head from 'next/head'
import { useRouter } from 'next/router'
import NavBar from '../components/NavBar'
import Seo from '../components/Seo'

export default function MyApp({ Component, pageProps }) {
  const router = useRouter()
  const isMarketingPage = ['/', '/pricing'].includes(router.pathname)

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
  const showProductNav = !isMarketingPage && !['auth', 'utility'].includes(experience)
  const publicSeo = {
    '/': {
      title: 'Run My Pool',
      description: 'Run a professional NFL survivor pool with automated picks, standings, deadlines, commissioner controls, and mobile access.',
    },
    '/pricing': {
      title: 'Football Pool Pricing',
      description: 'Simple season pricing for NFL survivor pool commissioners. Start free, grow by the hundred, or run unlimited entries for one predictable price.',
      path: '/pricing',
    },
    '/install': {
      title: 'Install the Run My Pool App',
      description: 'Install Run My Pool on iPhone, Android, or desktop for fast home-screen access to picks and standings.',
      path: '/install',
    },
  }[router.pathname]

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
        
        {/* Favicon and app icons */}
        <link rel="icon" type="image/png" href="/icons/icon-192x192.png" />
        <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
        <link rel="manifest" href="/manifest.json" />
        
      </Head>
      <Seo
        {...(publicSeo || {
          title: 'Run My Pool',
          description: 'Run My Pool account and commissioner workspace.',
          noIndex: true,
          path: router.asPath?.split('?')[0] || router.pathname,
        })}
      />
      <AuthProvider>
        <div
          className={isMarketingPage ? '' : `broadcast-v2 broadcast-v2--${experience}`}
          data-route={router.pathname}
        >
          {showProductNav && <NavBar />}
          <Component {...pageProps} />
        </div>
      </AuthProvider>
    </>
  )
}
