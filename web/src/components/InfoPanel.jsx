import React, { useState } from 'react';

const InfoPanel = ({ title, description }) => {
  const [isOpen, setIsOpen] = useState(false);

  if (!description) return null;

  return (
    <>
      <button 
        className="info-icon-btn" 
        onClick={(e) => { e.stopPropagation(); setIsOpen(true); }}
        title={`Learn about ${title}`}
      >
        &#9432;
      </button>

      {isOpen && (
        <div className="modal-overlay" onClick={(e) => { e.stopPropagation(); setIsOpen(false); }}>
          <div className="modal-content info-panel-content" onClick={e => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setIsOpen(false)}>&#x2715;</button>
            <h3 style={{ marginBottom: '1rem', color: 'var(--accent-primary)' }}>{title}</h3>
            <p style={{ color: 'var(--text-secondary)', lineHeight: '1.6' }}>
              {description}
            </p>
          </div>
        </div>
      )}
    </>
  );
};

export default InfoPanel;
