import sqlite3
import json
import os
from datetime import datetime

DB_PATH = "/home/manni/.openclaw/workspace/trading/data/hyperliquid.db"
JSON_PATH = "/home/manni/.openclaw/workspace/trading/dashboard/data.json"
SIGNALS_PATH = "/home/manni/.openclaw/workspace/trading/dashboard/signals.json"

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
    
    # Format timestamp
    try:
        if isinstance(raw_sync, int):
            last_sync = datetime.fromtimestamp(raw_sync / 1000).strftime('%Y-%m-%d %H:%M')
        else:
            last_sync = str(raw_sync)
    except:
        last_sync = str(raw_sync)

    # Get current prices for tiles
    prices = {}
    for coin in COINS:
        cursor.execute(f"SELECT close FROM candles WHERE symbol='{coin}' ORDER BY timestamp DESC LIMIT 1")
        res = cursor.fetchone()
        prices[coin] = res[0] if res else 0

    # Get chart data for ALL coins
    charts = {}
    for coin in COINS:
        cursor.execute(f"""
            SELECT timestamp, close 
            FROM candles 
            WHERE symbol='{coin}' AND interval='1h' 
            ORDER BY timestamp DESC 
            LIMIT 50
        """)
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
        with open(SIGNALS_PATH, "r") as f:
            signals = json.load(f)

    # Strategy Info (Mocked performance for now, could be dynamic later)
    strategies = [
        {
            "id": "rsi_div",
            "name": "RSI Divergence",
            "status": "active",
            "performance": "+239.3%",
            "trades": [
                {"date": "2026-02-08 14:00", "coin": "LINK", "type": "LONG", "profit": "+10.2%"},
                {"date": "2026-02-07 09:00", "coin": "BTC", "type": "SHORT", "profit": "-2.1%"},
                {"date": "2026-02-05 21:00", "coin": "SOL", "type": "LONG", "profit": "+5.4%"}
            ]
        },
        {
            "id": "ema_pullback",
            "name": "EMA Trend Pullback",
            "status": "inactive",
            "performance": "-12.5%",
            "trades": []
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