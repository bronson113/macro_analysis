import React, { useEffect, useState } from 'react';
import { buildMarkdownUrl } from '../utils/markdownSource';
import MarkdownContent from './MarkdownComponents';

const EditorialReview = () => {
  const [review, setReview] = useState({ status: 'loading', content: '' });

  useEffect(() => {
    let isActive = true;

    const loadReview = async () => {
      try {
        const response = await fetch(
          buildMarkdownUrl(import.meta.env.BASE_URL, 'llm_analysis.md', Date.now()),
        );
        if (!isActive) return;

        if (response.status === 404) {
          setReview({ status: 'unavailable', content: '' });
          return;
        }
        if (!response.ok) throw new Error('Unable to load the editorial review.');

        setReview({ status: 'ready', content: await response.text() });
      } catch {
        if (isActive) setReview({ status: 'error', content: '' });
      }
    };

    loadReview();
    const interval = setInterval(loadReview, 60000);
    return () => {
      isActive = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <section className="section animate-fade-in editorial-review" aria-labelledby="editorial-review-heading">
      <div className="dark-panel editorial-review-panel">
        <p className="feature-eyebrow">Cowork editorial</p>
        <h2 id="editorial-review-heading">Editorial interpretation of current evidence</h2>
        <p className="feature-deck">A dated research note that separates the published evidence from its editorial interpretation.</p>
        {review.status === 'loading' && <p className="text-secondary">Loading editorial review...</p>}
        {review.status === 'unavailable' && <p className="text-secondary">No editorial review has been published for the current evidence update.</p>}
        {review.status === 'error' && <p className="text-secondary">The editorial review could not be loaded.</p>}
        {review.status === 'ready' && (
          <div className="markdown-body">
            <MarkdownContent content={review.content} />
          </div>
        )}
      </div>
    </section>
  );
};

export default EditorialReview;
