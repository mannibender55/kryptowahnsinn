import sqlite3
import requests
import time
import os
import json

DB_PATH = "/home/manni/.openclaw/workspace/trading/data/market_data.db"
API_URL = "https://api.hyperliquid.xyz/info"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
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
    print(f"Database initialized at {DB_PATH}")

def fetch_candles(coin, interval="1h", start_time=None):
    # Hyperliquid expects startTime in ms. Default to 24h ago if None.
    if start_time is None:
        start_time = int((time.time() - 86400) * 1000)
    
    # End time is now
    end_time = int(time.time() * 1000)
    
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": coin,
            "interval": interval,
            "startTime": start_time,
            "endTime": end_time
        }
    }
    
    try:
        response = requests.post(API_URL, json=payload, headers={"Content-Type": "application/json"})
        response.raise_for_status()
        data = response.json()
        return data
    except Exception as e:
        print(f"Error fetching {coin}: {e}")
        return []

def save_candles(coin, interval, candles):
    if not candles:
        return
        
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    count = 0
    for candle in candles:
        # Candle format from Hyperliquid: 
        # { "t": 123456789, "o": "123.45", "h": "125.00", "l": "120.00", "c": "124.00", "v": "1000.5" ... }
        # Note: values are strings in some APIs, need float conversion
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
            print(f"Error parsing candle: {e}")
            continue
            
    conn.commit()
    conn.close()
    print(f"Saved {count} candles for {coin} ({interval})")

if __name__ == "__main__":
    init_db()
    
    # Test run for major coins
    coins = ["BTC", "ETH", "SOL"]
    interval = "1h"
    
    print(f"Fetching test data for {coins}...")
    for coin in coins:
        candles = fetch_candles(coin, interval)
        save_candles(coin, interval, candles)
        time.sleep(1) # Be nice to the API

    print("Setup complete.")
