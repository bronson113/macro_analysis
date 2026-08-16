import React, { useRef } from 'react';
import { useDialogFocus } from '../hooks/useDialogFocus';

const CheatSheet = ({ isOpen, onClose }) => {
  const dialogRef = useRef(null);
  const closeButtonRef = useRef(null);

  useDialogFocus({
    isOpen,
    onClose,
    dialogRef,
    initialFocusRef: closeButtonRef,
  });

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content cheat-sheet-content" ref={dialogRef} tabIndex="-1" role="dialog" aria-modal="true" aria-labelledby="cheat-sheet-title" onClick={e => e.stopPropagation()}>
        <button className="modal-close" ref={closeButtonRef} type="button" aria-label="Close cheat sheet" onClick={onClose}>&#x2715;</button>
        <h2 id="cheat-sheet-title" className="dialog-title">Defiant Gatekeeper Cheat Sheet</h2>
        
        <p className="text-secondary cheat-sheet-intro">
          This dashboard tracks macro indicators based on the 4-Quadrant Macro framework popularized by the{' '}
          <a href="https://www.youtube.com/@DefiantGatekeeper" target="_blank" rel="noopener noreferrer">
            Defiant Gatekeeper YouTube Channel
          </a>.
        </p>

        <h3 className="cheat-sheet-heading">The 4 Macro Situations</h3>
        <p className="text-secondary cheat-sheet-copy">
          The framework operates on a 2x2 matrix: <strong>Accommodative / Restrictive × Abundant / Scarce</strong>. These are current levels, not recent directions; momentum and market expectations are reported separately.
        </p>

        <div className="matrix-grid">
          <div className="glass-panel situation-card">
            <h4 className="positive">Situation 1 (Top Left)</h4>
            <div className="situation-detail"><strong>Policy level:</strong> Accommodative</div>
            <div className="situation-detail situation-detail-last"><strong>Liquidity level:</strong> Abundant</div>
            <p className="situation-summary">
              <strong>Risk-Liquidity Tailwind.</strong> Historically favors profitable technology, AI infrastructure, semiconductors, and consumer discretionary (if labor isn't breaking).
            </p>
          </div>
          
          <div className="glass-panel situation-card">
            <h4 className="warning">Situation 2 (Top Right)</h4>
            <div className="situation-detail"><strong>Policy level:</strong> Accommodative</div>
            <div className="situation-detail situation-detail-last"><strong>Liquidity level:</strong> Scarce</div>
            <p className="situation-summary">
              <strong>Late-Cycle Caution.</strong> The Fed may be easing because growth/labor is weakening while liquidity is still tight. Favors defensive sectors (Healthcare, Staples, Gold).
            </p>
          </div>

          <div className="glass-panel situation-card">
            <h4 className="warning">Situation 4 (Bottom Left)</h4>
            <div className="situation-detail"><strong>Policy level:</strong> Restrictive</div>
            <div className="situation-detail situation-detail-last"><strong>Liquidity level:</strong> Abundant</div>
            <p className="situation-summary">
              <strong>Policy/Liquidity Conflict.</strong> Policy is restrictive while reserve liquidity remains historically abundant. Favors hard assets, commodity producers, energy, and inflation-linked cash flows only when independent evidence confirms.
            </p>
          </div>

          <div className="glass-panel situation-card">
            <h4 className="negative">Situation 3 (Bottom Right)</h4>
            <div className="situation-detail"><strong>Policy level:</strong> Restrictive</div>
            <div className="situation-detail situation-detail-last"><strong>Liquidity level:</strong> Scarce</div>
            <p className="situation-summary">
              <strong>Restrictive Liquidity.</strong> High multiple-compression risk. Cash and T-bills are competitive. Long-duration growth stocks face severe headwinds.
            </p>
          </div>
        </div>

        <h3 className="cheat-sheet-heading">Important Definitions</h3>
        <ul className="text-secondary cheat-sheet-definitions">
          <li><strong>Policy level:</strong> Compare the real policy rate with the neutral real rate (r-star). The real-policy gap is <em>real policy rate − r-star</em>; above +0.50 percentage points is restrictive, below -0.50 points is accommodative, and the middle band is neutral.</li>
          <li><strong>Reserve-liquidity level:</strong> The proxy is Fed Assets − TGA Balance − ON RRP, normalized as a share of nominal GDP. Compare it with the trailing historical distribution: scarce at-or-below P40 and abundant at-or-above P60. This is history-relative, not a 30-day direction label.</li>
          <li><strong>Momentum:</strong> Show policy and liquidity separately at both 30 days and 90 days. Easing or deteriorating momentum can coexist with a high current level and cannot change the current quadrant.</li>
          <li><strong>Consensus:</strong> An optional forward-looking survey overlay reports expected policy and, when available, the Fed balance-sheet path. Unavailable or stale consensus leaves the current level-based quadrant unchanged.</li>
          <li><strong>High-but-falling example:</strong> A restrictive policy level plus an abundant liquidity level is <strong>Situation 4</strong> even when policy momentum is easing and liquidity momentum is deteriorating. Report those falling overlays separately.</li>
        </ul>
      </div>
    </div>
  );
};

export default CheatSheet;
