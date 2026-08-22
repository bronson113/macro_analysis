import pandas as pd
import os
from datetime import datetime, timedelta
from config import DASHBOARD_HISTORY_DAYS, OBSERVATIONS_CSV
from storage import MacroStorage

def backfill():
    if not os.path.exists(OBSERVATIONS_CSV):
        print("No observations CSV found. Cannot backfill.")
        return

    print("Loading observations...")
    df = pd.read_csv(OBSERVATIONS_CSV)
    df['date'] = pd.to_datetime(df['date'])
    
    cutoff = datetime.now() - timedelta(days=DASHBOARD_HISTORY_DAYS)
    
    dates = df[df['date'] >= cutoff]['date'].dt.strftime("%Y-%m-%d").unique()
    dates = sorted(dates)
    
    print(f"Found {len(dates)} dates to backfill.")
    
    from config import SNAPSHOTS_CSV
    storage = MacroStorage(snapshots_csv=SNAPSHOTS_CSV)
    inserted = 0
    
    for d_str in dates:
        d = pd.to_datetime(d_str)
        
        def get_val(key, date_target=d):
            sub = df[(df['indicator_key'] == key) & (df['date'] <= date_target)]
            if not sub.empty:
                return float(sub.sort_values('date').iloc[-1]['value'])
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

        snapshot_data = {
            'date': d_str,
            'net_liquidity': net_liq,
            'fed_assets': fed_assets,
            'tga': tga,
            'rrp': rrp,
            'treasury_10y': t10y,
            'treasury_2y': t2y,
            'spread_10y_2y': spread,
            'high_yield_oas': hy_oas,
            'vix': vix,
            'dxy': dxy,
            'sp500': sp500,
            'unemployment_rate': unemp,
            'cpi_yoy': cpi_yoy,
            'breakeven_10y': be10y,
            'm2_yoy': m2_yoy,
            'policy_rate': policy,
            'policy_rate_change_30d': policy_change,
            'real_yield_10y': real_yield
        }
        
        storage.save_daily_snapshot(snapshot_data)
        inserted += 1
        
    print(f"Backfilled {inserted} daily snapshots.")

def backfill_valuations():
    """Backfill 1-year historical peer-cohort relative multiples and sector valuations."""
    print("Backfilling historical valuations (cohort-relative multiples and sector aggregates)...")
    from raw_data_engine import RawDataEngine
    from valuation import SectorValuationEngine
    from storage import MacroStorage

    storage = MacroStorage()
    raw_engine = RawDataEngine(storage, verbose=False)
    metrics = raw_engine.fetch_individual_stock_metrics()
    today_str = datetime.now().strftime("%Y-%m-%d")
    price_histories = getattr(raw_engine, "_last_price_histories", None)
    rel_count = raw_engine.save_relative_multiple_observations(
        metrics, today_str, price_histories=price_histories
    )
    print(f"Saved {rel_count} cohort-relative valuation records.")

    val_engine = SectorValuationEngine(storage)
    sec_count = val_engine.save_historical_sector_valuations(price_histories=price_histories)
    print(f"Saved {sec_count} historical sector valuation records.")


if __name__ == '__main__':
    backfill_valuations()
    backfill()
