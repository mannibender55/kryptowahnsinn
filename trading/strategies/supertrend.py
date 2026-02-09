import sqlite3
import pandas as pd
import pandas_ta as ta
import numpy as np
import os

DB_PATH = "/home/manni/.openclaw/workspace/trading/data/hyperliquid.db"

def backtest_supertrend(df, length=10, multiplier=3.0, sl_pct=0.03, tp_pct=0.06):
    """
    SuperTrend Strategy:
    - Long when SuperTrend flips to bullish (Price > SuperTrend)
    - Short when SuperTrend flips to bearish (Price < SuperTrend)
    """
    # Calculate SuperTrend
    st = ta.supertrend(df['high'], df['low'], df['close'], length=length, multiplier=multiplier)
    if st is None: return 1000.0, []
    
    # Debug: print(f"ST shape: {st.shape}, NaNs: {st.isna().sum().sum()}")
    
    df = pd.concat([df, st], axis=1)
    # st column names can vary (e.g. SUPERTd_7_3.0 or SUPERTd_7_3)
    # Let's find the correct column name dynamically
    col_name = [c for c in df.columns if c.startswith('SUPERTd')][0]
    
    # Drop warmup
    df = df.dropna().reset_index(drop=True)
    
    capital = 1000.0
    position = 0
    entry_price = 0.0
    trades = []

    for i in range(1, len(df)):
        price = df['close'][i]
        direction = df[col_name][i] # 1 for bullish, -1 for bearish
        prev_direction = df[col_name][i-1]
        date = df['timestamp'][i]

        # Exit logic
        if position != 0:
            exit_price = 0
            if position == 1 and (direction == -1 or price <= entry_price * (1 - sl_pct) or price >= entry_price * (1 + tp_pct)):
                exit_price = price
                profit = (exit_price - entry_price) * (capital / entry_price)
                capital += profit
                trades.append({'type': 'EXIT_LONG', 'profit': profit, 'capital': capital, 'date': date})
                position = 0
            elif position == -1 and (direction == 1 or price >= entry_price * (1 + sl_pct) or price <= entry_price * (1 - tp_pct)):
                exit_price = price
                profit = (entry_price - exit_price) * (capital / entry_price)
                capital += profit
                trades.append({'type': 'EXIT_SHORT', 'profit': profit, 'capital': capital, 'date': date})
                position = 0

        # Entry logic
        if position == 0:
            if direction == 1 and prev_direction == -1: # Flip to bullish
                position = 1
                entry_price = price
                trades.append({'type': 'ENTRY_LONG', 'price': price, 'date': date})
            elif direction == -1 and prev_direction == 1: # Flip to bearish
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
            query = f"SELECT timestamp, open, high, low, close FROM candles WHERE symbol='{coin}' AND interval='{interval}' ORDER BY timestamp ASC"
            df = pd.read_sql_query(query, conn)
            # print(f"Processing {coin} {interval}, rows: {len(df)}")
            if len(df) < 100: continue
            
            # Optimization grid
            best_ret = -100
            best_params = {}
            
            for length in [7, 10, 14]:
                for mult in [2.0, 3.0, 4.0]:
                    final_cap, trades = backtest_supertrend(df, length=length, multiplier=mult)
                    ret = ((final_cap - 1000) / 1000) * 100
                    if ret > best_ret:
                        best_ret = ret
                        best_params = {'length': length, 'multiplier': mult, 'trades': len(trades)//2}
            
            results.append({
                'coin': coin,
                'interval': interval,
                'return': best_ret,
                'params': best_params
            })
            print(f"Optimized {coin} {interval}: {best_ret:.2f}% return with {best_params}")

    conn.close()
    
    # Save results to JSON for dashboard
    with open("/home/manni/.openclaw/workspace/trading/dashboard/supertrend_results.json", "w") as f:
        import json
        json.dump(results, f, indent=4)

if __name__ == "__main__":
    run_optimization()
