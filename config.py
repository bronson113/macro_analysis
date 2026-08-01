"""
Configuration for Macro Economic Analysis & Data Capture System
Based on Defiant Gatekeeper macro framework.
"""

from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
OUTPUT_DIR = BASE_DIR / "output"
CACHE_DIR = BASE_DIR / "cache"
YFINANCE_CACHE_DIR = CACHE_DIR / "yfinance"

for d in [DATA_DIR, LOG_DIR, OUTPUT_DIR, YFINANCE_CACHE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

DB_PATH_LEGACY = DATA_DIR / "macro_data.db"
INDICATORS_CSV = DATA_DIR / "indicators.csv"
OBSERVATIONS_CSV = DATA_DIR / "macro_observations.csv"
SNAPSHOTS_CSV = DATA_DIR / "daily_snapshots.csv"
NEWS_CSV = DATA_DIR / "macro_news.csv"
RUN_LOGS_CSV = DATA_DIR / "run_logs.csv"
SIGNALS_CSV = DATA_DIR / "signal_assessments.csv"
SOURCE_HEALTH_CSV = DATA_DIR / "source_health.csv"
OUTCOMES_JSON = OUTPUT_DIR / "outcome_evaluation.json"

DASHBOARD_HISTORY_DAYS = 365 * 10


def configure_yfinance_cache(yf_module) -> None:
    """Point yfinance at a writable project-local cache when the API is available."""
    cache_setter = getattr(yf_module, "set_tz_cache_location", None)
    if cache_setter is not None:
        cache_setter(str(YFINANCE_CACHE_DIR))

# FRED Series Mapping
# Maps human-readable key to FRED Series ID and description
FRED_SERIES = {
    # 1. Federal Reserve & Liquidity
    "fed_total_assets": {"id": "WALCL", "name": "Fed Total Assets (Millions of USD)", "frequency": "weekly", "unit_scale": "millions"},
    "reverse_repo": {"id": "RRPONTSYD", "name": "Overnight Reverse Repo (Billions of USD)", "frequency": "daily", "unit_scale": "billions"},
    "tga_balance": {"id": "WDTGAL", "name": "Treasury General Account (Millions of USD)", "frequency": "weekly", "unit_scale": "millions"},
    "effr": {"id": "FEDFUNDS", "name": "Effective Federal Funds Rate (%)", "frequency": "monthly"},
    "dff": {"id": "DFF", "name": "Daily Effective Federal Funds Rate (%)", "frequency": "daily"},
    "m2_money_supply": {"id": "M2SL", "name": "M2 Money Supply (Billions of USD)", "frequency": "monthly"},
    "bank_deposits": {"id": "DPSACBW027SBOG", "name": "Deposits, All Commercial Banks (Billions)", "frequency": "weekly"},

    # 2. Yield Curve & Interest Rates
    "treasury_10y": {"id": "DGS10", "name": "10-Year Treasury Constant Maturity Rate (%)", "frequency": "daily"},
    "treasury_2y": {"id": "DGS2", "name": "2-Year Treasury Constant Maturity Rate (%)", "frequency": "daily"},
    "treasury_3m": {"id": "DGS3MO", "name": "3-Month Treasury Constant Maturity Rate (%)", "frequency": "daily"},
    "treasury_30y": {"id": "DGS30", "name": "30-Year Treasury Constant Maturity Rate (%)", "frequency": "daily"},
    "spread_10y_2y": {"id": "T10Y2Y", "name": "10-Year minus 2-Year Treasury Spread (%)", "frequency": "daily"},
    "spread_10y_3m": {"id": "T10Y3M", "name": "10-Year minus 3-Month Treasury Spread (%)", "frequency": "daily"},

    # 3. Credit Spreads & Financial Conditions
    "high_yield_oas": {"id": "BAMLH0A0HYM2", "name": "ICE BofA US High Yield Option-Adjusted Spread (%)", "frequency": "daily"},
    "invest_grade_oas": {"id": "BAMLC0A1CAAA", "name": "ICE BofA AAA US Corporate Option-Adjusted Spread (%)", "frequency": "daily"},
    "ccc_below_oas": {"id": "BAMLH0A3HYC", "name": "ICE BofA CCC & Lower US High Yield OAS (%)", "frequency": "daily"},
    "chicago_fed_nfci": {"id": "ANFCI", "name": "Chicago Fed National Financial Conditions Index", "frequency": "weekly"},

    # 4. Labor Market
    "nonfarm_payrolls": {"id": "PAYEMS", "name": "Total Nonfarm Payroll Employment (Thousands)", "frequency": "monthly"},
    "unemployment_rate": {"id": "UNRATE", "name": "Unemployment Rate (%)", "frequency": "monthly"},
    "initial_claims": {"id": "ICSA", "name": "Initial Jobless Claims", "frequency": "weekly"},
    "continued_claims": {"id": "CCSA", "name": "Continued Jobless Claims", "frequency": "weekly"},
    "wage_growth": {"id": "CES0500000003", "name": "Average Hourly Earnings of All Employees ($/hr)", "frequency": "monthly"},
    "job_openings": {"id": "JTSJOL", "name": "JOLTS Total Job Openings (Thousands)", "frequency": "monthly"},

    # 5. Inflation & Purchasing Power
    "cpi": {"id": "CPIAUCSL", "name": "Consumer Price Index All Urban Consumers", "frequency": "monthly"},
    "core_cpi": {"id": "CPILFESL", "name": "Core CPI (Less Food and Energy)", "frequency": "monthly"},
    "pce": {"id": "PCEPI", "name": "Personal Consumption Expenditures Price Index", "frequency": "monthly"},
    "core_pce": {"id": "PCEPILFE", "name": "Core PCE Price Index", "frequency": "monthly"},
    "breakeven_5y": {"id": "T5YIE", "name": "5-Year Breakeven Inflation Rate (%)", "frequency": "daily"},
    "breakeven_10y": {"id": "T10YIE", "name": "10-Year Breakeven Inflation Rate (%)", "frequency": "daily"},

    # 6. Real Economic Activity & Growth
    "gdp": {"id": "GDPC1", "name": "Real Gross Domestic Product (Billions)", "frequency": "quarterly"},
    "retail_sales": {"id": "RSAFS", "name": "Advance Retail Sales (Millions)", "frequency": "monthly"},
    "industrial_production": {"id": "INDPRO", "name": "Industrial Production Index", "frequency": "monthly"},
    "housing_starts": {"id": "HOUST", "name": "Housing Starts: Total New Privately Owned", "frequency": "monthly"},
}

# Yahoo Finance Market Tickers (for daily high-frequency market prices)
YAHOO_TICKERS = {
    "sp500": "^GSPC",
    "nasdaq": "^IXIC",
    "vix": "^VIX",
    "dxy": "DX-Y.NYB",
    "crude_oil": "CL=F",
    "gold": "GC=F",
    "copper": "HG=F",
    "hyg_etf": "HYG",
    "lqd_etf": "LQD",
    "treasury_20y_etf": "TLT"
}

# Series that feed the current report, raw payload, validation, and web history.
# Set MACRO_FETCH_ALL_SERIES=1 to refresh every configured series instead.
ACTIVE_FRED_SERIES_KEYS = {
    "fed_total_assets",
    "reverse_repo",
    "tga_balance",
    "effr",
    "dff",
    "m2_money_supply",
    "treasury_10y",
    "treasury_2y",
    "treasury_3m",
    "spread_10y_2y",
    "spread_10y_3m",
    "high_yield_oas",
    "invest_grade_oas",
    "chicago_fed_nfci",
    "nonfarm_payrolls",
    "unemployment_rate",
    "initial_claims",
    "cpi",
    "breakeven_5y",
    "breakeven_10y",
    "housing_starts",
}

ACTIVE_YAHOO_TICKER_KEYS = {
    "sp500",
    "vix",
    "dxy",
    "crude_oil",
    "gold",
    "copper",
}

MARKET_SENTIMENT_INDICATORS = {
    "cnn_fear_greed_index": {
        "name": "CNN Fear & Greed Index",
        "source": "CNN",
        "category": "Market Sentiment",
        "frequency": "daily",
    },
    "shiller_pe": {
        "name": "Shiller PE Ratio",
        "source": "Multpl",
        "category": "Market Valuation",
        "frequency": "daily",
    }
}

# Thresholds & Regime Rules (Defiant Gatekeeper Logic)
REGIME_THRESHOLDS = {
    "yield_curve_inverted": 0.0,  # 10Y-2Y < 0 is inverted
    "high_yield_stress": 5.0,    # HY OAS > 5% indicates elevated credit stress
    "high_yield_panic": 8.0,     # HY OAS > 8% indicates market panic/crisis
    "vix_elevated": 20.0,
    "vix_panic": 30.0,
}
