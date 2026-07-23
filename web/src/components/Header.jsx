import React from 'react';

const Header = ({ metadata }) => {
  return (
    <header className="dashboard-header animate-fade-in stagger-1">
      <div>
        <h1 className="gradient-text">Macro Analysis Dashboard</h1>
        <p className="text-secondary">AI-driven financial insights & quantitative macro data.</p>
      </div>
    </header>
  );
};

export default Header;
