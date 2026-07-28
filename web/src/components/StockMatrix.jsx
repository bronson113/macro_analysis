import React from 'react';

const yahooFinanceUrl = (ticker) => `https://finance.yahoo.com/quote/${encodeURIComponent(ticker)}`;

const StockMatrix = ({ stocks = [] }) => {
  if (!stocks.length) return null;

  return (
    <div className="section animate-fade-in stagger-4">
      <div className="section-header">
        <h2>Stock Constituents Matrix</h2>
      </div>
      <div className="data-table-container">
        <table className="data-table" aria-label="Stock constituent research table">
          <thead>
            <tr>
              <th scope="col">Ticker</th>
              <th scope="col">Name</th>
              <th scope="col">Group</th>
              <th scope="col">Price</th>
              <th scope="col">Fwd P/E</th>
              <th scope="col">EV/EBITDA</th>
              <th scope="col">30D Return</th>
            </tr>
          </thead>
          <tbody>
            {stocks.map((s, i) => {
              const returnClass = s.return_30d_pct > 0 ? 'positive' : s.return_30d_pct < 0 ? 'negative' : 'neutral';
              
              return (
                <tr key={s.id || s.ticker || `${s.name || 'stock'}-${i}`}>
                  <th scope="row" className="ticker-cell">
                    <a
                      className="ticker-link"
                      href={yahooFinanceUrl(s.ticker)}
                      target="_blank"
                      rel="noreferrer"
                      title={`Open ${s.ticker} on Yahoo Finance`}
                    >
                      {s.ticker}
                    </a>
                  </th>
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
