"""
News Analyzer module for Macro Economic Analysis System.
Fetches, categorizes, and evaluates sentiment/impact for major macroeconomic news,
and performs Sector Bellwether Contagion Analysis (e.g., Micron, Nvidia, JPMorgan news impacting entire sectors).
"""

import re
import logging
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Any, Optional
import yfinance as yf
from storage import MacroStorage
from config import configure_yfinance_cache

configure_yfinance_cache(yf)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# RSS Feed Queries for Macro Topics
NEWS_RSS_QUERIES = [
    ("Federal Reserve & Liquidity", "https://news.google.com/rss/search?q=Federal+Reserve+OR+FOMC+OR+liquidity+OR+Powell&hl=en-US&gl=US&ceid=US:en"),
    ("Inflation & Prices", "https://news.google.com/rss/search?q=CPI+inflation+OR+PCE+OR+Consumer+Prices&hl=en-US&gl=US&ceid=US:en"),
    ("Labor & Employment", "https://news.google.com/rss/search?q=unemployment+OR+payrolls+OR+jobless+claims&hl=en-US&gl=US&ceid=US:en"),
    ("Credit & Rates", "https://news.google.com/rss/search?q=Treasury+yields+OR+credit+spreads+OR+bond+market&hl=en-US&gl=US&ceid=US:en"),
    ("Geopolitics & Oil", "https://news.google.com/rss/search?q=crude+oil+OR+OPEC+OR+tariffs+OR+geopolitical+risk&hl=en-US&gl=US&ceid=US:en")
]

# Sector Bellwethers Mapping
SECTOR_BELLWETHERS = {
    "MU": {"name": "Micron Technology", "sector": "Technology / Semiconductors", "etf": "XLK / SOXX"},
    "NVDA": {"name": "NVIDIA", "sector": "Technology / AI Hardware", "etf": "XLK / SOXX"},
    "AAPL": {"name": "Apple", "sector": "Technology / Consumer Hardware", "etf": "XLK"},
    "JPM": {"name": "JPMorgan Chase", "sector": "Financials / Banking System", "etf": "XLF"},
    "XOM": {"name": "ExxonMobil", "sector": "Energy / Oil & Gas", "etf": "XLE"},
    "TSLA": {"name": "Tesla", "sector": "Consumer Discretionary / EV", "etf": "XLY"},
    "CAT": {"name": "Caterpillar", "sector": "Industrials / Global Equipment", "etf": "XLI"},
    "UNH": {"name": "UnitedHealth Group", "sector": "Healthcare / Managed Care", "etf": "XLV"}
}

# Keyword rules for impact scoring & sentiment classification
HAWKISH_KEYWORDS = ["rate hike", "hikes", "tightening", "hotter", "higher inflation", "hawkish", "sticky inflation", "surge"]
DOVISH_KEYWORDS = ["rate cut", "cuts", "easing", "cooling", "lower inflation", "dovish", "slowdown", "softening"]
STRESS_KEYWORDS = ["default", "crisis", "panic", "stress", "turmoil", "sell-off", "collapse", "downgrade", "liquidity squeeze"]
CONTAGION_KEYWORDS = ["capex cut", "guidance cut", "demand slump", "warning", "inventory glut", "margin squeeze", "revenue miss", "layoffs"]


class MacroNewsAnalyzer:
    def __init__(self, storage: Optional[MacroStorage] = None):
        self.storage = storage or MacroStorage()
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) MacroNewsFetcher/1.0"

    def _classify_sentiment_and_impact(self, title: str, summary: str) -> Dict[str, Any]:
        text = (title + " " + summary).lower()

        score = 0.0
        sentiment = "Neutral / Mixed"

        hawkish_matches = sum(1 for k in HAWKISH_KEYWORDS if k in text)
        dovish_matches = sum(1 for k in DOVISH_KEYWORDS if k in text)
        stress_matches = sum(1 for k in STRESS_KEYWORDS if k in text)
        contagion_matches = sum(1 for k in CONTAGION_KEYWORDS if k in text)

        if contagion_matches > 0 or stress_matches > 0:
            sentiment = "Sector Contagion / Stress Warning"
            score = -0.8
        elif hawkish_matches > dovish_matches:
            sentiment = "Hawkish / Tightening Bias"
            score = -0.4
        elif dovish_matches > hawkish_matches:
            sentiment = "Dovish / Easing Bias"
            score = 0.5

        return {"impact_score": score, "sentiment": sentiment}

    def fetch_google_news(self) -> List[Dict[str, Any]]:
        all_news = []
        today_str = datetime.now().strftime("%Y-%m-%d")

        for category, url in NEWS_RSS_QUERIES:
            req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    xml_data = resp.read()
                    root = ET.fromstring(xml_data)

                    for item in root.findall("channel/item")[:4]:
                        title = item.find("title").text if item.find("title") is not None else ""
                        link = item.find("link").text if item.find("link") is not None else ""
                        source = item.find("source").text if item.find("source") is not None else "Google News"
                        description = item.find("description").text if item.find("description") is not None else ""

                        clean_summary = re.sub(r"<[^>]+>", "", description) if description else ""
                        analysis = self._classify_sentiment_and_impact(title, clean_summary)

                        all_news.append({
                            "date": today_str,
                            "title": title,
                            "summary": clean_summary[:200] if clean_summary else title,
                            "source": source,
                            "link": link,
                            "category": category,
                            "impact_score": analysis["impact_score"],
                            "sentiment": analysis["sentiment"]
                        })
            except Exception as e:
                logging.error(f"Error fetching news for category {category}: {e}")

        return all_news

    def fetch_bellwether_sector_news(self) -> List[Dict[str, Any]]:
        """
        Fetch news for sector bellwether companies (Micron, Nvidia, JPMorgan, Tesla, Exxon)
        and assess potential sector-wide contagion risk.
        """
        today_str = datetime.now().strftime("%Y-%m-%d")
        bellwether_news = []

        for ticker, meta in SECTOR_BELLWETHERS.items():
            try:
                t = yf.Ticker(ticker)
                raw_news = t.news
                for item in raw_news[:3]:
                    content = item.get("content", {})
                    title = content.get("title") or item.get("title") or ""
                    summary = content.get("summary") or item.get("summary") or ""
                    link = content.get("canonicalUrl", {}).get("url") or item.get("link") or ""

                    if title:
                        analysis = self._classify_sentiment_and_impact(title, summary)
                        category_str = f"Sector Bellwether: {ticker} ({meta['sector']})"

                        # Elevate contagion classification if bellwether shows stress
                        contagion_flag = "Low Risk"
                        if "Contagion" in analysis["sentiment"] or analysis["impact_score"] < -0.5:
                            contagion_flag = f"HIGH SECTOR RISK ({meta['etf']})"

                        bellwether_news.append({
                            "date": today_str,
                            "title": f"[{ticker} - {meta['name']}] {title}",
                            "summary": summary[:200] if summary else title,
                            "source": f"Yahoo Finance ({ticker})",
                            "link": link,
                            "category": category_str,
                            "impact_score": analysis["impact_score"],
                            "sentiment": f"{analysis['sentiment']} | {contagion_flag}"
                        })
            except Exception as e:
                logging.error(f"Error fetching bellwether news for {ticker}: {e}")

        return bellwether_news

    def fetch_and_store_news(self) -> int:
        google_news = self.fetch_google_news()
        bellwether_news = self.fetch_bellwether_sector_news()

        combined = google_news + bellwether_news
        count = self.storage.save_news_events(combined)
        logging.info(f"Fetched {len(combined)} news events (macro + sector bellwethers). Saved {count} new entries.")
        return count

    def get_major_event_summary(self, limit: int = 12) -> List[Dict[str, Any]]:
        return self.storage.get_recent_news(limit=limit)
