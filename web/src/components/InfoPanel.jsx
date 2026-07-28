import React, { useId, useState } from 'react';

const InfoPanel = ({ title, description }) => {
  const [isOpen, setIsOpen] = useState(false);
  const titleId = useId();

  if (!description) return null;

  return (
    <>
      <button 
        className="info-icon-btn" 
        type="button"
        onClick={(e) => { e.stopPropagation(); setIsOpen(true); }}
        title={`Learn about ${title}`}
      >
        &#9432;
      </button>

      {isOpen && (
        <div className="modal-overlay" onClick={(e) => { e.stopPropagation(); setIsOpen(false); }}>
          <div className="modal-content info-panel-content" role="dialog" aria-modal="true" aria-labelledby={titleId} onClick={e => e.stopPropagation()}>
            <button className="modal-close" type="button" aria-label={`Close ${title} details`} onClick={() => setIsOpen(false)}>&#x2715;</button>
            <h3 id={titleId} className="dialog-title">{title}</h3>
            <p className="dialog-copy">
              {description}
            </p>
          </div>
        </div>
      )}
    </>
  );
};

export default InfoPanel;
