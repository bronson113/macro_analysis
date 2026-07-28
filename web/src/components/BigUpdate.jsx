import React, { useState, useEffect, useId, useRef } from 'react';
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
  const reportId = useId();

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

  const markdownComponents = {
    table: ({ children }) => <div className="markdown-table-scroll"><table>{children}</table></div>,
  };

  return (
    <>
      <section className="section animate-fade-in stagger-2" aria-labelledby="big-update-heading">
        <div className="section-header big-update-header">
          <div>
            <p className="section-kicker">Daily Brief</p>
            <h2 id="big-update-heading">The Big Update</h2>
          </div>
          <div className="report-date-picker">
            <label htmlFor="report-date">Date</label>
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
            <button className="range-btn" type="button" onClick={handleLoadSelectedDate} disabled={!reports.length}>
              Load
            </button>
            {selectedDate && (
              <button className="range-btn" type="button" onClick={() => setSelectedDate('')}>
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
                    id={`${reportId}-${tab.id}-tab`}
                    aria-selected={visibleTab === tab.id}
                    aria-controls={`${reportId}-${tab.id}-panel`}
                    onClick={() => setActiveTab(tab.id)}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
              <div
                className={`markdown-body report-tab-body ${visibleTab === 'full' ? 'full-report' : ''}`}
                id={`${reportId}-${visibleTab}-panel`}
                role="tabpanel"
                aria-labelledby={`${reportId}-${visibleTab}-tab`}
              >
                <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>{activeContent}</ReactMarkdown>
              </div>
              <button className="link-button" type="button" onClick={() => setIsModalOpen(true)}>
                Open Expanded Report &rarr;
              </button>
            </>
          )}
        </div>
      </section>

      {isModalOpen && !reportError && (
        <div className="modal-overlay" onClick={() => setIsModalOpen(false)}>
          <div className="modal-content" role="dialog" aria-modal="true" aria-label="Expanded Big Update report" onClick={e => e.stopPropagation()}>
            <button className="modal-close" type="button" aria-label="Close expanded report" onClick={() => setIsModalOpen(false)}>
              &#x2715;
            </button>
            <div className="markdown-body">
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>{content}</ReactMarkdown>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default BigUpdate;
