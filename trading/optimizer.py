import sqlite3
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime

# --- Configuration ---
DB_PATH = "/home/manni/.openclaw/workspace/trading/data/hyperliquid.db"

# --- Strategy Logic ---
def detect_divergence_signals(df, rsi_length, rsi_oversold, rsi_overbought, lookback=2):
    """
    Returns a Series of signals: 1 (Long), -1 (Short), 0 (None)
    Using vectorized-ish approach for speed in optimization loop.
    """
    # Calculate RSI
    rsi = ta.rsi(df['close'], length=rsi_length)
    if rsi is None: return np.zeros(len(df))
    
    # Pivot Detection
    n = lookback
    lows = df['low']
    highs = df['high']
    
    # Rolling min/max to find pivots
    # Using shift to align "future" lookahead for pivot definition
    # pivot low at i means low[i] < low[i-n...i+n]
    # We can use rolling(window=2n+1, center=True)
    is_pl = (lows.rolling(window=2*n+1, center=True).min() == lows).fillna(False)
    is_ph = (highs.rolling(window=2*n+1, center=True).max() == highs).fillna(False)
    
    # We need to iterate to compare pivots (vectorizing pivot-to-pivot is hard)
    signals = np.zeros(len(df))
    
    last_pl_idx = -1
    last_ph_idx = -1
    
    # Convert to numpy arrays for fast access
    c_lows = lows.values
    c_highs = highs.values
    c_rsi = rsi.values
    c_is_pl = is_pl.values
    c_is_ph = is_ph.values
    
    # Loop starts after RSI warmup
    for i in range(rsi_length + n, len(df) - n):
        # Current confirmation point is i, pivot was at i-n
        pivot_idx = i - n
        
        # Bullish Div Check
        if c_is_pl[pivot_idx]:
            if last_pl_idx != -1:
                # Compare current pivot with last pivot
                if c_lows[pivot_idx] < c_lows[last_pl_idx] and \
                   c_rsi[pivot_idx] > c_rsi[last_pl_idx]:
                    # Filter: RSI Oversold
                    if c_rsi[pivot_idx] < rsi_oversold:
                         signals[i] = 1 # Long Signal
            last_pl_idx = pivot_idx

        # Bearish Div Check
        if c_is_ph[pivot_idx]:
            if last_ph_idx != -1:
                # Compare current pivot with last pivot
                if c_highs[pivot_idx] > c_highs[last_ph_idx] and \
                   c_rsi[pivot_idx] < c_rsi[last_ph_idx]:
                    # Filter: RSI Overbought
                    if c_rsi[pivot_idx] > rsi_overbought:
                         signals[i] = -1 # Short Signal
            last_ph_idx = pivot_idx
            
    return signals

def run_backtest_fast(df, signals, sl_pct, tp_pct):
    """
    Fast backtest for optimization loop. Returns Total Return %.
    Assumes initial capital 1000.
    """
    initial_capital = 1000.0
    capital = initial_capital
    position = 0.0 # size
    entry_price = 0.0
    
    closes = df['close'].values
    
    # Stop/Target prices
    stop_price = 0.0
    target_price = 0.0
    
    # Trade counters
    wins = 0
    losses = 0
    
    for i in range(len(df)):
        price = closes[i]
        signal = signals[i]
        
        # Check Exit
        if position != 0:
            pnl = 0
            closed = False
            
            if position > 0: # LONG
                if price <= stop_price or price >= target_price:
                    pnl = (price - entry_price) * position
                    capital += (position * entry_price) + pnl
                    closed = True
            elif position < 0: # SHORT
                if price >= stop_price or price <= target_price:
                    pnl = (entry_price - price) * abs(position)
                    capital += (abs(position) * entry_price) + pnl
                    closed = True
            
            if closed:
                if pnl > 0: wins += 1
                else: losses += 1
                position = 0
                continue # Trade closed, wait for next candle for new signal
        
        # Check Entry
        if position == 0:
            if signal == 1: # LONG
                position = capital / price
                entry_price = price
                capital -= (position * price)
                stop_price = price * (1.0 - sl_pct)
                target_price = price * (1.0 + tp_pct)
            
            elif signal == -1: # SHORT
                size = capital / price
                position = -size
                entry_price = price
                capital -= (size * price)
                stop_price = price * (1.0 + sl_pct)
                target_price = price * (1.0 - tp_pct)
                
    # Close final
    if position != 0:
        if position > 0:
            final_val = capital + (position * closes[-1])
        else:
            pnl = (entry_price - closes[-1]) * abs(position)
            final_val = capital + (abs(position) * entry_price) + pnl
    else:
        final_val = capital
        
    ret = ((final_val - initial_capital) / initial_capital) * 100
    return ret, wins, losses

def optimize():
    conn = sqlite3.connect(DB_PATH)
    
    # Optimization Parameters
    symbols = ['BTC', 'ETH', 'SOL', 'BNB', 'ARB', 'OP', 'SUI', 'MATIC', 'LINK', 'DOGE']
    intervals = ['15m', '1h', '4h']
    
    rsi_thresholds = [ (30, 70), (35, 65), (40, 60), (45, 55) ] # Added more range
    sl_tp_ratios = [ (0.01, 0.02), (0.02, 0.04), (0.03, 0.06), (0.02, 0.06), (0.05, 0.10) ]
    
    results = []
    
    print("Starting Optimization Run...", flush=True)
    
    for symbol in symbols:
        for interval in intervals:
            # Load Data Once
            query = f"SELECT timestamp, open, high, low, close, volume FROM candles WHERE symbol='{symbol}' AND interval='{interval}' ORDER BY timestamp ASC"
            df = pd.read_sql_query(query, conn)
            if df.empty: continue
            
            print(f"Testing {symbol} {interval} ({len(df)} candles)...", flush=True)
            
            for (oversold, overbought) in rsi_thresholds:
                # Pre-calculate signals for this RSI setting
                signals = detect_divergence_signals(df, 14, oversold, overbought)
                
                if np.sum(np.abs(signals)) == 0:
                    continue # No signals generated
                
                for (sl, tp) in sl_tp_ratios:
                    ret, w, l = run_backtest_fast(df, signals, sl, tp)
                    
                    results.append({
                        'Symbol': symbol,
                        'Interval': interval,
                        'RSI_Set': f"{oversold}/{overbought}",
                        'SL_TP': f"{sl*100:.0f}%/{tp*100:.0f}%",
                        'Return%': ret,
                        'Trades': w + l,
                        'WinRate': (w/(w+l)*100) if (w+l)>0 else 0
                    })
    
    conn.close()
    
    # Convert to DataFrame for sorting
    res_df = pd.DataFrame(results)
    res_df = res_df.sort_values('Return%', ascending=False)
    
    print("\n=== TOP 10 STRATEGIES ===")
    print(res_df.head(10).to_string(index=False))
    
    # Save full results
    res_df.to_csv("/home/manni/.openclaw/workspace/trading/optimization_results.csv", index=False)
    print("\nFull results saved to optimization_results.csv")

if __name__ == "__main__":
    optimize()
