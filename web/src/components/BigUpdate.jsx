import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { splitReportSections } from '../utils/dashboardPresentation';

const latestReport = { date: '', path: '/latest_report.md' };

const BigUpdate = ({ reports = [] }) => {
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedDate, setSelectedDate] = useState('');
  const [reportError, setReportError] = useState('');
  const [activeTab, setActiveTab] = useState('summary');
  const dateInputRef = useRef(null);

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

  const newestDate = reports[0]?.date || '';
  const oldestDate = reports[reports.length - 1]?.date || '';
  const displayedDate = selectedDate || newestDate;
  const reportSections = splitReportSections(content);
  const reportTabs = [
    { id: 'summary', label: 'Summary', content: reportSections.summary },
    { id: 'active', label: 'Active Situation', content: reportSections.active },
    { id: 'risks', label: 'Risks', content: reportSections.risks },
    { id: 'full', label: 'Full Report', content: reportSections.full },
  ].filter(tab => tab.content);
  const visibleTab = reportTabs.some(tab => tab.id === activeTab) ? activeTab : 'summary';
  const activeContent = reportTabs.find(tab => tab.id === visibleTab)?.content || content;

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
          <h2 id="big-update-heading">The Big Update</h2>
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
              <div className="report-tabs" role="tablist" aria-label="Big Update report sections">
                {reportTabs.map(tab => (
                  <button
                    key={tab.id}
                    className={`report-tab ${visibleTab === tab.id ? 'active' : ''}`}
                    type="button"
                    role="tab"
                    aria-selected={visibleTab === tab.id}
                    onClick={() => setActiveTab(tab.id)}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
              <div className={`markdown-body report-tab-body ${visibleTab === 'full' ? 'full-report' : ''}`} role="tabpanel">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{activeContent}</ReactMarkdown>
              </div>
              <button className="link-button" onClick={() => setIsModalOpen(true)}>
                Open Expanded Report &rarr;
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
