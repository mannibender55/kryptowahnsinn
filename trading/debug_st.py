import pandas as pd
import pandas_ta as ta
import sqlite3

df = pd.DataFrame({
    'high': [10, 11, 12, 11, 10, 9, 8, 9, 10] * 10,
    'low': [9, 10, 11, 10, 9, 8, 7, 8, 9] * 10,
    'close': [9.5, 10.5, 11.5, 10.5, 9.5, 8.5, 7.5, 8.5, 9.5] * 10
})

st = ta.supertrend(df['high'], df['low'], df['close'], length=7, multiplier=3.0)
print(st.columns)
print(st.head())
