import React from 'react';

const StockMatrix = ({ stocks = [] }) => {
  if (!stocks.length) return null;

  return (
    <div className="section animate-fade-in stagger-4">
      <div className="section-header">
        <h2>Stock Constituents Matrix</h2>
      </div>
      <div className="data-table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th>Ticker</th>
              <th>Name</th>
              <th>Group</th>
              <th>Price</th>
              <th>Fwd P/E</th>
              <th>EV/EBITDA</th>
              <th>30D Return</th>
            </tr>
          </thead>
          <tbody>
            {stocks.map((s, i) => {
              const returnClass = s.return_30d_pct > 0 ? 'positive' : s.return_30d_pct < 0 ? 'negative' : 'neutral';
              
              return (
                <tr key={i}>
                  <td style={{ fontWeight: 600 }}>{s.ticker}</td>
                  <td>{s.name}</td>
                  <td><span className="text-muted">{s.group}</span></td>
                  <td>${Number(s.price).toFixed(2)}</td>
                  <td>{s.forward_pe ? Number(s.forward_pe).toFixed(1) : '-'}</td>
                  <td>{s.ev_ebitda ? Number(s.ev_ebitda).toFixed(1) : '-'}</td>
                  <td className={returnClass}>
                    {s.return_30d_pct ? Number(s.return_30d_pct).toFixed(2) + '%' : '-'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default StockMatrix;
