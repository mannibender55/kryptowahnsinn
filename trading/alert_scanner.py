import sqlite3
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime
import json
import sys

# --- Configuration ---
DB_PATH = "/home/manni/.openclaw/workspace/trading/data/hyperliquid.db"
# We define the "Best" parameters per coin/interval based on optimization results.
# Or we use a robust "Default" if no specific optimization was found.
# Let's use the TOP optimized params where available, otherwise fallback.

# Format: 'SYMBOL_INTERVAL': {'rsi_len': 14, 'rsi_os': 30, 'rsi_ob': 70, 'sl': 0.02, 'tp': 0.04}
STRATEGIES = {
    # TOP PERFORMERS (From Optimization)
    'LINK_4h': {'rsi_len': 14, 'rsi_os': 45, 'rsi_ob': 55, 'sl': 0.05, 'tp': 0.10}, # +239%
    'ETH_1h':  {'rsi_len': 14, 'rsi_os': 45, 'rsi_ob': 55, 'sl': 0.05, 'tp': 0.10}, # +110%
    'BNB_4h':  {'rsi_len': 14, 'rsi_os': 35, 'rsi_ob': 65, 'sl': 0.03, 'tp': 0.06}, # +78%
    'SOL_4h':  {'rsi_len': 14, 'rsi_os': 40, 'rsi_ob': 60, 'sl': 0.01, 'tp': 0.02}, # +45%
    'BTC_4h':  {'rsi_len': 14, 'rsi_os': 30, 'rsi_ob': 70, 'sl': 0.03, 'tp': 0.06}, # +41%
    
    # Defaults for others (Conservative)
    'DEFAULT_1h': {'rsi_len': 14, 'rsi_os': 30, 'rsi_ob': 70, 'sl': 0.02, 'tp': 0.04},
    'DEFAULT_4h': {'rsi_len': 14, 'rsi_os': 30, 'rsi_ob': 70, 'sl': 0.03, 'tp': 0.06}
}

COINS = ['BTC', 'ETH', 'SOL', 'BNB', 'ARB', 'OP', 'SUI', 'MATIC', 'LINK', 'DOGE']
INTERVALS = ['1h', '4h']

def get_strategy(symbol, interval):
    key = f"{symbol}_{interval}"
    if key in STRATEGIES:
        return STRATEGIES[key]
    else:
        return STRATEGIES[f"DEFAULT_{interval}"]

def check_signals():
    conn = sqlite3.connect(DB_PATH)
    alerts = []
    
    print(f"Checking signals at {datetime.now()}...", flush=True)
    
    for symbol in COINS:
        for interval in INTERVALS:
            # Load Data (Last 100 candles is enough for RSI + Pivot)
            query = f"SELECT timestamp, open, high, low, close, volume FROM candles WHERE symbol='{symbol}' AND interval='{interval}' ORDER BY timestamp DESC LIMIT 100"
            df = pd.read_sql_query(query, conn)
            
            if df.empty or len(df) < 50: continue
            
            # Sort ascending for calculation
            df = df.sort_values('timestamp')
            
            # Get Params
            strat = get_strategy(symbol, interval)
            
            # Calc RSI
            df['RSI'] = ta.rsi(df['close'], length=strat['rsi_len'])
            
            # Pivot Detection (Lookback 2)
            n = 2
            # We only need to check the *latest* completed candle for a signal.
            # Pivot at i-n is confirmed at i.
            # So we check if a signal fired at the last closed candle (iloc[-1] or iloc[-2]?)
            # Usually we want the signal *as soon as it closes*.
            # If we run this every hour, we check the last closed 1h candle.
            
            # Let's calculate for the last few candles to be sure we didn't miss it
            # Pivot logic: low[i-n] is min of [i-2n ... i]
            # So if i is the last closed candle, we check if i-n was a pivot and if divergence existed.
            
            # Indices:
            # -1 is the last candle in DF.
            # -1-n is the potential pivot candle.
            # We need to check if -1-n was a pivot using data up to -1.
            
            last_idx = len(df) - 1
            pivot_idx = last_idx - n
            
            if pivot_idx < 0: continue

            # Check Pivot Low
            lows = df['low'].values
            is_pivot_low = True
            # Check window around pivot_idx: [pivot_idx - n, pivot_idx + n]
            # Verify range bounds
            start_window = pivot_idx - n
            end_window = pivot_idx + n
            
            if start_window < 0 or end_window > last_idx: continue # Should not happen with limit 100
            
            pivot_low_val = lows[pivot_idx]
            for k in range(start_window, end_window + 1):
                if lows[k] < pivot_low_val:
                    is_pivot_low = False
                    break
            
            # Check Pivot High
            highs = df['high'].values
            is_pivot_high = True
            pivot_high_val = highs[pivot_idx]
            for k in range(start_window, end_window + 1):
                if highs[k] > pivot_high_val:
                    is_pivot_high = False
                    break
            
            # --- Bullish Div Logic ---
            if is_pivot_low:
                # Find previous pivot low
                # Loop backwards from start_window - 1
                prev_pivot_idx = -1
                for k in range(start_window - 1, 0, -1):
                    # Check if k is a pivot low
                    # Need full window [k-n, k+n]
                    # We can't easily check full pivot property without full scan.
                    # Simplified: Just find a local minimum in the past?
                    # Strict: Re-run pivot check for k.
                    
                    # Optimization: Just check if lows[k] is a local low?
                    # Let's use the same logic as backtest:
                    # Rolling check would be easier but we are in a loop.
                    # Let's assume we find *any* recent low that is Higher than current?
                    # Wait, Bullish Div: Price Lower Low, RSI Higher Low.
                    
                    # Let's use the Pivot Low found at pivot_idx.
                    curr_rsi = df['RSI'].iloc[pivot_idx]
                    curr_low = df['low'].iloc[pivot_idx]
                    
                    # Filter: RSI Oversold
                    if curr_rsi < strat['rsi_os']:
                         # Look for ANY previous pivot low in last 30 candles
                         # that has Higher Low Price but Lower RSI? NO.
                         # Bullish Div:
                         # Current Price (Low) < Prev Price (Low)
                         # Current RSI > Prev RSI
                         
                         # Let's search back 20 candles
                         found_div = False
                         for j in range(pivot_idx - 1, max(0, pivot_idx - 30), -1):
                             # Is j a pivot low? (Approximate check: is it lower than neighbors?)
                             if lows[j] < lows[j-1] and lows[j] < lows[j+1]:
                                 prev_low = lows[j]
                                 prev_rsi = df['RSI'].iloc[j]
                                 
                                 if curr_low < prev_low and curr_rsi > prev_rsi:
                                     # FOUND DIV!
                                     alerts.append({
                                         'symbol': symbol,
                                         'interval': interval,
                                         'type': 'BUY (Bullish Div)',
                                         'price': df['close'].iloc[-1],
                                         'sl': df['close'].iloc[-1] * (1 - strat['sl']),
                                         'tp': df['close'].iloc[-1] * (1 + strat['tp']),
                                         'time': df.index[pivot_idx] # Time of pivot
                                     })
                                     found_div = True
                                     break
                         if found_div: break

            # --- Bearish Div Logic ---
            if is_pivot_high:
                curr_rsi = df['RSI'].iloc[pivot_idx]
                curr_high = df['high'].iloc[pivot_idx]
                
                if curr_rsi > strat['rsi_ob']:
                     # Search back
                     found_div = False
                     for j in range(pivot_idx - 1, max(0, pivot_idx - 30), -1):
                         if highs[j] > highs[j-1] and highs[j] > highs[j+1]:
                             prev_high = highs[j]
                             prev_rsi = df['RSI'].iloc[j]
                             
                             if curr_high > prev_high and curr_rsi < prev_rsi:
                                 # FOUND DIV!
                                 alerts.append({
                                     'symbol': symbol,
                                     'interval': interval,
                                     'type': 'SELL (Bearish Div)',
                                     'price': df['close'].iloc[-1],
                                     'sl': df['close'].iloc[-1] * (1 + strat['sl']),
                                     'tp': df['close'].iloc[-1] * (1 - strat['tp']),
                                     'time': df.index[pivot_idx]
                                 })
                                 found_div = True
                                 break
                     if found_div: break
    
    conn.close()
    
    # Save to JSON for Dashboard
    try:
        with open("/home/manni/.openclaw/workspace/trading/dashboard/signals.json", "w") as f:
            json.dump(alerts, f)
    except:
        pass

    # Print Alerts as JSON for the Agent to read and send
    if alerts:
        print(json.dumps(alerts))
    else:
        # Output explicit empty status for heartbeat
        print(json.dumps([{"type": "STATUS", "message": "No signals found via RSI Divergence strategy. System active."}]))

if __name__ == "__main__":
    check_signals()
