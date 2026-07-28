import React, { useCallback, useId, useRef, useState } from 'react';
import { useDialogFocus } from '../hooks/useDialogFocus';

const InfoPanel = ({ title, description }) => {
  const [isOpen, setIsOpen] = useState(false);
  const titleId = useId();
  const dialogRef = useRef(null);
  const closeButtonRef = useRef(null);
  const closePanel = useCallback(() => setIsOpen(false), []);

  useDialogFocus({
    isOpen,
    onClose: closePanel,
    dialogRef,
    initialFocusRef: closeButtonRef,
  });

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
        <div className="modal-overlay" onClick={closePanel}>
          <div className="modal-content info-panel-content" ref={dialogRef} tabIndex="-1" role="dialog" aria-modal="true" aria-labelledby={titleId} onClick={e => e.stopPropagation()}>
            <button className="modal-close" ref={closeButtonRef} type="button" aria-label={`Close ${title} details`} onClick={closePanel}>&#x2715;</button>
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
