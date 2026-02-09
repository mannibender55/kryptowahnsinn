import sqlite3
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime

# --- Configuration ---
DB_PATH = "/home/manni/.openclaw/workspace/trading/data/hyperliquid.db"
RSI_LENGTH = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
STOP_LOSS_PCT = 0.03 # 3% Stop Loss
TAKE_PROFIT_PCT = 0.06 # 6% Take Profit (2:1 Ratio)

def detect_divergence(df):
    """
    Detects Regular Bullish and Bearish RSI Divergences.
    """
    df['RSI'] = ta.rsi(df['close'], length=RSI_LENGTH)
    
    n = 2 
    df['is_pivot_low'] = df['low'].rolling(window=n*2+1, center=True).min() == df['low']
    df['is_pivot_high'] = df['high'].rolling(window=n*2+1, center=True).max() == df['high']
    
    df['signal'] = 0 
    
    last_pivot_low_idx = None
    last_pivot_high_idx = None
    
    closes = df['close'].values
    lows = df['low'].values
    highs = df['high'].values
    rsis = df['RSI'].values
    is_pl = df['is_pivot_low'].values
    is_ph = df['is_pivot_high'].values
    
    signals = np.zeros(len(df))
    
    for i in range(RSI_LENGTH + n, len(df) - n):
        pivot_idx = i - n
        
        # Bullish Divergence
        if is_pl[pivot_idx]:
            curr_low = lows[pivot_idx]
            curr_rsi = rsis[pivot_idx]
            if last_pivot_low_idx is not None:
                prev_low = lows[last_pivot_low_idx]
                prev_rsi = rsis[last_pivot_low_idx]
                if curr_low < prev_low and curr_rsi > prev_rsi:
                    signals[i] = 1 
            last_pivot_low_idx = pivot_idx

        # Bearish Divergence
        if is_ph[pivot_idx]:
            curr_high = highs[pivot_idx]
            curr_rsi = rsis[pivot_idx]
            if last_pivot_high_idx is not None:
                prev_high = highs[last_pivot_high_idx]
                prev_rsi = rsis[last_pivot_high_idx]
                if curr_high > prev_high and curr_rsi < prev_rsi:
                    signals[i] = -1
            last_pivot_high_idx = pivot_idx

    df['signal'] = signals
    return df

def run_backtest(symbol, interval, initial_capital=1000):
    conn = sqlite3.connect(DB_PATH)
    query = f"SELECT timestamp, open, high, low, close, volume FROM candles WHERE symbol='{symbol}' AND interval='{interval}' ORDER BY timestamp ASC"
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        print(f"No data for {symbol} {interval}")
        return

    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('date', inplace=True)
    
    # Detect Signals
    df = detect_divergence(df)
    
    capital = initial_capital
    position = 0 # 0: flat, >0: long size, <0: short size
    entry_price = 0
    stop_loss = 0
    take_profit = 0 
    trades = []
    
    for i in range(len(df)):
        row = df.iloc[i]
        price = row['close']
        signal = row['signal']
        date = row.name
        
        # --- Check OPEN Position ---
        if position != 0:
            exit_type = None
            
            if position > 0: # LONG
                if price <= stop_loss: exit_type = "Stop Loss"
                elif price >= take_profit: exit_type = "Take Profit"
                # Time exit? Or reversal? 
                
            elif position < 0: # SHORT
                if price >= stop_loss: exit_type = "Stop Loss"
                elif price <= take_profit: exit_type = "Take Profit"
            
            if exit_type:
                # Calculate PnL
                if position > 0:
                    profit = (price - entry_price) * position
                    capital += (position * entry_price) + profit
                else:
                    profit = (entry_price - price) * abs(position)
                    capital += (abs(position) * entry_price) + profit
                
                trades.append({'type': 'CLOSE', 'side': 'LONG' if position > 0 else 'SHORT', 'date': date, 'price': price, 'profit': profit, 'reason': exit_type})
                position = 0

        # --- Check NEW Entry ---
        if position == 0:
            if signal == 1 and row['RSI'] < 35: # Bullish Entry
                position = capital / price
                entry_price = price
                capital -= (position * price)
                stop_loss = price * (1 - STOP_LOSS_PCT)
                take_profit = price * (1 + TAKE_PROFIT_PCT)
                trades.append({'type': 'OPEN', 'side': 'LONG', 'date': date, 'price': price})
                
            elif signal == -1 and row['RSI'] > 65: # Bearish Entry
                size = capital / price
                position = -size
                entry_price = price
                capital -= (size * price)
                stop_loss = price * (1 + STOP_LOSS_PCT)
                take_profit = price * (1 - TAKE_PROFIT_PCT)
                trades.append({'type': 'OPEN', 'side': 'SHORT', 'date': date, 'price': price})

    # Final Value
    if position != 0:
        curr_val = 0
        if position > 0:
            curr_val = position * df.iloc[-1]['close']
        else:
            profit = (entry_price - df.iloc[-1]['close']) * abs(position)
            curr_val = (abs(position) * entry_price) + profit
        final_value = capital + curr_val
    else:
        final_value = capital
        
    profit_pct = ((final_value - initial_capital) / initial_capital) * 100
    
    print(f"\n=== Backtest Result: {symbol} ({interval}) ===")
    print(f"Initial Capital: ${initial_capital}")
    print(f"Final Value:     ${final_value:.2f}")
    print(f"Total Return:    {profit_pct:.2f}%")
    print(f"Trades Executed: {len(trades)}")
    
    wins = [t for t in trades if t['type']=='CLOSE' and t['profit'] > 0]
    losses = [t for t in trades if t['type']=='CLOSE' and t['profit'] <= 0]
    win_rate = (len(wins) / len([t for t in trades if t['type']=='CLOSE'])) * 100 if trades else 0
    print(f"Win Rate:        {win_rate:.1f}% ({len(wins)} W / {len(losses)} L)")

    if trades:
        print("Last 5 Trades:")
        for t in trades[-5:]:
            p_str = f" (${t['profit']:.2f})" if 'profit' in t else ""
            side = t.get('side', '')
            print(f"  {t['date']} {t['type']} {side} @ {t['price']:.2f} {t.get('reason','')}{p_str}")

if __name__ == "__main__":
    print("Running RSI Divergence Backtest (Long/Short + SL/TP)...")
    run_backtest("BTC", "1h")
    run_backtest("ETH", "1h")
    run_backtest("SOL", "4h")
