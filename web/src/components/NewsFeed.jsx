import React from 'react';

function getTopicTags(topicTags) {
  if (Array.isArray(topicTags)) return topicTags;
  if (typeof topicTags !== 'string') return [];

  try {
    const parsed = JSON.parse(topicTags);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return topicTags.split(',').map(tag => tag.trim()).filter(Boolean);
  }
}

const NewsFeed = ({ newsEvents = [] }) => {
  if (!newsEvents.length) return null;

  return (
    <div className="section animate-fade-in stagger-3">
      <div className="section-header">
        <h2>Recent Macro News</h2>
      </div>
      <div className="news-list glass-panel">
        {newsEvents.map((item, i) => {
          const articleUrl = item.url || item.link;
          const itemKey = item.id || item.url || item.link || `${item.date}-${item.title || i}`;
          const topicTags = getTopicTags(item.topic_tags);

          return (
          <article key={itemKey} className="news-item">
            <div className="news-item-header">
              <span className="text-muted">{new Date(item.date).toLocaleString()}</span>
              {item.source && <span className="news-source">{item.source}</span>}
            </div>
            <h3 className="news-item-title">{item.title}</h3>
            <div className="news-item-body">{item.summary}</div>
            <div className="news-context" aria-label="News context">
              <span className="news-context-label">Uninterpreted context</span>
              {topicTags.map(tag => <span className="news-topic-tag" key={tag}>{tag.replaceAll('_', ' ')}</span>)}
            </div>
            {articleUrl && (
              <a className="news-item-link" href={articleUrl} target="_blank" rel="noopener noreferrer">
                Read Article &rarr;
              </a>
            )}
          </article>
          );
        })}
      </div>
    </div>
  );
};

export default NewsFeed;
