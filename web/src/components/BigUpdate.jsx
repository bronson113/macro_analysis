import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const latestReport = { date: '', path: '/latest_report.md' };

const BigUpdate = () => {
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [reports, setReports] = useState([]);
  const [selectedDate, setSelectedDate] = useState('');
  const [reportError, setReportError] = useState('');
  const dateInputRef = useRef(null);

  useEffect(() => {
    fetch(import.meta.env.BASE_URL + 'reports/index.json?t=' + new Date().getTime())
      .then(res => {
        if (!res.ok) throw new Error('Failed to load report history.');
        return res.json();
      })
      .then(json => {
        setReports(Array.isArray(json) ? json : []);
      })
      .catch(err => {
        console.error(err);
        setReports([]);
      });
  }, []);

  useEffect(() => {
    const selectedReport = reports.find(report => report.date === selectedDate) || latestReport;
    const isLatest = !selectedDate;

    const fetchReport = () => {
      setReportError('');
      fetch(import.meta.env.BASE_URL + selectedReport.path + '?t=' + new Date().getTime())
        .then(res => {
          if (!res.ok) throw new Error('Failed to load the selected report.');
          return res.text();
        })
        .then(text => {
          setContent(text);
          setLoading(false);
        })
        .catch(err => {
          console.error(err);
          setContent('');
          setReportError(err.message);
          setLoading(false);
        });
    };

    setLoading(true);
    fetchReport();
    if (!isLatest) return undefined;

    const interval = setInterval(fetchReport, 60000); // refresh every minute
    return () => clearInterval(interval);
  }, [reports, selectedDate]);

  if (loading) return <div className="glass-panel text-muted">Loading Big Update...</div>;

  // Extract just the summary section.
  let summary = content;
  const splitPoint = content.indexOf('## 1. Active Macro Situation');
  if (splitPoint !== -1) {
    summary = content.substring(0, splitPoint);
  }

  const newestDate = reports[0]?.date || '';
  const oldestDate = reports[reports.length - 1]?.date || '';
  const displayedDate = selectedDate || newestDate;

  const selectReportDate = nextDate => {
    if (!nextDate || nextDate === newestDate) {
      setSelectedDate('');
      return;
    }

    const matchingReport = reports.find(report => report.date === nextDate);
    if (!matchingReport) {
      setReportError(`No Big Update report is available for ${nextDate}.`);
      return;
    }

    setSelectedDate(nextDate);
  };

  const handleDateChange = event => {
    selectReportDate(event.target.value);
  };

  const handleLoadSelectedDate = () => {
    selectReportDate(dateInputRef.current?.value || '');
  };

  return (
    <>
      <div className="section animate-fade-in stagger-2">
        <div className="section-header big-update-header">
          <h2>The Big Update</h2>
          <div className="report-date-picker">
            <label htmlFor="report-date">Report date</label>
            <input
              id="report-date"
              ref={dateInputRef}
              type="date"
              value={displayedDate}
              min={oldestDate}
              max={newestDate}
              onInput={handleDateChange}
              onChange={handleDateChange}
              disabled={!reports.length}
            />
            <button className="range-btn" onClick={handleLoadSelectedDate} disabled={!reports.length}>
              Load
            </button>
            {selectedDate && (
              <button className="range-btn" onClick={() => setSelectedDate('')}>
                Latest
              </button>
            )}
          </div>
        </div>
        <div className="glass-panel">
          {reportError ? (
            <p className="text-secondary">{reportError}</p>
          ) : (
            <>
              <div className="markdown-body">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{summary}</ReactMarkdown>
              </div>
              <button className="link-button" onClick={() => setIsModalOpen(true)}>
                Read Full Report &rarr;
              </button>
            </>
          )}
        </div>
      </div>

      {isModalOpen && !reportError && (
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
