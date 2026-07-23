import React, { useState, useEffect } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, Legend } from 'recharts';
import InfoPanel from './InfoPanel';
import { descriptions } from '../utils/descriptions';

const TrendGraphs = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('3M'); // '1M', '3M', '1Y'

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

  if (loading) return <div className="glass-panel text-muted">Loading Trend Data...</div>;
  if (!data.length) return null;

  // Filter data based on selected time range
  let filteredData = data;
  if (timeRange === '1M') {
    filteredData = data.slice(Math.max(data.length - 30, 0));
  } else if (timeRange === '3M') {
    filteredData = data.slice(Math.max(data.length - 90, 0));
  } else if (timeRange === '1Y') {
    filteredData = data.slice(Math.max(data.length - 365, 0));
  }

  return (
    <div className="section animate-fade-in stagger-3">
      <div className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>Historical Trends</h2>
        <div className="range-selector">
          <button className={`range-btn ${timeRange === '1M' ? 'active' : ''}`} onClick={() => setTimeRange('1M')}>1M</button>
          <button className={`range-btn ${timeRange === '3M' ? 'active' : ''}`} onClick={() => setTimeRange('3M')}>3M</button>
          <button className={`range-btn ${timeRange === '1Y' ? 'active' : ''}`} onClick={() => setTimeRange('1Y')}>1Y</button>
        </div>
      </div>
      
      <div className="grid grid-cols-2" style={{ gap: '2rem' }}>
        
        {/* Liquidity vs S&P 500 Chart */}
        <div className="glass-panel">
          <h3 style={{ fontSize: '1.1rem', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }} className="text-secondary">
            Net Liquidity vs S&P 500
            <InfoPanel title="Net Liquidity vs S&P 500" description={descriptions.net_liquidity} />
          </h3>
          <div style={{ width: '100%', height: 300 }}>
            <ResponsiveContainer>
              <LineChart data={filteredData} margin={{ top: 5, right: 0, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                <XAxis dataKey="date" stroke="var(--text-muted)" tick={{ fontSize: 12 }} minTickGap={30} />
                <YAxis yAxisId="left" domain={['auto', 'auto']} stroke="var(--accent-primary)" tick={{ fontSize: 12 }} tickFormatter={(val) => `$${Math.round(val/1000)}k`} />
                <YAxis yAxisId="right" orientation="right" domain={['auto', 'auto']} stroke="var(--status-positive)" tick={{ fontSize: 12 }} />
                <Tooltip contentStyle={{ backgroundColor: 'var(--bg-surface-hover)', borderColor: 'rgba(255,255,255,0.1)', borderRadius: '8px' }} />
                <Legend />
                <Line yAxisId="left" type="monotone" dataKey="net_liquidity" name="Net Liquidity ($B)" stroke="var(--accent-primary)" strokeWidth={2} dot={false} />
                <Line yAxisId="right" type="monotone" dataKey="sp500" name="S&P 500" stroke="var(--status-positive)" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Yield Curve Area Chart */}
        <div className="glass-panel">
          <h3 style={{ fontSize: '1.1rem', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }} className="text-secondary">
            Yield Curve Dynamics (10Y & 2Y)
            <InfoPanel title="Yield Curve Dynamics" description={descriptions.yield_curve} />
          </h3>
          <div style={{ width: '100%', height: 300 }}>
            <ResponsiveContainer>
              <AreaChart data={filteredData} margin={{ top: 5, right: 0, left: 0, bottom: 5 }}>
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
                <Area type="monotone" dataKey="treasury_10y" name="10Y Yield" stroke="var(--status-warning)" fillOpacity={1} fill="url(#color10y)" />
                <Area type="monotone" dataKey="treasury_2y" name="2Y Yield" stroke="var(--accent-secondary)" fillOpacity={1} fill="url(#color2y)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
        
        {/* Volatility & Dollar Index Chart */}
        <div className="glass-panel">
          <h3 style={{ fontSize: '1.1rem', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }} className="text-secondary">
            Market Stress (VIX & DXY)
            <InfoPanel title="Market Stress" description={descriptions.market_stress} />
          </h3>
          <div style={{ width: '100%', height: 300 }}>
            <ResponsiveContainer>
              <LineChart data={filteredData} margin={{ top: 5, right: 0, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                <XAxis dataKey="date" stroke="var(--text-muted)" tick={{ fontSize: 12 }} minTickGap={30} />
                <YAxis yAxisId="left" domain={['auto', 'auto']} stroke="var(--status-negative)" tick={{ fontSize: 12 }} />
                <YAxis yAxisId="right" orientation="right" domain={['auto', 'auto']} stroke="var(--text-primary)" tick={{ fontSize: 12 }} />
                <Tooltip contentStyle={{ backgroundColor: 'var(--bg-surface-hover)', borderColor: 'rgba(255,255,255,0.1)', borderRadius: '8px' }} />
                <Legend />
                <Line yAxisId="left" type="monotone" dataKey="vix" name="VIX" stroke="var(--status-negative)" strokeWidth={2} dot={false} />
                <Line yAxisId="right" type="monotone" dataKey="dxy" name="DXY" stroke="var(--text-primary)" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Inflation vs Policy Rate Chart */}
        <div className="glass-panel">
          <h3 style={{ fontSize: '1.1rem', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }} className="text-secondary">
            Inflation (CPI) & Fed Funds Rate
            <InfoPanel title="Inflation vs Policy Rate" description={descriptions.inflation_policy} />
          </h3>
          <div style={{ width: '100%', height: 300 }}>
            <ResponsiveContainer>
              <LineChart data={filteredData} margin={{ top: 5, right: 0, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                <XAxis dataKey="date" stroke="var(--text-muted)" tick={{ fontSize: 12 }} minTickGap={30} />
                <YAxis domain={['auto', 'auto']} stroke="var(--status-warning)" tick={{ fontSize: 12 }} tickFormatter={(val) => `${val}%`} />
                <Tooltip contentStyle={{ backgroundColor: 'var(--bg-surface-hover)', borderColor: 'rgba(255,255,255,0.1)', borderRadius: '8px' }} />
                <Legend />
                <Line type="stepAfter" dataKey="policy_rate" name="Fed Funds Rate" stroke="var(--status-neutral)" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="cpi_yoy" name="CPI YoY" stroke="var(--status-warning)" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
        
      </div>
    </div>
  );
};

export default TrendGraphs;
