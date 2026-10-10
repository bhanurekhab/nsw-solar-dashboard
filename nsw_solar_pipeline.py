"""
NSW Solar & Battery Installations - Data Pipeline
==================================================
Cleans rooftop solar and battery installation data
published by the Clean Energy Regulator (CER).

Source: https://cer.gov.au/document_page/sres-postcode-data-installations-2011-to-present-and-totals

Usage: python nsw_solar_pipeline.py

Input:  data/solar_raw.csv
        data/battery_raw.csv

Output: output/nsw_solar_monthly.csv
        output/nsw_solar_yearly_summary.csv
        output/nsw_battery_monthly.csv
        output/nsw_battery_yearly_summary.csv
        output/nsw_top_postcodes.csv
        output/issues_log.txt
"""

import pandas as pd
import os
import sys

DATA_DIR = "data"
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

issues = []

def log_issue(msg):
    issues.append(msg)
    print(f"  [ISSUE] {msg}")


def process_file(filepath, label):
    print(f"\n{'='*60}")
    print(f"Processing: {label}")
    print(f"{'='*60}")
    
    if not os.path.exists(filepath):
        print(f"  ERROR: {filepath} not found.")
        print(f"  Download from CER website and save to data/ folder.")
        return None, None
    
    df = pd.read_csv(filepath)
    print(f"  Rows loaded: {len(df)}")
    
    pc_col = [c for c in df.columns if 'postcode' in c.lower()][0]
    df[pc_col] = df[pc_col].astype(str).str.strip().str.zfill(4)
    
    short = df[df[pc_col].str.len() < 4]
    if len(short) > 0:
        log_issue(f"{label}: Fixed {len(short)} postcodes shorter than 4 digits")
    
    df['postcode_num'] = pd.to_numeric(df[pc_col], errors='coerce')
    df_nsw = df[(df['postcode_num'] >= 2000) & (df['postcode_num'] <= 2999)].copy()
    log_issue(f"{label}: Filtered to NSW (2000-2999): {len(df_nsw)} of {len(df)} rows")
    
    month_cols = [c for c in df_nsw.columns if '- Installation Quantity' in c]
    print(f"  Monthly columns: {len(month_cols)}")
    
    if not month_cols:
        log_issue(f"{label}: No monthly columns found")
        return None, None
    
    df_long = df_nsw.melt(
        id_vars=[pc_col],
        value_vars=month_cols,
        var_name='period',
        value_name='installations'
    )
    
    df_long['period'] = df_long['period'].str.replace(' - Installation Quantity', '')
    df_long['year'] = df_long['period'].str.extract(r'(\d{4})').astype(int)
    df_long['month'] = df_long['period'].str.extract(r'([A-Za-z]+)')
    df_long['installations'] = pd.to_numeric(df_long['installations'], errors='coerce').fillna(0).astype(int)
    df_long = df_long.rename(columns={pc_col: 'postcode'})
    df_long = df_long[df_long['installations'] > 0].copy()
    
    df_clean = df_long[['postcode', 'year', 'month', 'installations']].copy()
    df_clean = df_clean.sort_values(['postcode', 'year', 'month']).reset_index(drop=True)
    print(f"  Clean rows: {len(df_clean)}")
    
    yearly = df_clean.groupby('year')['installations'].sum().reset_index()
    yearly.columns = ['year', 'total_installations']

    # Count months per year to detect incomplete years
    months_per_year = df_clean.groupby('year')['month'].nunique().reset_index()
    months_per_year.columns = ['year', 'months_count']
    yearly = yearly.merge(months_per_year, on='year')

    # Calculate projected full-year totals for like-for-like growth comparison
    yearly['projected_annual'] = (yearly['total_installations'] / yearly['months_count'] * 12).astype(int)

    # Growth % based on projected annual totals (fair comparison)
    yearly['growth_pct'] = yearly['projected_annual'].pct_change().mul(100).round(1)
    yearly['growth_pct_note'] = ''
    for i, row in yearly.iterrows():
        if row['months_count'] < 12:
            yearly.loc[i, 'growth_pct_note'] = f"Incomplete ({row['months_count']} months)"

    yearly['cumulative'] = yearly['total_installations'].cumsum()
    yearly = yearly.drop(columns=['months_count', 'projected_annual'])
    
    print(f"\n  {'Year':<6} {'Installations':>14} {'Growth':>8} {'Cumulative':>12}")
    print(f"  {'-'*42}")
    for _, row in yearly.iterrows():
        gr = f"{row['growth_pct']:+.1f}%" if pd.notna(row['growth_pct']) else ""
        print(f"  {int(row['year']):<6} {int(row['total_installations']):>14,} {gr:>8} {int(row['cumulative']):>12,}")
    
    print(f"\n  Total: {int(yearly['total_installations'].sum()):,}")
    peak = yearly.loc[yearly['total_installations'].idxmax()]
    print(f"  Peak year: {int(peak['year'])} with {int(peak['total_installations']):,}")
    
    return df_clean, yearly


# ===== RUN =====
solar_monthly, solar_yearly = process_file(os.path.join(DATA_DIR, "solar_raw.csv"), "Solar")
battery_monthly, battery_yearly = process_file(os.path.join(DATA_DIR, "battery_raw.csv"), "Battery")

# ===== TOP POSTCODES =====
if solar_monthly is not None:
    print(f"\n{'='*60}")
    print("Top 20 NSW Postcodes by Solar Installations")
    print(f"{'='*60}")
    top = solar_monthly.groupby('postcode')['installations'].sum().sort_values(ascending=False).head(20).reset_index()
    top.columns = ['postcode', 'total_installations']
    top['rank'] = range(1, len(top) + 1)
    top = top[['rank', 'postcode', 'total_installations']]
    for _, row in top.iterrows():
        print(f"  {int(row['rank']):>3}. {row['postcode']}  {int(row['total_installations']):>10,}")
    top.to_csv(os.path.join(OUTPUT_DIR, "nsw_top_postcodes.csv"), index=False)

# ===== SAVE =====
print(f"\n{'='*60}")
print("Saving files")
print(f"{'='*60}")

if solar_monthly is not None:
    solar_monthly.to_csv(os.path.join(OUTPUT_DIR, "nsw_solar_monthly.csv"), index=False)
    print(f"  output/nsw_solar_monthly.csv ({len(solar_monthly)} rows)")
if solar_yearly is not None:
    solar_yearly.to_csv(os.path.join(OUTPUT_DIR, "nsw_solar_yearly_summary.csv"), index=False)
    print(f"  output/nsw_solar_yearly_summary.csv ({len(solar_yearly)} rows)")
if battery_monthly is not None:
    battery_monthly.to_csv(os.path.join(OUTPUT_DIR, "nsw_battery_monthly.csv"), index=False)
    print(f"  output/nsw_battery_monthly.csv ({len(battery_monthly)} rows)")
if battery_yearly is not None:
    bat_max_year = battery_monthly['year'].max()
    bat_months_in_current = battery_monthly[battery_monthly['year'] == bat_max_year]['month'].nunique()
    battery_yearly['is_complete_year'] = battery_yearly['year'].apply(
        lambda x: 'No' if x == bat_max_year else 'Yes'
    )
    battery_yearly['projected_full_year'] = None
    if bat_months_in_current < 12:
        bat_current_total = battery_yearly[battery_yearly['year'] == bat_max_year]['total_installations'].values[0]
        bat_projected = int(bat_current_total / bat_months_in_current * 12)
        battery_yearly.loc[battery_yearly['year'] == bat_max_year, 'projected_full_year'] = bat_projected
        print(f"  Battery {bat_max_year} has {bat_months_in_current} months. Projected: {bat_projected:,}")
    battery_yearly.to_csv(os.path.join(OUTPUT_DIR, "nsw_battery_yearly_summary.csv"), index=False)
    print(f"  output/nsw_battery_yearly_summary.csv ({len(battery_yearly)} rows)")

with open(os.path.join(OUTPUT_DIR, "issues_log.txt"), 'w') as f:
    f.write("NSW Solar & Battery Data Quality Issues Log\n")
    f.write("=" * 50 + "\n")
    f.write("Source: Clean Energy Regulator (CER)\n")
    f.write("URL: https://cer.gov.au\n\n")
    for issue in issues:
        f.write(f"- {issue}\n")
print(f"  output/issues_log.txt")

# ===== ENHANCE SOLAR MONTHLY WITH DASHBOARD FIELDS =====
if solar_monthly is not None:
    print(f"\n{'='*60}")
    print("Adding dashboard fields to solar monthly")
    print(f"{'='*60}")
    
    month_map = {'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,
                 'Jul':7,'Aug':8,'Sep':9,'Oct':10,'Nov':11,'Dec':12}
    solar_monthly['month_num'] = solar_monthly['month'].map(month_map)
    solar_monthly['quarter'] = solar_monthly['month_num'].map(lambda x: f"Q{(x-1)//3+1}")
    solar_monthly['date'] = pd.to_datetime(
        solar_monthly['year'].astype(str) + '-' + solar_monthly['month_num'].astype(str) + '-01'
    )
    solar_monthly['year_month'] = solar_monthly['date'].dt.strftime('%Y-%m')
    max_year = solar_monthly['year'].max()
    solar_monthly['is_current_year'] = solar_monthly['year'].apply(
        lambda x: 'Yes' if x == max_year else 'No'
    )
    solar_monthly = solar_monthly.sort_values(['postcode', 'date'])
    solar_monthly['cumulative_by_postcode'] = solar_monthly.groupby('postcode')['installations'].cumsum()
    solar_monthly = solar_monthly.sort_values(['date', 'postcode']).reset_index(drop=True)
    
    # Resave with new columns
    solar_monthly.to_csv(os.path.join(OUTPUT_DIR, "nsw_solar_monthly.csv"), index=False)
    print(f"  Resaved: output/nsw_solar_monthly.csv (added month_num, quarter, date, year_month, is_current_year, cumulative_by_postcode)")

# ===== ENHANCE YEARLY WITH PROJECTED =====
if solar_yearly is not None:
    months_in_current = solar_monthly[solar_monthly['year'] == max_year]['month_num'].nunique()
    current_total = solar_yearly[solar_yearly['year'] == max_year]['total_installations'].values[0]
    solar_yearly['is_complete_year'] = solar_yearly['year'].apply(
        lambda x: 'No' if x == max_year else 'Yes'
    )
    solar_yearly['projected_full_year'] = None
    if months_in_current < 12:
        projected = int(current_total / months_in_current * 12)
        solar_yearly.loc[solar_yearly['year'] == max_year, 'projected_full_year'] = projected
        print(f"  {max_year} has {months_in_current} months. Projected full year: {projected:,}")
    
    solar_yearly.to_csv(os.path.join(OUTPUT_DIR, "nsw_solar_yearly_summary.csv"), index=False)
    print(f"  Resaved: output/nsw_solar_yearly_summary.csv (added is_complete_year, projected_full_year)")

# ===== ENHANCE BATTERY MONTHLY =====
if battery_monthly is not None:
    month_map = {'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,
                 'Jul':7,'Aug':8,'Sep':9,'Oct':10,'Nov':11,'Dec':12}
    battery_monthly['month_num'] = battery_monthly['month'].map(month_map)
    battery_monthly['quarter'] = battery_monthly['month_num'].map(lambda x: f"Q{(x-1)//3+1}")
    battery_monthly['date'] = pd.to_datetime(
        battery_monthly['year'].astype(str) + '-' + battery_monthly['month_num'].astype(str) + '-01'
    )
    battery_monthly['year_month'] = battery_monthly['date'].dt.strftime('%Y-%m')
    battery_monthly = battery_monthly.sort_values(['date', 'postcode']).reset_index(drop=True)
    battery_monthly.to_csv(os.path.join(OUTPUT_DIR, "nsw_battery_monthly.csv"), index=False)
    print(f"  Resaved: output/nsw_battery_monthly.csv (added month_num, quarter, date, year_month)")

# ===== ENHANCE TOP POSTCODES WITH SUBURB NAMES =====
if solar_monthly is not None:
    suburb_map = {
        '2765':'Marsden Park / Box Hill','2155':'Kellyville / Rouse Hill',
        '2259':'Central Coast (Wyong)','2560':'Campbelltown','2170':'Liverpool',
        '2480':'Lismore / Byron','2570':'Camden','2830':'Dubbo',
        '2444':'Port Macquarie','2650':'Wagga Wagga','2540':'Nowra / Shoalhaven',
        '2450':'Coffs Harbour','2340':'Tamworth','2250':'Gosford / Central Coast',
        '2800':'Orange','2486':'Tweed Heads','2153':'Baulkham Hills',
        '2615':'Queanbeyan area','2640':'Albury','2478':'Ballina / Lennox Head',
    }
    top_file = os.path.join(OUTPUT_DIR, "nsw_top_postcodes.csv")
    tp = pd.read_csv(top_file)
    tp['postcode'] = tp['postcode'].astype(str).str.zfill(4)
    tp['suburb'] = tp['postcode'].map(suburb_map).fillna('')
    tp.to_csv(top_file, index=False)
    print(f"  Resaved: output/nsw_top_postcodes.csv (added suburb names)")

# ===== QUARTERLY SUMMARY =====
if solar_monthly is not None:
    print(f"\n{'='*60}")
    print("Creating quarterly summary and dashboard cards")
    print(f"{'='*60}")
    
    sq = solar_monthly.groupby(['year', 'quarter']).agg(
        total_installations=('installations', 'sum'),
        active_postcodes=('postcode', 'nunique')
    ).reset_index()
    sq = sq.sort_values(['year', 'quarter']).reset_index(drop=True)
    sq['year_quarter'] = sq['year'].astype(str) + ' ' + sq['quarter']
    sq.to_csv(os.path.join(OUTPUT_DIR, "nsw_solar_quarterly_summary.csv"), index=False)
    print(f"  Saved: output/nsw_solar_quarterly_summary.csv ({len(sq)} rows)")

# ===== DASHBOARD CARDS =====
if solar_monthly is not None and solar_yearly is not None:
    complete_years = solar_yearly[solar_yearly['is_complete_year'] == 'Yes']
    peak_idx = complete_years['total_installations'].idxmax()
    
    cards = {
        'total_solar_installations': int(solar_monthly['installations'].sum()),
        'total_postcodes': int(solar_monthly['postcode'].nunique()),
        'peak_year': int(solar_yearly.loc[peak_idx, 'year']),
        'peak_year_installations': int(complete_years['total_installations'].max()),
        'latest_year': int(max_year),
        'latest_year_installations': int(current_total),
        'latest_year_months': int(months_in_current),
        'latest_year_projected': int(projected) if months_in_current < 12 else int(current_total),
        'total_battery_installations': int(battery_monthly['installations'].sum()) if battery_monthly is not None else 0,
        'top_postcode': tp.iloc[0]['postcode'],
        'top_postcode_suburb': tp.iloc[0]['suburb'],
        'top_postcode_installations': int(tp.iloc[0]['total_installations']),
    }
    pd.DataFrame([cards]).to_csv(os.path.join(OUTPUT_DIR, "nsw_dashboard_cards.csv"), index=False)
    print(f"  Saved: output/nsw_dashboard_cards.csv")
    
    print(f"\n  Dashboard card values:")
    for k, v in cards.items():
        print(f"    {k}: {v}")

print(f"\n{'='*60}")
print("DONE! All output files are in the output/ folder:")
print(f"{'='*60}")
print("  nsw_solar_monthly.csv           - monthly data with dashboard fields")
print("  nsw_solar_yearly_summary.csv    - yearly totals with growth and projections")
print("  nsw_solar_quarterly_summary.csv - quarterly totals")
print("  nsw_battery_monthly.csv         - battery data with dashboard fields")
print("  nsw_battery_yearly_summary.csv  - battery yearly totals")
print("  nsw_top_postcodes.csv           - top 20 postcodes with suburb names")
print("  nsw_dashboard_cards.csv         - pre-calculated card values")
print("  issues_log.txt                  - data quality issues")
