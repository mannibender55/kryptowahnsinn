import sqlite3
import pandas as pd
import pandas_ta as ta
import numpy as np
import os
import json

DB_PATH = "/home/manni/.openclaw/workspace/trading/data/hyperliquid.db"

def backtest_macd(df, fast=12, slow=26, signal=9, sl_pct=0.03, tp_pct=0.06):
    """
    MACD Strategy:
    - Long when MACD crosses above Signal line
    - Short when MACD crosses below Signal line
    """
    macd = ta.macd(df['close'], fast=fast, slow=slow, signal=signal)
    if macd is None: return 1000.0, []
    
    df = pd.concat([df, macd], axis=1)
    macd_col = f"MACD_{fast}_{slow}_{signal}"
    signal_col = f"MACDs_{fast}_{slow}_{signal}"
    
    df = df.dropna().reset_index(drop=True)
    
    capital = 1000.0
    position = 0
    entry_price = 0.0
    trades = []

    for i in range(1, len(df)):
        price = df['close'][i]
        macd_val = df[macd_col][i]
        sig_val = df[signal_col][i]
        prev_macd = df[macd_col][i-1]
        prev_sig = df[signal_col][i-1]
        date = df['timestamp'][i]

        # Exit
        if position != 0:
            if position == 1 and (macd_val < sig_val or price <= entry_price * (1 - sl_pct) or price >= entry_price * (1 + tp_pct)):
                profit = (price - entry_price) * (capital / entry_price)
                capital += profit
                trades.append({'type': 'EXIT_LONG', 'profit': profit, 'capital': capital, 'date': date})
                position = 0
            elif position == -1 and (macd_val > sig_val or price >= entry_price * (1 + sl_pct) or price <= entry_price * (1 - tp_pct)):
                profit = (entry_price - price) * (capital / entry_price)
                capital += profit
                trades.append({'type': 'EXIT_SHORT', 'profit': profit, 'capital': capital, 'date': date})
                position = 0

        # Entry
        if position == 0:
            if macd_val > sig_val and prev_macd <= prev_sig:
                position = 1
                entry_price = price
                trades.append({'type': 'ENTRY_LONG', 'price': price, 'date': date})
            elif macd_val < sig_val and prev_macd >= prev_sig:
                position = -1
                entry_price = price
                trades.append({'type': 'ENTRY_SHORT', 'price': price, 'date': date})

    return capital, trades

def run_optimization():
    conn = sqlite3.connect(DB_PATH)
    coins = ['BTC', 'ETH', 'SOL', 'LINK', 'DOGE']
    intervals = ['1h', '4h']
    results = []
    
    for coin in coins:
        for interval in intervals:
            query = f"SELECT timestamp, close FROM candles WHERE symbol='{coin}' AND interval='{interval}' ORDER BY timestamp ASC"
            df = pd.read_sql_query(query, conn)
            if len(df) < 100: continue
            
            best_ret = -100
            best_params = {}
            
            # Simple grid
            for f, s, sig in [(12,26,9), (8,21,5)]:
                final_cap, trades = backtest_macd(df, fast=f, slow=s, signal=sig)
                ret = ((final_cap - 1000) / 1000) * 100
                if ret > best_ret:
                    best_ret = ret
                    best_params = {'fast': f, 'slow': s, 'signal': sig, 'trades': len(trades)//2}
            
            results.append({
                'coin': coin,
                'interval': interval,
                'return': best_ret,
                'params': best_params
            })
            print(f"Optimized {coin} {interval} (MACD): {best_ret:.2f}% return")

    conn.close()
    with open("/home/manni/.openclaw/workspace/trading/dashboard/macd_results.json", "w") as f:
        json.dump(results, f, indent=4)

if __name__ == "__main__":
    run_optimization()
