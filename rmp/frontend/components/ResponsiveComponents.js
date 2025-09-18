import { useState, useEffect } from 'react';
import { mobileStyles, getResponsiveStyle, touchStyles } from '../styles/globalStyles';

const ResponsiveInput = ({ 
  type = 'text', 
  placeholder, 
  value, 
  onChange, 
  onFocus,
  onBlur,
  required = false,
  ...props 
}) => {
  const [isMobile, setIsMobile] = useState(false);
  const [isFocused, setIsFocused] = useState(false);

  useEffect(() => {
    const checkDevice = () => {
      setIsMobile(window.innerWidth <= 767);
    };
    
    checkDevice();
    window.addEventListener('resize', checkDevice);
    return () => window.removeEventListener('resize', checkDevice);
  }, []);

  const inputStyles = {
    width: '100%',
    padding: isMobile ? '0.875rem 1rem' : '0.75rem 1rem',
    fontSize: isMobile ? '16px' : '1rem', // Prevents zoom on iOS
    border: `2px solid ${isFocused ? '#667eea' : '#e2e8f0'}`,
    borderRadius: '8px',
    outline: 'none',
    backgroundColor: 'white',
    transition: 'all 0.2s ease',
    minHeight: isMobile ? '48px' : '44px',
    boxShadow: isFocused ? '0 0 0 3px rgba(102, 126, 234, 0.1)' : 'none',
    ...props.style
  };

  const handleFocus = (e) => {
    setIsFocused(true);
    if (onFocus) onFocus(e);
  };

  const handleBlur = (e) => {
    setIsFocused(false);
    if (onBlur) onBlur(e);
  };

  return (
    <input
      type={type}
      placeholder={placeholder}
      value={value}
      onChange={onChange}
      onFocus={handleFocus}
      onBlur={handleBlur}
      required={required}
      style={inputStyles}
      {...props}
    />
  );
};

const ResponsiveButton = ({ 
  children, 
  onClick, 
  type = 'button', 
  variant = 'primary', 
  disabled = false, 
  ...props 
}) => {
  const [isMobile, setIsMobile] = useState(false);
  const [isPressed, setIsPressed] = useState(false);

  useEffect(() => {
    const checkDevice = () => {
      setIsMobile(window.innerWidth <= 767);
    };
    
    checkDevice();
    window.addEventListener('resize', checkDevice);
    return () => window.removeEventListener('resize', checkDevice);
  }, []);

  const getVariantStyles = () => {
    switch (variant) {
      case 'primary':
        return {
          backgroundColor: disabled ? '#94a3b8' : '#667eea',
          color: 'white',
          border: 'none'
        };
      case 'secondary':
        return {
          backgroundColor: disabled ? '#f1f5f9' : 'white',
          color: disabled ? '#94a3b8' : '#334155',
          border: `2px solid ${disabled ? '#e2e8f0' : '#e2e8f0'}`
        };
      case 'success':
        return {
          backgroundColor: disabled ? '#94a3b8' : '#22c55e',
          color: 'white',
          border: 'none'
        };
      case 'danger':
        return {
          backgroundColor: disabled ? '#94a3b8' : '#ef4444',
          color: 'white',
          border: 'none'
        };
      default:
        return {
          backgroundColor: disabled ? '#94a3b8' : '#667eea',
          color: 'white',
          border: 'none'
        };
    }
  };

  const buttonStyles = {
    padding: isMobile ? '0.875rem 1.5rem' : '0.75rem 2rem',
    fontSize: isMobile ? '1rem' : '1rem',
    fontWeight: '600',
    borderRadius: '8px',
    cursor: disabled ? 'not-allowed' : 'pointer',
    transition: 'all 0.2s ease',
    minHeight: isMobile ? '48px' : '44px',
    minWidth: isMobile ? '48px' : '44px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    userSelect: 'none',
    WebkitTapHighlightColor: 'transparent',
    transform: isPressed ? 'scale(0.98)' : 'scale(1)',
    ...getVariantStyles(),
    ...props.style
  };

  const handleMouseDown = () => setIsPressed(true);
  const handleMouseUp = () => setIsPressed(false);
  const handleMouseLeave = () => setIsPressed(false);

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      style={buttonStyles}
      onMouseDown={handleMouseDown}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseLeave}
      {...props}
    >
      {children}
    </button>
  );
};

const ResponsiveCard = ({ children, ...props }) => {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkDevice = () => {
      setIsMobile(window.innerWidth <= 767);
    };
    
    checkDevice();
    window.addEventListener('resize', checkDevice);
    return () => window.removeEventListener('resize', checkDevice);
  }, []);

  const cardStyles = {
    backgroundColor: 'white',
    borderRadius: isMobile ? '8px' : '12px',
    padding: isMobile ? '1rem' : '1.5rem',
    boxShadow: isMobile ? '0 1px 3px rgba(0, 0, 0, 0.1)' : '0 4px 6px rgba(0, 0, 0, 0.1)',
    border: '1px solid #e2e8f0',
    transition: 'all 0.2s ease',
    ...props.style
  };

  return (
    <div style={cardStyles} {...props}>
      {children}
    </div>
  );
};

const ResponsiveGrid = ({ children, columns = { mobile: 1, tablet: 2, desktop: 3 }, gap = '1rem', ...props }) => {
  const [isMobile, setIsMobile] = useState(false);
  const [isTablet, setIsTablet] = useState(false);

  useEffect(() => {
    const checkDevice = () => {
      const width = window.innerWidth;
      setIsMobile(width <= 767);
      setIsTablet(width > 767 && width <= 1023);
    };
    
    checkDevice();
    window.addEventListener('resize', checkDevice);
    return () => window.removeEventListener('resize', checkDevice);
  }, []);

  const getGridColumns = () => {
    if (isMobile) return columns.mobile;
    if (isTablet) return columns.tablet;
    return columns.desktop;
  };

  const gridStyles = {
    display: 'grid',
    gridTemplateColumns: `repeat(${getGridColumns()}, 1fr)`,
    gap: gap,
    width: '100%',
    ...props.style
  };

  return (
    <div style={gridStyles} {...props}>
      {children}
    </div>
  );
};

export { ResponsiveInput, ResponsiveButton, ResponsiveCard, ResponsiveGrid };
