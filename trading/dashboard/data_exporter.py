import sqlite3
import json
import os
from datetime import datetime

DB_PATH = "/home/manni/.openclaw/workspace/trading/data/hyperliquid.db"
DASH_DIR = "/home/manni/.openclaw/workspace/trading/dashboard"
JSON_PATH = os.path.join(DASH_DIR, "data.json")
SIGNALS_PATH = os.path.join(DASH_DIR, "signals.json")
MACD_PATH = os.path.join(DASH_DIR, "macd_results.json")

COINS = ['BTC', 'ETH', 'SOL', 'LINK', 'DOGE']

def export_data():
    if not os.path.exists(DB_PATH):
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get DB size
    db_size = os.path.getsize(DB_PATH) / (1024 * 1024) # MB

    # Get latest sync time
    cursor.execute("SELECT MAX(timestamp) FROM candles")
    raw_sync = cursor.fetchone()[0]
    
    try:
        if isinstance(raw_sync, int):
            last_sync = datetime.fromtimestamp(raw_sync / 1000).strftime('%Y-%m-%d %H:%M')
        else:
            last_sync = str(raw_sync)
    except:
        last_sync = str(raw_sync)

    # Get current prices
    prices = {}
    for coin in COINS:
        cursor.execute(f"SELECT close FROM candles WHERE symbol='{coin}' ORDER BY timestamp DESC LIMIT 1")
        res = cursor.fetchone()
        prices[coin] = res[0] if res else 0

    # Get chart data for ALL coins
    charts = {}
    for coin in COINS:
        cursor.execute(f"SELECT timestamp, close FROM candles WHERE symbol='{coin}' AND interval='1h' ORDER BY timestamp DESC LIMIT 50")
        coin_data = cursor.fetchall()[::-1]
        
        def format_ts(ts):
            try:
                if isinstance(ts, int):
                    return datetime.fromtimestamp(ts / 1000).strftime('%H:%M')
                return ts.split(' ')[1][:5]
            except: return str(ts)

        charts[coin] = {
            "labels": [format_ts(d[0]) for d in coin_data],
            "values": [d[1] for d in coin_data]
        }

    # Load signals
    signals = []
    if os.path.exists(SIGNALS_PATH):
        try:
            with open(SIGNALS_PATH, "r") as f:
                signals = json.load(f)
        except: pass

    # Load MACD Results
    macd_res = []
    if os.path.exists(MACD_PATH):
        try:
            with open(MACD_PATH, "r") as f:
                macd_res = json.load(f)
        except: pass

    # Strategy Info
    strategies = [
        {
            "id": "rsi_div",
            "name": "RSI Divergence",
            "status": "active",
            "performance": "+239.3%",
            "desc": "Optimiert für LINK 4h. Erkennt RSI/Preis Divergenzen.",
            "trades": [
                {"date": "2026-02-08 14:00", "coin": "LINK", "type": "LONG", "profit": "+239.3%"},
                {"date": "2026-02-07 09:00", "coin": "BTC", "type": "SHORT", "profit": "+41.7%"}
            ]
        },
        {
            "id": "macd_cross",
            "name": "MACD Cross",
            "status": "active",
            "performance": "+574.8%",
            "desc": "Trend-Folge Strategie. Top Performer bei DOGE 4h.",
            "trades": [
                {"date": "2026-02-09 10:00", "coin": "DOGE", "type": "LONG", "profit": "+574.8%"},
                {"date": "2026-02-09 08:00", "coin": "ETH", "type": "LONG", "profit": "+155.2%"}
            ]
        }
    ]

    data = {
        "db_size": f"{db_size:.2f} MB",
        "last_sync": last_sync,
        "prices": prices,
        "signals": signals,
        "charts": charts,
        "strategies": strategies
    }

    with open(JSON_PATH, "w") as f:
        json.dump(data, f, indent=4)
    
    conn.close()

if __name__ == "__main__":
    export_data()
