import React from 'react';
import InfoPanel from './InfoPanel';

const StatCard = ({ title, value, date, unit = '', format = 'number', description }) => {
  let displayValue = value;
  
  if (value !== undefined && value !== null) {
    if (format === 'currency') {
      displayValue = '$' + Number(value).toLocaleString();
    } else if (format === 'percent') {
      displayValue = Number(value).toFixed(2) + '%';
    } else if (format === 'number') {
      displayValue = Number(value).toLocaleString();
    }
  } else {
    displayValue = 'N/A';
  }

  // Determine color based on common macro metrics (naive approach for visual effect)
  let valClass = '';
  if (format === 'percent') {
    if (value > 2) valClass = 'negative'; // high yield/inflation bad
    if (value < 0) valClass = 'positive'; // low spreads good
  }

  return (
    <div className="glass-panel interactive stat-card animate-fade-in stagger-2">
      <div className="stat-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>{title}</span>
        <InfoPanel title={title} description={description} />
      </div>
      <div className={`stat-value ${valClass}`}>
        {displayValue} <span style={{ fontSize: '1rem', color: 'var(--text-secondary)' }}>{unit}</span>
      </div>
      <div className="stat-date">As of {date || 'Unknown Date'}</div>
    </div>
  );
};

export default StatCard;
