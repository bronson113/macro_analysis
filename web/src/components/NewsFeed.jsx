import React from 'react';

const NewsFeed = ({ newsEvents = [] }) => {
  if (!newsEvents.length) return null;

  return (
    <div className="section animate-fade-in stagger-3">
      <div className="section-header">
        <h2>Recent Macro News</h2>
      </div>
      <div className="news-list glass-panel">
        {newsEvents.map((item, i) => (
          <div key={i} className="news-item">
            <div className="news-item-header">
              <span className="text-muted">{new Date(item.date).toLocaleString()}</span>
              {item.source && <span className="accent-text" style={{ color: 'var(--accent-primary)' }}>{item.source}</span>}
            </div>
            <div className="news-item-title">{item.title}</div>
            <div className="news-item-body">{item.summary}</div>
            {item.url && (
              <a href={item.url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--accent-secondary)', fontSize: '0.875rem', textDecoration: 'none' }}>
                Read Article &rarr;
              </a>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default NewsFeed;
