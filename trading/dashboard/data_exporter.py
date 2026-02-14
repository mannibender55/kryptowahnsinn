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

    # Get signals directly from database
    signals = []
    cursor.execute("SELECT id, timestamp, symbol, signal, entry_price, sl_price, tp_price, status, profit_loss FROM signals ORDER BY timestamp DESC")
    for row in cursor.fetchall():
        signals.append({
            "id": row[0],
            "date": row[1],
            "symbol": row[2],
            "signal": row[3],
            "entry": row[4],
            "sl": row[5],
            "tp": row[6],
            "status": row[7],
            "profit_loss": row[8]
        })

    # Load MACD Results
    macd_res = []
    if os.path.exists(MACD_PATH):
        try:
            with open(MACD_PATH, "r") as f:
                macd_res = json.load(f)
        except: pass

    # Strategy Info
    strategies = []
    
    # 1. RSI Divergence
    rsi_trades = []
    # Load from BTC 1h or LINK 4h
    for coin in ['LINK', 'BTC']:
        path = os.path.join(DASH_DIR, f"trades_rsi_{coin}.json")
        if os.path.exists(path):
            with open(path, "r") as f:
                raw_trades = json.load(f)
                # Only take the CLOSE trades for the performance table
                for t in raw_trades:
                    if t['type'] == 'CLOSE' or t['type'] == 'EXIT_LONG' or t['type'] == 'EXIT_SHORT':
                        rsi_trades.append({
                            "date": t['date'],
                            "coin": coin,
                            "type": t.get('side', t['type']),
                            "profit": f"{t['profit']:.2f}$",
                            "entry": f"{t.get('entry', 0):.2f}",
                            "sl": f"{t.get('sl', 0):.2f}",
                            "tp": f"{t.get('tp', 0):.2f}"
                        })

    strategies.append({
        "id": "rsi_div",
        "name": "RSI Divergence",
        "status": "active",
        "performance": "+239.3%",
        "desc": "Optimiert für LINK 4h. Erkennt RSI/Preis Divergenzen.",
        "trades": rsi_trades[::-1][:20] # Last 20 trades
    })

    # 2. MACD Cross
    macd_trades = []
    for coin in ['DOGE', 'ETH', 'BTC']:
        path = os.path.join(DASH_DIR, f"trades_macd_{coin}.json")
        if os.path.exists(path):
            with open(path, "r") as f:
                raw_trades = json.load(f)
                for t in raw_trades:
                    if 'EXIT' in t['type']:
                        macd_trades.append({
                            "date": t['date'],
                            "coin": coin,
                            "type": t['type'].replace('EXIT_', ''),
                            "profit": f"{t['profit']:.2f}$",
                            "entry": f"{t['entry']:.2f}",
                            "sl": f"{t['sl']:.2f}",
                            "tp": f"{t['tp']:.2f}"
                        })

    strategies.append({
        "id": "macd_cross",
        "name": "MACD Cross",
        "status": "active",
        "performance": "+574.8%",
        "desc": "Trend-Folge Strategie. Top Performer bei DOGE 4h.",
        "trades": macd_trades[::-1][:20]
    })

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
