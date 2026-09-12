import React, { useCallback, useState, useEffect, useId, useRef } from 'react';
import { splitReportSections, splitWeeklyDigestSections } from '../utils/dashboardPresentation';
import { useDialogFocus } from '../hooks/useDialogFocus';
import { getNextTabIndex } from '../utils/keyboardNavigation';
import { buildMarkdownUrl } from '../utils/markdownSource';
import MarkdownContent from './MarkdownComponents';
import RegimeOverview from './RegimeOverview';

const latestReport = { date: '', path: '/latest_report.md' };
const latestWeeklyDigest = { date: '', path: '/latest_weekly_digest.md' };

const BigUpdate = ({
  reports = [],
  weeklyDigests = [],
  macroRegime,
  macroSituation,
  macroRegimeSections,
}) => {
  const [reportMode, setReportMode] = useState('daily');
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedDate, setSelectedDate] = useState('');
  const [selectedWeekDate, setSelectedWeekDate] = useState('');
  const [reportError, setReportError] = useState('');
  const [activeTab, setActiveTab] = useState('summary');
  const dateInputRef = useRef(null);
  const dialogRef = useRef(null);
  const closeButtonRef = useRef(null);
  const tabRefs = useRef([]);
  const reportId = useId();
  const closeModal = useCallback(() => setIsModalOpen(false), []);

  useDialogFocus({
    isOpen: isModalOpen && !reportError,
    onClose: closeModal,
    dialogRef,
    initialFocusRef: closeButtonRef,
  });

  useEffect(() => {
    let reportPath = '';
    let isLatest = true;

    if (reportMode === 'daily') {
      const selectedReport = reports.find(report => report.date === selectedDate) || latestReport;
      reportPath = selectedReport.path;
      isLatest = !selectedDate;
    } else {
      const activeWeek = weeklyDigests.find(w => w.date === selectedWeekDate) || weeklyDigests[0] || latestWeeklyDigest;
      reportPath = activeWeek.path;
      isLatest = !selectedWeekDate || (weeklyDigests[0] && selectedWeekDate === weeklyDigests[0].date);
    }

    const fetchReport = () => {
      setReportError('');
      fetch(buildMarkdownUrl(import.meta.env.BASE_URL, reportPath, Date.now()))
        .then(res => {
          if (!res.ok) throw new Error(`Failed to load the selected ${reportMode === 'weekly' ? 'weekly digest' : 'daily report'}.`);
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

    const interval = setInterval(fetchReport, 60000);
    return () => clearInterval(interval);
  }, [reports, weeklyDigests, selectedDate, selectedWeekDate, reportMode]);

  if (loading && !content) return <div className="glass-panel text-muted">Loading Big Update...</div>;

  const newestDate = reports[0]?.date || '';
  const oldestDate = reports[reports.length - 1]?.date || '';
  const displayedDate = selectedDate || newestDate;

  const newestWeekDate = weeklyDigests[0]?.date || '';
  const displayedWeekDate = selectedWeekDate || newestWeekDate;
  const currentWeeklyDigest = weeklyDigests.find(w => w.date === displayedWeekDate) || weeklyDigests[0];

  let reportTabs = [];
  if (reportMode === 'daily') {
    const reportSections = splitReportSections(content);
    reportTabs = [
      { id: 'summary', label: 'Summary', content: reportSections.summary },
      { id: 'active', label: 'Active Situation', content: reportSections.active },
      { id: 'risks', label: 'Risks', content: reportSections.risks },
      { id: 'full', label: 'Full Report', content: reportSections.full },
    ].filter(tab => tab.content);
  } else {
    const weeklySections = splitWeeklyDigestSections(content);
    reportTabs = [
      { id: 'summary', label: 'Summary', content: weeklySections.summary },
      { id: 'active', label: 'Active Situation', content: weeklySections.active },
      { id: 'deltas', label: 'Weekly Deltas', content: weeklySections.deltas },
      { id: 'catalysts', label: 'Catalysts & Outlook', content: weeklySections.catalysts },
      { id: 'full', label: 'Full Digest', content: weeklySections.full },
    ].filter(tab => tab.content);
  }

  const visibleTab = reportTabs.some(tab => tab.id === activeTab) ? activeTab : reportTabs[0]?.id;

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

  const handleWeekChange = event => {
    setSelectedWeekDate(event.target.value);
  };

  const handleTabKeyDown = (event, currentIndex) => {
    const nextIndex = getNextTabIndex({
      key: event.key,
      currentIndex,
      tabCount: reportTabs.length,
    });
    if (nextIndex === null) return;

    event.preventDefault();
    setActiveTab(reportTabs[nextIndex].id);
    tabRefs.current[nextIndex]?.focus();
  };

  return (
    <>
      <section className="section animate-fade-in stagger-2" aria-labelledby="big-update-heading">
        <div className="section-header big-update-header">
          <div>
            <p className="section-kicker">
              {reportMode === 'weekly' ? 'Weekly Digest' : 'Daily Brief'}
            </p>
            <h2 id="big-update-heading">
              {reportMode === 'weekly' ? 'The Weekly Digest' : 'The Big Update'}
            </h2>
          </div>

          <div className="report-controls-bar">
            <div className="report-mode-toggle" role="group" aria-label="Report view mode">
              <button
                type="button"
                className={`mode-btn ${reportMode === 'daily' ? 'active' : ''}`}
                onClick={() => { setReportMode('daily'); setActiveTab('summary'); }}
              >
                Daily Brief
              </button>
              <button
                type="button"
                className={`mode-btn ${reportMode === 'weekly' ? 'active' : ''}`}
                onClick={() => { setReportMode('weekly'); setActiveTab('summary'); }}
              >
                Weekly Digest
              </button>
            </div>

            {reportMode === 'daily' ? (
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
            ) : (
              <div className="report-date-picker week-picker">
                <label htmlFor="week-select">Week</label>
                <select
                  id="week-select"
                  value={displayedWeekDate}
                  onChange={handleWeekChange}
                  disabled={!weeklyDigests.length}
                >
                  {weeklyDigests.map((w, idx) => (
                    <option key={w.date} value={w.date}>
                      {w.label} {idx === 0 ? '(Latest)' : ''}
                    </option>
                  ))}
                </select>
                {selectedWeekDate && weeklyDigests[0] && selectedWeekDate !== weeklyDigests[0].date && (
                  <button className="range-btn" type="button" onClick={() => setSelectedWeekDate(weeklyDigests[0].date)}>
                    Latest
                  </button>
                )}
              </div>
            )}
          </div>
        </div>

        {reportMode === 'weekly' && currentWeeklyDigest && (
          <div className="weekly-summary-chips animate-fade-in" aria-label="Weekly summary indicators">
            <span className="metadata-chip">
              <span>Reserve Liquidity</span>
              <strong>{currentWeeklyDigest.net_liquidity_change || 'N/A'}</strong>
            </span>
            <span className="metadata-chip">
              <span>10Y Treasury</span>
              <strong>{currentWeeklyDigest.treasury_10y_change || 'N/A'}</strong>
            </span>
            <span className="metadata-chip">
              <span>S&P 500</span>
              <strong>{currentWeeklyDigest.sp500_change || 'N/A'}</strong>
            </span>
            <span className="metadata-chip">
              <span>High Yield OAS</span>
              <strong>{currentWeeklyDigest.hy_oas_change || 'N/A'}</strong>
            </span>
          </div>
        )}

        <RegimeOverview
          regime={macroRegime}
          situation={macroSituation}
          sections={macroRegimeSections}
        />

        <div className="glass-panel">
          {reportError ? (
            <p className="text-secondary">{reportError}</p>
          ) : (
            <>
              <div className="report-tabs" role="tablist" aria-label={`${reportMode === 'weekly' ? 'Weekly Digest' : 'Big Update'} report sections`} aria-orientation="horizontal">
                {reportTabs.map((tab, index) => (
                  <button
                    key={tab.id}
                    ref={element => { tabRefs.current[index] = element; }}
                    className={`report-tab ${visibleTab === tab.id ? 'active' : ''}`}
                    type="button"
                    role="tab"
                    id={`${reportId}-${tab.id}-tab`}
                    aria-selected={visibleTab === tab.id}
                    aria-controls={`${reportId}-${tab.id}-panel`}
                    tabIndex={visibleTab === tab.id ? 0 : -1}
                    onClick={() => setActiveTab(tab.id)}
                    onKeyDown={event => handleTabKeyDown(event, index)}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
              {reportTabs.map(tab => (
                <div
                  key={tab.id}
                  className={`markdown-body report-tab-body ${tab.id === 'full' ? 'full-report' : ''}`}
                  id={`${reportId}-${tab.id}-panel`}
                  role="tabpanel"
                  aria-labelledby={`${reportId}-${tab.id}-tab`}
                  hidden={visibleTab !== tab.id}
                >
                  <MarkdownContent content={tab.content} />
                </div>
              ))}
              <button className="link-button" type="button" onClick={() => setIsModalOpen(true)}>
                Open Expanded {reportMode === 'weekly' ? 'Digest' : 'Report'} &rarr;
              </button>
            </>
          )}
        </div>
      </section>

      {isModalOpen && !reportError && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal-content" ref={dialogRef} tabIndex="-1" role="dialog" aria-modal="true" aria-labelledby={`${reportId}-expanded-title`} onClick={e => e.stopPropagation()}>
            <button className="modal-close" ref={closeButtonRef} type="button" aria-label={`Close expanded ${reportMode === 'weekly' ? 'digest' : 'report'}`} onClick={closeModal}>
              &#x2715;
            </button>
            <h2 id={`${reportId}-expanded-title`} className="sr-only">Expanded {reportMode === 'weekly' ? 'Weekly Digest' : 'Big Update report'}</h2>
            <div className="markdown-body">
              <MarkdownContent content={content} />
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default BigUpdate;

