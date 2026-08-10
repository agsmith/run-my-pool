import { useState, useEffect } from 'react';

const ResponsiveTable = ({ 
  columns, 
  data, 
  onRowClick,
  className = '',
  ...props 
}) => {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkDevice = () => {
      setIsMobile(window.innerWidth <= 767);
    };
    
    checkDevice();
    window.addEventListener('resize', checkDevice);
    return () => window.removeEventListener('resize', checkDevice);
  }, []);

  if (isMobile) {
    // Mobile card layout
    return (
      <div className={className} {...props}>
        {data.map((row, rowIndex) => (
          <div
            key={rowIndex}
            style={{
              backgroundColor: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              padding: '1rem',
              marginBottom: '1rem',
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
              cursor: onRowClick ? 'pointer' : 'default'
            }}
            onClick={() => onRowClick && onRowClick(row, rowIndex)}
          >
            {columns.map((column, colIndex) => (
              <div key={colIndex} style={{ marginBottom: colIndex === columns.length - 1 ? 0 : '0.75rem' }}>
                <div style={{
                  fontSize: '0.875rem',
                  fontWeight: '600',
                  color: '#6b7280',
                  marginBottom: '0.25rem'
                }}>
                  {column.header}
                </div>
                <div style={{
                  fontSize: '1rem',
                  color: '#1f2937'
                }}>
                  {column.render ? column.render(row[column.key], row, rowIndex) : row[column.key]}
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>
    );
  }

  // Desktop table layout
  return (
    <div style={{ overflowX: 'auto', WebkitOverflowScrolling: 'touch' }} className={className} {...props}>
      <table style={{
        width: '100%',
        borderCollapse: 'collapse',
        backgroundColor: 'white',
        borderRadius: '8px',
        overflow: 'hidden',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
      }}>
        <thead>
          <tr style={{ backgroundColor: '#f8fafc' }}>
            {columns.map((column, index) => (
              <th key={index} style={{
                padding: '1rem',
                textAlign: 'left',
                fontSize: '0.875rem',
                fontWeight: '600',
                color: '#374151',
                borderBottom: '1px solid #e5e7eb'
              }}>
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, rowIndex) => (
            <tr 
              key={rowIndex}
              style={{
                borderBottom: rowIndex === data.length - 1 ? 'none' : '1px solid #f3f4f6',
                cursor: onRowClick ? 'pointer' : 'default'
              }}
              onClick={() => onRowClick && onRowClick(row, rowIndex)}
              onMouseEnter={(e) => {
                if (onRowClick) {
                  e.currentTarget.style.backgroundColor = '#f8fafc';
                }
              }}
              onMouseLeave={(e) => {
                if (onRowClick) {
                  e.currentTarget.style.backgroundColor = 'white';
                }
              }}
            >
              {columns.map((column, colIndex) => (
                <td key={colIndex} style={{
                  padding: '1rem',
                  fontSize: '0.875rem',
                  color: '#1f2937'
                }}>
                  {column.render ? column.render(row[column.key], row, rowIndex) : row[column.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const ResponsiveModal = ({ isOpen, onClose, title, children, className = '', ...props }) => {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkDevice = () => {
      setIsMobile(window.innerWidth <= 767);
    };
    
    checkDevice();
    window.addEventListener('resize', checkDevice);
    return () => window.removeEventListener('resize', checkDevice);
  }, []);

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }

    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const overlayStyles = {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    display: 'flex',
    alignItems: isMobile ? 'flex-end' : 'center',
    justifyContent: 'center',
    padding: isMobile ? 0 : '1rem',
    zIndex: 1000
  };

  const modalStyles = {
    backgroundColor: 'white',
    borderRadius: isMobile ? '12px 12px 0 0' : '12px',
    boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
    width: '100%',
    maxWidth: isMobile ? '100%' : '500px',
    maxHeight: isMobile ? '90vh' : '80vh',
    display: 'flex',
    flexDirection: 'column',
    animation: isMobile ? 'slideUp 0.3s ease-out' : 'fadeIn 0.3s ease-out'
  };

  const headerStyles = {
    padding: '1.5rem',
    borderBottom: '1px solid #e5e7eb',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between'
  };

  const titleStyles = {
    fontSize: '1.25rem',
    fontWeight: '600',
    color: '#1f2937',
    margin: 0
  };

  const closeButtonStyles = {
    background: 'none',
    border: 'none',
    fontSize: '1.5rem',
    cursor: 'pointer',
    color: '#6b7280',
    padding: '0.25rem',
    borderRadius: '4px',
    minHeight: '44px',
    minWidth: '44px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center'
  };

  const contentStyles = {
    padding: '1.5rem',
    overflowY: 'auto',
    flex: 1
  };

  return (
    <div style={overlayStyles} onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`responsive-modal ${className}`.trim()} style={modalStyles} {...props}>
        <div className="responsive-modal__header" style={headerStyles}>
          <h2 className="responsive-modal__title" style={titleStyles}>{title}</h2>
          <button
            style={closeButtonStyles}
            onClick={onClose}
            onMouseEnter={(e) => e.target.style.backgroundColor = '#f3f4f6'}
            onMouseLeave={(e) => e.target.style.backgroundColor = 'transparent'}
          >
            ✕
          </button>
        </div>
        <div className="responsive-modal__content" style={contentStyles}>
          {children}
        </div>
      </div>
      <style jsx>{`
        @keyframes slideUp {
          from {
            transform: translateY(100%);
          }
          to {
            transform: translateY(0);
          }
        }
        
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: scale(0.95);
          }
          to {
            opacity: 1;
            transform: scale(1);
          }
        }
      `}</style>
    </div>
  );
};

const ResponsiveTabs = ({ tabs, activeTab, onTabChange, ...props }) => {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkDevice = () => {
      setIsMobile(window.innerWidth <= 767);
    };
    
    checkDevice();
    window.addEventListener('resize', checkDevice);
    return () => window.removeEventListener('resize', checkDevice);
  }, []);

  const tabsContainerStyles = {
    borderBottom: '1px solid #e5e7eb',
    marginBottom: '1.5rem',
    overflowX: isMobile ? 'auto' : 'visible',
    WebkitOverflowScrolling: 'touch'
  };

  const tabsListStyles = {
    display: 'flex',
    gap: isMobile ? '0' : '1rem',
    minWidth: isMobile ? 'max-content' : 'auto'
  };

  const tabStyles = (isActive) => ({
    padding: isMobile ? '0.75rem 1rem' : '0.75rem 1.5rem',
    border: 'none',
    backgroundColor: 'transparent',
    cursor: 'pointer',
    fontSize: '0.875rem',
    fontWeight: '600',
    color: isActive ? '#667eea' : '#6b7280',
    borderBottom: isActive ? '2px solid #667eea' : '2px solid transparent',
    transition: 'all 0.2s ease',
    whiteSpace: 'nowrap',
    minHeight: '44px',
    display: 'flex',
    alignItems: 'center'
  });

  return (
    <div {...props}>
      <div style={tabsContainerStyles}>
        <div style={tabsListStyles}>
          {tabs.map((tab) => (
            <button
              key={tab.id}
              style={tabStyles(activeTab === tab.id)}
              onClick={() => onTabChange(tab.id)}
              onMouseEnter={(e) => {
                if (activeTab !== tab.id) {
                  e.target.style.color = '#374151';
                }
              }}
              onMouseLeave={(e) => {
                if (activeTab !== tab.id) {
                  e.target.style.color = '#6b7280';
                }
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>
      <div>
        {tabs.find(tab => tab.id === activeTab)?.content}
      </div>
    </div>
  );
};

export { ResponsiveTable, ResponsiveModal, ResponsiveTabs };
