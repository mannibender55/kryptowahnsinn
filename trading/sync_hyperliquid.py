import sqlite3
import requests
import time
import os
import sys
from datetime import datetime, timedelta

# Configuration
DB_PATH = "/home/manni/.openclaw/workspace/trading/data/hyperliquid.db"
API_URL = "https://api.hyperliquid.xyz/info"
TIMEFRAMES = ["15m", "1h", "4h"]
# Default lookback for fresh sync (e.g. 30 days). Increase if needed, but mind API limits.
MAX_LOOKBACK_DAYS = 365 * 2 # 2 years

# List of coins to track. We can make this dynamic later.
COINS = ["BTC", "ETH", "SOL", "BNB", "ARB", "OP", "SUI", "MATIC", "LINK", "DOGE"] 

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Ensure table exists with correct schema
    c.execute('''
        CREATE TABLE IF NOT EXISTS candles (
            symbol TEXT,
            interval TEXT,
            timestamp INTEGER,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            PRIMARY KEY (symbol, interval, timestamp)
        )
    ''')
    conn.commit()
    conn.close()

def get_time_range(coin, interval):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT MIN(timestamp), MAX(timestamp) FROM candles WHERE symbol = ? AND interval = ?', (coin, interval))
    result = c.fetchone()
    conn.close()
    return result if result and result[0] else (None, None)

def fetch_candles_chunk(coin, interval, start_time, end_time):
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": coin,
            "interval": interval,
            "startTime": start_time,
            "endTime": end_time
        }
    }
    
    max_retries = 5
    backoff = 2
    
    for i in range(max_retries):
        try:
            response = requests.post(API_URL, json=payload, headers={"Content-Type": "application/json"}, timeout=15)
            if response.status_code == 429:
                print(f"Rate limited (429). Waiting {backoff}s...", flush=True)
                time.sleep(backoff)
                backoff *= 2
                continue
            response.raise_for_status()
            data = response.json()
            return data
        except Exception as e:
            if i == max_retries - 1:
                print(f"Error fetching {coin} {interval} after {max_retries} retries: {e}", flush=True)
            else:
                time.sleep(1)
                continue
    return []

def save_candles(coin, interval, candles):
    if not candles:
        return 0
        
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    count = 0
    
    for candle in candles:
        try:
            ts = candle['t']
            o = float(candle['o'])
            h = float(candle['h'])
            l = float(candle['l'])
            cl = float(candle['c'])
            v = float(candle['v'])
            
            c.execute('''
                INSERT OR REPLACE INTO candles (symbol, interval, timestamp, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (coin, interval, ts, o, h, l, cl, v))
            count += 1
        except Exception as e:
            continue
            
    conn.commit()
    conn.close()
    return count

def sync_coin(coin):
    print(f"Syncing {coin}...", flush=True)
    total_saved = 0
    current_time_ms = int(time.time() * 1000)
    target_start_time = int((time.time() - (MAX_LOOKBACK_DAYS * 86400)) * 1000)
    
    for interval in TIMEFRAMES:
        min_ts, max_ts = get_time_range(coin, interval)
        
        start_time = target_start_time
        
        if min_ts is not None:
             # Check if we have data going back far enough (allow 7 days slack)
             if min_ts > target_start_time + (7 * 86400 * 1000):
                 print(f"  {interval}: Existing data starts {datetime.fromtimestamp(min_ts/1000)}. Fetching older data from {datetime.fromtimestamp(target_start_time/1000)}...", flush=True)
                 start_time = target_start_time
             else:
                 print(f"  {interval}: History looks good (starts {datetime.fromtimestamp(min_ts/1000)}). Resuming from {datetime.fromtimestamp(max_ts/1000)}...", flush=True)
                 start_time = max_ts + 1
        else:
             print(f"  {interval}: Initial fetch (last {MAX_LOOKBACK_DAYS/365:.1f} years)", flush=True)
             start_time = target_start_time

        chunk_start = start_time
        loop_guard = 0
        prev_last_ts = None
        
        while chunk_start < current_time_ms:
            loop_guard += 1
            if loop_guard > 500: # Safety break
                print(f"  {interval}: Loop guard hit (500 iterations). Breaking.", flush=True)
                break
                
            candles = fetch_candles_chunk(coin, interval, chunk_start, current_time_ms)
            
            if not candles:
                print(f"  {interval}: No more candles returned from API.", flush=True)
                break
                
            last_candle_ts = candles[-1]['t']
            if last_candle_ts == prev_last_ts:
                print(f"  {interval}: No new candles (stuck at {datetime.fromtimestamp(last_candle_ts/1000)}). breaking.", flush=True)
                break
            prev_last_ts = last_candle_ts

            saved = save_candles(coin, interval, candles)
            total_saved += saved
            print(f"  {interval}: Fetched {len(candles)} candles. Saved {saved}. Latest: {datetime.fromtimestamp(last_candle_ts/1000)}", flush=True)
            
            if last_candle_ts >= current_time_ms - 60000:
                print(f"  {interval}: Caught up to now.", flush=True)
                break
                
            chunk_start = last_candle_ts + 1
            time.sleep(1.0) # Rate limit: 1s

    print(f"  Saved {total_saved} new candles for {coin}.", flush=True)

if __name__ == "__main__":
    init_db()
    print(f"Starting sync at {datetime.now()}", flush=True)
    for coin in COINS:
        sync_coin(coin)
    print("Sync complete.", flush=True)
    
    # Update Dashboard Data
    try:
        import subprocess
        subprocess.run(["python3", "/home/manni/.openclaw/workspace/trading/dashboard/data_exporter.py"], check=True)
    except Exception as e:
        print(f"Dashboard update failed: {e}")
