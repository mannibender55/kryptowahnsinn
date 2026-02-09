import sqlite3
import pandas as pd

conn = sqlite3.connect("/home/manni/.openclaw/workspace/trading/data/hyperliquid.db")
df = pd.read_sql_query("SELECT * FROM candles WHERE symbol='BTC' AND interval='4h' LIMIT 5", conn)
print(df)
conn.close()
