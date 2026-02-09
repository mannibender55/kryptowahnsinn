import sqlite3
import pandas as pd
import pandas_ta as ta
import numpy as np

# --- Strategy Logic ---
def backtest_ema_pullback(df, ema_trend=200, ema_entry=50, sl_atr=2.0, tp_atr=4.0):
    """
    Trend Following Strategy:
    1. Trend Filter: Price > EMA 200 (Long only) / Price < EMA 200 (Short only)
    2. Entry: Price touches EMA 50 (Pullback)
    3. Exit: ATR-based SL/TP
    """
    
    # Indicators
    df['EMA_Trend'] = ta.ema(df['close'], length=ema_trend)
    df['EMA_Entry'] = ta.ema(df['close'], length=ema_entry)
    df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    
    # Drop warmup
    df = df.dropna().reset_index(drop=True)
    
    # Simulation
    capital = 1000.0
    position = 0 # 0: flat, 1: long, -1: short
    entry_price = 0.0
    stop_loss = 0.0
    take_profit = 0.0
    
    trades = []
    
    for i in range(1, len(df)):
        price = df['close'][i]
        high = df['high'][i]
        low = df['low'][i]
        ema_t = df['EMA_Trend'][i]
        ema_e = df['EMA_Entry'][i]
        atr = df['ATR'][i]
        date = df['timestamp'][i]
        
        # --- Check Exit ---
        if position != 0:
            pnl = 0
            exit_reason = None
            
            if position == 1: # LONG
                if low <= stop_loss:
                    exit_price = stop_loss
                    exit_reason = "SL"
                elif high >= take_profit:
                    exit_price = take_profit
                    exit_reason = "TP"
            elif position == -1: # SHORT
                if high >= stop_loss:
                    exit_price = stop_loss
                    exit_reason = "SL"
                elif low <= take_profit:
                    exit_price = take_profit
                    exit_reason = "TP"
            
            if exit_reason:
                # Calc PnL
                if position == 1:
                    profit = (exit_price - entry_price) * (capital / entry_price)
                else:
                    profit = (entry_price - exit_price) * (capital / entry_price)
                
                capital += profit
                trades.append({'type': exit_reason, 'profit': profit, 'capital': capital})
                position = 0
                continue

        # --- Check Entry ---
        if position == 0:
            # LONG Condition
            # Trend is UP (Close > EMA 200) AND Pullback (Low touches EMA 50)
            if df['close'][i-1] > df['EMA_Trend'][i-1] and low <= ema_e and df['close'][i] > ema_e:
                # Entry Long
                position = 1
                entry_price = price
                stop_loss = price - (atr * sl_atr)
                take_profit = price + (atr * tp_atr)
                trades.append({'type': 'ENTRY_LONG', 'price': price, 'date': date})
                
            # SHORT Condition
            # Trend is DOWN (Close < EMA 200) AND Pullback (High touches EMA 50)
            elif df['close'][i-1] < df['EMA_Trend'][i-1] and high >= ema_e and df['close'][i] < ema_e:
                # Entry Short
                position = -1
                entry_price = price
                stop_loss = price + (atr * sl_atr)
                take_profit = price - (atr * tp_atr)
                trades.append({'type': 'ENTRY_SHORT', 'price': price, 'date': date})

    return capital, trades

if __name__ == "__main__":
    conn = sqlite3.connect("/home/manni/.openclaw/workspace/trading/data/hyperliquid.db")
    
    print("Testing EMA Trend Strategy...")
    coins = ['BTC', 'ETH', 'SOL', 'LINK', 'DOGE']
    
    for coin in coins:
        query = f"SELECT timestamp, open, high, low, close, volume FROM candles WHERE symbol='{coin}' AND interval='1h' ORDER BY timestamp ASC"
        df = pd.read_sql_query(query, conn)
        if df.empty: continue
        
        final_cap, trades = backtest_ema_pullback(df)
        ret = ((final_cap - 1000) / 1000) * 100
        print(f"{coin} 1h: Return {ret:.2f}% | Trades: {len(trades)/2:.0f}")
