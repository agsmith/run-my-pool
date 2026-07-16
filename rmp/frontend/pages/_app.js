import '../styles/globals.css'
import { AuthProvider } from '../context/AuthContext'
import Head from 'next/head'

export default function MyApp({ Component, pageProps }) {
  return (
    <>
      <Head>
        <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
        <meta name="theme-color" content="#667eea" />
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
        <Component {...pageProps} />
      </AuthProvider>
    </>
  )
}
