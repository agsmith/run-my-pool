// Global styling system for consistent design across all pages

// Responsive breakpoints
export const breakpoints = {
  mobile: '767px',
  tablet: '768px', 
  desktop: '1024px',
  wide: '1200px'
};

// Mobile detection utility
export const isMobile = () => {
  if (typeof window !== 'undefined') {
    return window.innerWidth <= parseInt(breakpoints.mobile);
  }
  return false;
};

// Responsive style generator
export const responsive = {
  mobile: (styles) => ({
    [`@media (max-width: ${breakpoints.mobile})`]: styles
  }),
  tablet: (styles) => ({
    [`@media (min-width: ${breakpoints.tablet}) and (max-width: 1023px)`]: styles  
  }),
  desktop: (styles) => ({
    [`@media (min-width: ${breakpoints.desktop})`]: styles
  }),
  tabletAndUp: (styles) => ({
    [`@media (min-width: ${breakpoints.tablet})`]: styles
  })
};

export const colors = {
  // Primary colors
  primary: {
    50: '#f8fafc',
    100: '#f1f5f9', 
    200: '#e2e8f0',
    300: '#cbd5e1',
    400: '#94a3b8',
    500: '#64748b',
    600: '#475569',
    700: '#334155',
    800: '#1e293b',
    900: '#0f172a'
  },
  
  // Brand colors
  brand: {
    primary: '#10191c',
    secondary: '#286678',
    accent: '#d7ff3f'
  },
  
  // Semantic colors
  success: {
    50: '#f0fff4',
    100: '#dcfce7',
    500: '#22c55e',
    600: '#16a34a',
    700: '#15803d',
    800: '#166534',
    900: '#14532d'
  },
  
  error: {
    50: '#fef2f2',
    100: '#fee2e2',
    500: '#ef4444',
    600: '#dc2626',
    700: '#b91c1c',
    800: '#991b1b',
    900: '#7f1d1d'
  },
  
  warning: {
    50: '#fefcbf',
    100: '#fef3c7',
    500: '#f59e0b',
    600: '#d97706',
    700: '#b45309',
    800: '#92400e'
  },
  
  info: {
    50: '#eff6ff',
    100: '#dbeafe',
    500: '#3b82f6',
    600: '#2563eb',
    700: '#1d4ed8'
  }
};

export const gradients = {
  primary: 'linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)',
  brand: 'radial-gradient(circle at 70% 25%, rgba(39, 114, 130, 0.45), transparent 38%), linear-gradient(135deg, #080d0f 0%, #10191c 100%)',
  success: 'linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)',
  error: 'linear-gradient(135deg, #fee2e2 0%, #fecaca 100%)'
};

export const shadows = {
  sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
  base: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
  md: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
  lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
  xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
  '2xl': '0 25px 50px -12px rgba(0, 0, 0, 0.25)'
};

// Common component styles
export const baseStyles = {
  // Page layouts
  fullPageContainer: {
    minHeight: '100vh',
    background: gradients.primary,
    display: 'flex',
    flexDirection: 'column'
  },
  
  authPageContainer: {
    minHeight: '100vh',
    background: gradients.brand,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '2rem'
  },
  
  // Headers
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '1.5rem 2rem',
    background: 'rgba(255, 255, 255, 0.8)',
    backdropFilter: 'blur(10px)',
    borderBottom: `1px solid ${colors.primary[200]}`
  },
  
  authHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '1.5rem 2rem',
    background: 'rgba(255, 255, 255, 0.1)',
    backdropFilter: 'blur(10px)'
  },
  
  // Main content containers
  mainContent: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '2rem',
    background: 'transparent'
  },
  
  cardContainer: {
    background: 'white',
    borderRadius: '12px',
    padding: '2rem',
    maxWidth: '1400px',
    width: '100%',
    boxShadow: shadows.md,
    border: `1px solid ${colors.primary[200]}`
  },
  
  authCard: {
    backgroundColor: 'white',
    borderRadius: '16px',
    boxShadow: shadows['2xl'],
    padding: '3rem',
    width: '100%',
    maxWidth: '440px',
    position: 'relative'
  },
  
  // Typography
  pageTitle: {
    fontSize: '3rem',
    fontWeight: '800',
    marginBottom: '1rem',
    color: colors.primary[800],
    textAlign: 'center'
  },
  
  sectionTitle: {
    fontSize: '2rem',
    fontWeight: '700',
    color: colors.primary[800],
    margin: 0
  },
  
  brandTitle: {
    color: colors.primary[800],
    fontSize: '2rem',
    fontWeight: '700',
    margin: '0 0 0.5rem 0',
    letterSpacing: '-0.025em'
  },
  
  brandTitleWhite: {
    color: 'white',
    fontSize: '1.5rem',
    fontWeight: '700'
  },
  
  subtitle: {
    color: colors.primary[500],
    fontSize: '1rem',
    margin: 0,
    fontWeight: '400'
  },
  
  // Form elements
  input: {
    width: '100%',
    padding: '0.75rem 1rem',
    border: `2px solid ${colors.primary[200]}`,
    borderRadius: '8px',
    fontSize: '1rem',
    transition: 'all 0.2s ease',
    outline: 'none',
    backgroundColor: 'white'
  },
  
  inputFocus: {
    borderColor: colors.info[500],
    boxShadow: `0 0 0 3px ${colors.info[50]}`
  },
  
  select: {
    width: '100%',
    padding: '0.75rem 1rem',
    border: `1px solid ${colors.primary[300]}`,
    borderRadius: '6px',
    backgroundColor: 'white',
    color: colors.primary[700],
    fontSize: '0.875rem',
    fontWeight: '500',
    cursor: 'pointer',
    outline: 'none',
    transition: 'all 0.2s ease'
  },
  
  label: {
    display: 'block',
    fontSize: '0.875rem',
    fontWeight: '600',
    color: colors.primary[700],
    marginBottom: '0.5rem'
  },
  
  // Buttons
  button: {
    primary: {
      backgroundColor: colors.brand.primary,
      color: 'white',
      border: 'none',
      borderRadius: '8px',
      padding: '0.75rem 1.5rem',
      fontSize: '1rem',
      fontWeight: '600',
      cursor: 'pointer',
      transition: 'all 0.2s ease',
      boxShadow: shadows.base
    },
    
    secondary: {
      backgroundColor: 'white',
      color: colors.brand.primary,
      border: `2px solid ${colors.brand.primary}`,
      borderRadius: '8px',
      padding: '0.75rem 1.5rem',
      fontSize: '1rem',
      fontWeight: '600',
      cursor: 'pointer',
      transition: 'all 0.2s ease',
      boxShadow: shadows.base
    },
    
    success: {
      backgroundColor: colors.success[600],
      color: 'white',
      border: 'none',
      borderRadius: '6px',
      padding: '0.5rem 1rem',
      fontSize: '0.875rem',
      fontWeight: '500',
      cursor: 'pointer',
      transition: 'all 0.2s ease'
    },
    
    warning: {
      backgroundColor: colors.warning[500],
      color: 'white',
      border: 'none',
      borderRadius: '6px',
      padding: '0.5rem 1rem',
      fontSize: '0.875rem',
      fontWeight: '500',
      cursor: 'pointer',
      transition: 'all 0.2s ease'
    },
    
    info: {
      backgroundColor: colors.info[500],
      color: 'white',
      border: 'none',
      borderRadius: '6px',
      padding: '0.5rem 1rem',
      fontSize: '0.875rem',
      fontWeight: '500',
      cursor: 'pointer',
      transition: 'all 0.2s ease'
    },
    
    small: {
      padding: '0.5rem 0.75rem',
      fontSize: '0.75rem',
      borderRadius: '4px'
    }
  },
  
  // Alert messages
  alert: {
    success: {
      backgroundColor: colors.success[50],
      color: colors.success[800],
      padding: '0.75rem 1rem',
      borderRadius: '8px',
      marginBottom: '1.5rem',
      border: `1px solid ${colors.success[200]}`,
      fontSize: '0.875rem'
    },
    
    error: {
      backgroundColor: colors.error[50],
      color: colors.error[800],
      padding: '0.75rem 1rem',
      borderRadius: '8px',
      marginBottom: '1.5rem',
      border: `1px solid ${colors.error[200]}`,
      fontSize: '0.875rem'
    },
    
    warning: {
      backgroundColor: colors.warning[50],
      color: colors.warning[800],
      padding: '0.75rem 1rem',
      borderRadius: '8px',
      marginBottom: '1.5rem',
      border: `1px solid ${colors.warning[200]}`,
      fontSize: '0.875rem'
    },
    
    info: {
      backgroundColor: colors.info[50],
      color: colors.info[700],
      padding: '0.75rem 1rem',
      borderRadius: '8px',
      marginBottom: '1.5rem',
      border: `1px solid ${colors.info[200]}`,
      fontSize: '0.875rem'
    }
  },
  
  // Common layout components
  grid: {
    display: 'grid',
    gap: '2rem',
    gridTemplateColumns: 'repeat(auto-fit, minmax(min(350px, 100%), 1fr))',
    width: '100%',
    padding: '0'
  },
  
  flexBetween: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  
  flexCenter: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center'
  },
  
  // Pool/card specific styles
  poolCard: {
    border: `1px solid ${colors.primary[200]}`,
    borderRadius: '12px',
    padding: '1.5rem',
    backgroundColor: '#fafafa',
    transition: 'all 0.2s ease',
    boxShadow: shadows.sm,
    minWidth: '0',
    minHeight: '280px',
    position: 'relative',
    display: 'flex',
    flexDirection: 'column'
  }
};

// Hover effects
export const hoverEffects = {
  button: {
    primary: {
      backgroundColor: colors.primary[700],
      boxShadow: shadows.lg
    },
    
    secondary: {
      backgroundColor: colors.primary[50]
    },
    
    success: {
      backgroundColor: colors.success[700]
    },
    
    warning: {
      backgroundColor: colors.warning[600]
    },
    
    info: {
      backgroundColor: colors.info[600]
    }
  },
  
  card: {
    boxShadow: shadows.xl,
    transform: 'translateY(-2px)'
  }
};

// Utility functions
export const createHoverHandlers = (baseStyle, hoverStyle) => ({
  onMouseEnter: (e) => {
    Object.assign(e.target.style, hoverStyle);
  },
  onMouseLeave: (e) => {
    Object.assign(e.target.style, baseStyle);
  }
});

export const createFocusHandlers = (focusStyle, blurStyle) => ({
  onFocus: (e) => {
    Object.assign(e.target.style, focusStyle);
  },
  onBlur: (e) => {
    Object.assign(e.target.style, blurStyle);
  }
});

// Mobile-responsive styles
export const mobileStyles = {
  // Container styles
  container: {
    mobile: {
      padding: '1rem',
      maxWidth: '100%'
    },
    tablet: {
      padding: '2rem',
      maxWidth: '768px',
      margin: '0 auto'
    },
    desktop: {
      padding: '2rem',
      maxWidth: '1200px',
      margin: '0 auto'
    }
  },

  // Typography responsive styles
  typography: {
    pageTitle: {
      mobile: {
        fontSize: '2rem',
        lineHeight: '1.2',
        textAlign: 'center',
        marginBottom: '1rem'
      },
      desktop: {
        fontSize: '3rem',
        lineHeight: '1.1',
        marginBottom: '1.5rem'
      }
    },
    sectionTitle: {
      mobile: {
        fontSize: '1.5rem',
        lineHeight: '1.3'
      },
      desktop: {
        fontSize: '2rem',
        lineHeight: '1.2'
      }
    }
  },

  // Grid system
  grid: {
    mobile: {
      display: 'grid',
      gridTemplateColumns: '1fr',
      gap: '1rem'
    },
    tablet: {
      gridTemplateColumns: 'repeat(2, 1fr)',
      gap: '1.5rem'
    },
    desktop: {
      gridTemplateColumns: 'repeat(3, 1fr)',
      gap: '2rem'
    }
  },

  // Card responsive styles
  card: {
    mobile: {
      padding: '1rem',
      borderRadius: '8px',
      boxShadow: shadows.sm
    },
    desktop: {
      padding: '1.5rem',
      borderRadius: '12px',
      boxShadow: shadows.md
    }
  },

  // Button responsive styles
  button: {
    mobile: {
      padding: '0.75rem 1.5rem',
      fontSize: '1rem',
      minHeight: '48px', // Touch-friendly
      borderRadius: '8px'
    },
    desktop: {
      padding: '0.75rem 2rem',
      fontSize: '1rem',
      minHeight: '44px',
      borderRadius: '10px'
    }
  },

  // Form responsive styles
  form: {
    mobile: {
      gap: '1rem'
    },
    desktop: {
      gap: '1.5rem'
    }
  },

  // Input responsive styles
  input: {
    mobile: {
      padding: '0.875rem 1rem',
      fontSize: '16px', // Prevents zoom on iOS
      borderRadius: '8px',
      minHeight: '48px'
    },
    desktop: {
      padding: '0.75rem 1rem',
      fontSize: '1rem',
      borderRadius: '8px',
      minHeight: '44px'
    }
  },

  // Table responsive styles
  table: {
    mobile: {
      display: 'block',
      overflowX: 'auto',
      whiteSpace: 'nowrap',
      WebkitOverflowScrolling: 'touch'
    },
    desktop: {
      display: 'table',
      width: '100%'
    }
  }
};

// Utility function to get responsive styles based on screen size
export const getResponsiveStyle = (styles, device = 'mobile') => {
  if (typeof window === 'undefined') return styles.mobile || {};
  
  const width = window.innerWidth;
  
  if (width <= parseInt(breakpoints.mobile)) {
    return styles.mobile || {};
  } else if (width <= parseInt(breakpoints.desktop)) {
    return styles.tablet || styles.mobile || {};
  } else {
    return styles.desktop || styles.tablet || styles.mobile || {};
  }
};

// Touch-friendly styles for mobile devices
export const touchStyles = {
  minTouchTarget: {
    minHeight: '44px',
    minWidth: '44px'
  },
  largeTouchTarget: {
    minHeight: '48px',
    minWidth: '48px'
  },
  touchButton: {
    padding: '0.75rem 1.5rem',
    fontSize: '1rem',
    fontWeight: '600',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    userSelect: 'none',
    WebkitTapHighlightColor: 'transparent'
  }
};
