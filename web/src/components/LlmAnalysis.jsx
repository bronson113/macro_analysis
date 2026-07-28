import React, { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { buildMarkdownUrl } from '../utils/markdownSource';

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
      <div className="section-header">
        <div>
          <p className="section-kicker">Priority View</p>
          <h2 id="llm-analysis-heading">LLM Analysis</h2>
        </div>
      </div>
      <div className="glass-panel llm-analysis-panel">
        {loading && <p className="text-secondary">Loading LLM analysis...</p>}
        {!loading && error && <p className="text-secondary">{error}</p>}
        {!loading && !error && (
          <div className="markdown-body">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          </div>
        )}
      </div>
    </section>
  );
};

export default LlmAnalysis;
