import React, { useEffect, useState } from 'react';
import { buildMarkdownUrl } from '../utils/markdownSource';
import MarkdownContent from './MarkdownComponents';

const LlmAnalysis = () => {
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadAnalysis = () => {
      fetch(buildMarkdownUrl(import.meta.env.BASE_URL, 'llm_analysis.md', Date.now()))
        .then(response => {
          if (!response.ok) throw new Error('The LLM analysis has not been published yet.');
          return response.text();
        })
        .then(text => {
          setContent(text);
          setError('');
          setLoading(false);
        })
        .catch(loadError => {
          console.error(loadError);
          setError(loadError.message);
          setLoading(false);
        });
    };

    loadAnalysis();
    const interval = setInterval(loadAnalysis, 60000);
    return () => clearInterval(interval);
  }, []);

  return (
    <section className="section animate-fade-in llm-analysis" aria-labelledby="llm-analysis-heading">
      <div className="dark-panel llm-analysis-panel">
        <p className="feature-eyebrow">Priority View</p>
        <h2 id="llm-analysis-heading">Market signal, distilled</h2>
        <p className="feature-deck">A live synthesis of the macro signals most likely to shape today’s market regime.</p>
        {loading && <p className="text-secondary">Loading LLM analysis...</p>}
        {!loading && error && <p className="text-secondary">{error}</p>}
        {!loading && !error && (
          <div className="markdown-body">
            <MarkdownContent content={content} />
          </div>
        )}
      </div>
    </section>
  );
};

export default LlmAnalysis;
