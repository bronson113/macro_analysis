import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, Legend } from 'recharts';
import InfoPanel from './InfoPanel';
import { descriptions } from '../utils/descriptions';
import { createTrailingViewport, getVisibleViewport, getWheelAnchorRatio, updateViewportWithWheel } from '../utils/chartViewport';

const TIME_RANGES = [
  { label: '1M', days: 30 },
  { label: '3M', days: 90 },
  { label: '1Y', days: 365 },
  { label: '3Y', days: 365 * 3 },
  { label: '5Y', days: 365 * 5 },
  { label: '10Y', days: 365 * 10 },
];

const TrendGraphs = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('3M');
  const [viewport, setViewport] = useState({ start: 0, end: 0 });

  useEffect(() => {
    const fetchHistory = () => {
      fetch('/history.json?t=' + new Date().getTime())
        .then(res => res.json())
        .then(json => {
          setData(json);
          setLoading(false);
        })
        .catch(err => {
          console.error(err);
          setLoading(false);
        });
    };

    fetchHistory();
    const interval = setInterval(fetchHistory, 60000); // refresh every minute
    return () => clearInterval(interval);
  }, []);

  const handleTimeRangeChange = (nextTimeRange) => {
    if (nextTimeRange === timeRange) return;

    const selectedRange = TIME_RANGES.find(({ label }) => label === nextTimeRange);
    setTimeRange(nextTimeRange);
    if (selectedRange) {
      setViewport(createTrailingViewport(selectedRange.days, data.length));
    }
  };

  const indexedData = useMemo(
    () => data.map((point, index) => ({ ...point, __index: index })),
    [data]
  );
  const visibleViewport = useMemo(
    () => getVisibleViewport(viewport, data.length),
    [viewport, data.length]
  );
  const visibleData = useMemo(
    () => indexedData.slice(visibleViewport.start, visibleViewport.end),
    [indexedData, visibleViewport]
  );

  useEffect(() => {
    if (!data.length) return undefined;

    const selectedRange = TIME_RANGES.find(({ label }) => label === timeRange) ?? TIME_RANGES[1];
    setViewport((currentViewport) => {
      if (currentViewport.end > currentViewport.start) {
        return getVisibleViewport(currentViewport, data.length);
      }

      return createTrailingViewport(selectedRange.days, data.length);
    });
  }, [data.length, timeRange]);

  const handleTrendWheel = useCallback((event) => {
    if (!data.length) return;

    const chartSurface = event.target instanceof Element
      ? event.target.closest('.preset-zoom-chart')
      : null;
    if (!chartSurface) return;

    event.preventDefault();
    event.stopPropagation();
    const bounds = chartSurface.getBoundingClientRect();
    const anchorRatio = getWheelAnchorRatio({
      clientX: event.clientX,
      left: bounds.left,
      width: bounds.width,
    });

    setTimeRange('CUSTOM');
    setViewport((currentViewport) => updateViewportWithWheel({
      viewport: currentViewport,
      length: data.length,
      deltaX: event.deltaX,
      deltaY: event.deltaY,
      anchorRatio,
      panOnly: event.shiftKey,
    }));
  }, [data.length]);

  useEffect(() => {
    document.addEventListener('wheel', handleTrendWheel, { passive: false, capture: true });

    return () => {
      document.removeEventListener('wheel', handleTrendWheel, { capture: true });
    };
  }, [handleTrendWheel]);

  if (loading) return <div className="glass-panel text-muted">Loading Trend Data...</div>;
  if (!data.length) return null;

  return (
    <div className="section animate-fade-in stagger-3">
      <div className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>Historical Trends</h2>
        <div className="range-selector">
          {TIME_RANGES.map(({ label }) => (
            <button
              key={label}
              className={`range-btn ${timeRange === label ? 'active' : ''}`}
              onClick={() => handleTimeRangeChange(label)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      
      <div
        className="grid grid-cols-2 historical-chart-grid"
        style={{ gap: '2rem' }}
      >
        
        {/* Liquidity vs S&P 500 Chart */}
        <div className="glass-panel">
          <h3 style={{ fontSize: '1.1rem', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }} className="text-secondary">
            Net Liquidity vs S&P 500
            <InfoPanel title="Net Liquidity vs S&P 500" description={descriptions.net_liquidity} />
          </h3>
          <div style={{ width: '100%', height: 300 }}>
            <div
              className="preset-zoom-chart"
              title="Wheel to zoom. Shift-wheel or horizontal scroll to pan."
            >
              <ResponsiveContainer>
                <LineChart data={visibleData} margin={{ top: 5, right: 0, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                  <XAxis dataKey="date" stroke="var(--text-muted)" tick={{ fontSize: 12 }} minTickGap={30} />
                  <YAxis yAxisId="left" domain={['auto', 'auto']} stroke="var(--accent-primary)" tick={{ fontSize: 12 }} tickFormatter={(val) => `$${Math.round(val/1000)}k`} />
                  <YAxis yAxisId="right" orientation="right" domain={['auto', 'auto']} stroke="var(--status-positive)" tick={{ fontSize: 12 }} />
                  <Tooltip contentStyle={{ backgroundColor: 'var(--bg-surface-hover)', borderColor: 'rgba(255,255,255,0.1)', borderRadius: '8px' }} />
                  <Legend />
                  <Line isAnimationActive={false} yAxisId="left" type="monotone" dataKey="net_liquidity" name="Net Liquidity ($B)" stroke="var(--accent-primary)" strokeWidth={2} dot={false} />
                  <Line isAnimationActive={false} yAxisId="right" type="monotone" dataKey="sp500" name="S&P 500" stroke="var(--status-positive)" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Yield Curve Area Chart */}
        <div className="glass-panel">
          <h3 style={{ fontSize: '1.1rem', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }} className="text-secondary">
            Yield Curve Dynamics (10Y & 2Y)
            <InfoPanel title="Yield Curve Dynamics" description={descriptions.yield_curve} />
          </h3>
          <div style={{ width: '100%', height: 300 }}>
            <div
              className="preset-zoom-chart"
              title="Wheel to zoom. Shift-wheel or horizontal scroll to pan."
            >
              <ResponsiveContainer>
                <AreaChart data={visibleData} margin={{ top: 5, right: 0, left: 0, bottom: 5 }}>
                  <defs>
                    <linearGradient id="color10y" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--status-warning)" stopOpacity={0.8}/>
                      <stop offset="95%" stopColor="var(--status-warning)" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="color2y" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--accent-secondary)" stopOpacity={0.8}/>
                      <stop offset="95%" stopColor="var(--accent-secondary)" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                  <XAxis dataKey="date" stroke="var(--text-muted)" tick={{ fontSize: 12 }} minTickGap={30} />
                  <YAxis domain={['auto', 'auto']} stroke="var(--text-muted)" tick={{ fontSize: 12 }} tickFormatter={(val) => `${val}%`} />
                  <Tooltip contentStyle={{ backgroundColor: 'var(--bg-surface-hover)', borderColor: 'rgba(255,255,255,0.1)', borderRadius: '8px' }} />
                  <Legend />
                  <Area isAnimationActive={false} type="monotone" dataKey="treasury_10y" name="10Y Yield" stroke="var(--status-warning)" fillOpacity={1} fill="url(#color10y)" />
                  <Area isAnimationActive={false} type="monotone" dataKey="treasury_2y" name="2Y Yield" stroke="var(--accent-secondary)" fillOpacity={1} fill="url(#color2y)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
        
        {/* Volatility & Dollar Index Chart */}
        <div className="glass-panel">
          <h3 style={{ fontSize: '1.1rem', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }} className="text-secondary">
            Market Stress (VIX & DXY)
            <InfoPanel title="Market Stress" description={descriptions.market_stress} />
          </h3>
          <div style={{ width: '100%', height: 300 }}>
            <div
              className="preset-zoom-chart"
              title="Wheel to zoom. Shift-wheel or horizontal scroll to pan."
            >
              <ResponsiveContainer>
                <LineChart data={visibleData} margin={{ top: 5, right: 0, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                  <XAxis dataKey="date" stroke="var(--text-muted)" tick={{ fontSize: 12 }} minTickGap={30} />
                  <YAxis yAxisId="left" domain={['auto', 'auto']} stroke="var(--status-negative)" tick={{ fontSize: 12 }} />
                  <YAxis yAxisId="right" orientation="right" domain={['auto', 'auto']} stroke="var(--text-primary)" tick={{ fontSize: 12 }} />
                  <Tooltip contentStyle={{ backgroundColor: 'var(--bg-surface-hover)', borderColor: 'rgba(255,255,255,0.1)', borderRadius: '8px' }} />
                  <Legend />
                  <Line isAnimationActive={false} yAxisId="left" type="monotone" dataKey="vix" name="VIX" stroke="var(--status-negative)" strokeWidth={2} dot={false} />
                  <Line isAnimationActive={false} yAxisId="right" type="monotone" dataKey="dxy" name="DXY" stroke="var(--text-primary)" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Inflation vs Policy Rate Chart */}
        <div className="glass-panel">
          <h3 style={{ fontSize: '1.1rem', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }} className="text-secondary">
            Inflation (CPI) & Fed Funds Rate
            <InfoPanel title="Inflation vs Policy Rate" description={descriptions.inflation_policy} />
          </h3>
          <div style={{ width: '100%', height: 300 }}>
            <div
              className="preset-zoom-chart"
              title="Wheel to zoom. Shift-wheel or horizontal scroll to pan."
            >
              <ResponsiveContainer>
                <LineChart data={visibleData} margin={{ top: 5, right: 0, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                  <XAxis dataKey="date" stroke="var(--text-muted)" tick={{ fontSize: 12 }} minTickGap={30} />
                  <YAxis domain={['auto', 'auto']} stroke="var(--status-warning)" tick={{ fontSize: 12 }} tickFormatter={(val) => `${val}%`} />
                  <Tooltip contentStyle={{ backgroundColor: 'var(--bg-surface-hover)', borderColor: 'rgba(255,255,255,0.1)', borderRadius: '8px' }} />
                  <Legend />
                  <Line isAnimationActive={false} type="stepAfter" dataKey="policy_rate" name="Fed Funds Rate" stroke="var(--status-neutral)" strokeWidth={2} dot={false} />
                  <Line isAnimationActive={false} type="monotone" dataKey="cpi_yoy" name="CPI YoY" stroke="var(--status-warning)" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
        
      </div>
    </div>
  );
};

export default TrendGraphs;
