import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const BigUpdate = () => {
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);

  useEffect(() => {
    const fetchReport = () => {
      fetch('/latest_report.md?t=' + new Date().getTime())
        .then(res => res.text())
        .then(text => {
          setContent(text);
          setLoading(false);
        })
        .catch(err => {
          console.error(err);
          setContent('Failed to load the latest report.');
          setLoading(false);
        });
    };

    fetchReport();
    const interval = setInterval(fetchReport, 60000); // refresh every minute
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div className="glass-panel text-muted">Loading Big Update...</div>;

  // Extract just the summary section.
  let summary = content;
  const splitPoint = content.indexOf('## 1. Active Macro Situation');
  if (splitPoint !== -1) {
    summary = content.substring(0, splitPoint);
  }

  return (
    <>
      <div className="section animate-fade-in stagger-2">
        <div className="section-header">
          <h2>The Big Update</h2>
        </div>
        <div className="glass-panel">
          <div className="markdown-body">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{summary}</ReactMarkdown>
          </div>
          <button className="link-button" onClick={() => setIsModalOpen(true)}>
            Read Full Report &rarr;
          </button>
        </div>
      </div>

      {isModalOpen && (
        <div className="modal-overlay" onClick={() => setIsModalOpen(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setIsModalOpen(false)}>
              &#x2715;
            </button>
            <div className="markdown-body">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default BigUpdate;
