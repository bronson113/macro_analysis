import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from config import DB_PATH
from analyzer import MacroAnalyzer

def backfill():
    print("Connecting to DB...")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get distinct dates from macro_observations for the last 365 days
    cutoff = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    cursor.execute("""
        SELECT DISTINCT date 
        FROM macro_observations 
        WHERE date >= ? 
        ORDER BY date ASC
    """, (cutoff,))
    
    dates = [row['date'] for row in cursor.fetchall()]
    print(f"Found {len(dates)} dates to backfill.")
    
    # We will simulate analyzer for each date by querying the DB
    # Actually, the easiest way is to use SQL to find the latest value ON OR BEFORE each date.
    
    keys = [
        "fed_total_assets", "tga_balance", "reverse_repo", 
        "treasury_10y", "treasury_2y", "spread_10y_2y", 
        "high_yield_oas", "vix", "dxy", "sp500",
        "unemployment_rate", "cpi", "breakeven_10y", "m2_money_supply",
        "dff"
    ]
    
    # Pre-load all data into pandas to make it blazing fast
    cursor.execute("SELECT indicator_key, date, value FROM macro_observations WHERE indicator_key IN ({})".format(','.join(['?']*len(keys))), keys)
    df = pd.DataFrame(cursor.fetchall(), columns=['indicator_key', 'date', 'value'])
    df['date'] = pd.to_datetime(df['date'])
    
    # For YoY calculations, we also need data from a year ago
    
    inserted = 0
    for d_str in dates:
        d = pd.to_datetime(d_str)
        
        # Helper to get latest value on or before 'd'
        def get_val(key, date_target=d):
            sub = df[(df['indicator_key'] == key) & (df['date'] <= date_target)]
            if not sub.empty:
                return sub.sort_values('date').iloc[-1]['value']
            return None
            
        fed_assets = get_val("fed_total_assets")
        tga = get_val("tga_balance")
        rrp = get_val("reverse_repo")
        
        net_liq = None
        if fed_assets and tga and rrp:
            net_liq = (fed_assets / 1000.0) - (tga / 1000.0) - rrp
            
        t10y = get_val("treasury_10y")
        t2y = get_val("treasury_2y")
        spread = get_val("spread_10y_2y")
        hy_oas = get_val("high_yield_oas")
        vix = get_val("vix")
        dxy = get_val("dxy")
        sp500 = get_val("sp500")
        unemp = get_val("unemployment_rate")
        
        cpi = get_val("cpi")
        cpi_1y = get_val("cpi", d - pd.Timedelta(days=365))
        cpi_yoy = ((cpi / cpi_1y) - 1.0) * 100.0 if cpi and cpi_1y else None
        
        be10y = get_val("breakeven_10y")
        
        m2 = get_val("m2_money_supply")
        m2_1y = get_val("m2_money_supply", d - pd.Timedelta(days=365))
        m2_yoy = ((m2 / m2_1y) - 1.0) * 100.0 if m2 and m2_1y else None
        
        policy = get_val("dff")
        policy_30d = get_val("dff", d - pd.Timedelta(days=30))
        policy_change = policy - policy_30d if policy and policy_30d else None
        
        real_yield = t10y - cpi_yoy if t10y and cpi_yoy else None

        # Insert or replace
        cursor.execute("""
            INSERT OR REPLACE INTO daily_snapshots (
                date, net_liquidity, fed_assets, tga, rrp,
                treasury_10y, treasury_2y, spread_10y_2y, high_yield_oas,
                vix, dxy, sp500, unemployment_rate, cpi_yoy,
                breakeven_10y, m2_yoy, policy_rate, policy_rate_change_30d,
                real_yield_10y
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            d_str, net_liq, fed_assets, tga, rrp,
            t10y, t2y, spread, hy_oas, vix, dxy, sp500,
            unemp, cpi_yoy, be10y, m2_yoy, policy, policy_change, real_yield
        ))
        inserted += 1
        
    conn.commit()
    conn.close()
    print(f"Backfilled {inserted} daily snapshots.")

if __name__ == '__main__':
    backfill()
