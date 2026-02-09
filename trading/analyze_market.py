import sqlite3
import pandas as pd
import pandas_ta as ta

DB_PATH = "/home/manni/.openclaw/workspace/trading/data/hyperliquid.db"

def load_data(symbol, interval, limit=200):
    conn = sqlite3.connect(DB_PATH)
    query = f"""
        SELECT timestamp, open, high, low, close, volume 
        FROM candles 
        WHERE symbol = '{symbol}' AND interval = '{interval}' 
        ORDER BY timestamp DESC 
        LIMIT {limit}
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        return df

    # Sort by time ascending for calculation
    df = df.sort_values('timestamp')
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('date', inplace=True)
    return df

def analyze(symbol, interval):
    df = load_data(symbol, interval)
    
    if df.empty:
        print(f"No data for {symbol} {interval}")
        return

    # Calculate Indicators using functional API (safer)
    # RSI
    df['RSI'] = ta.rsi(df['close'], length=14)
    
    # SMA 50
    df['SMA_50'] = ta.sma(df['close'], length=50)
    
    # Bollinger Bands
    bb = ta.bbands(df['close'], length=20, std=2)
    if bb is not None:
        df = pd.concat([df, bb], axis=1)

    print(f"\n--- Analysis for {symbol} ({interval}) ---")
    
    # Select columns to show
    cols = ['close', 'RSI', 'volume']
    if 'SMA_50' in df.columns: cols.append('SMA_50')
    
    print(df[cols].tail())
    
    last_rsi = df['RSI'].iloc[-1]
    last_close = df['close'].iloc[-1]
    
    print(f"Latest: Close={last_close:.2f} | RSI={last_rsi:.2f}")

if __name__ == "__main__":
    print("Running market analysis...")
    try:
        analyze("BTC", "1h")
        analyze("ETH", "15m")
    except Exception as e:
        print(f"Error: {e}")
