# Scalping Strategy Synthesis

## Sources
- LuxAlgo Blog: "Scalping 101: High-Frequency Trading Tips"
- YouTube: "Best Crypto Scalping Strategy" (LuxAlgo)
- YouTube: "Data Trader’s Best 5-Minute Scalping Strategy Ever"

## Strategy Logic (The "LuxAlgo Scalper" Approach)

### Core Indicators
1. **EMA (Exponential Moving Average):**
   - Use a **short-term EMA (5-13 periods)** for quick trend direction.
   - Use a **long-term EMA (200)** to filter direction (only Long if Price > EMA 200).
2. **RSI (Relative Strength Index):**
   - Period: **14** (standard) or **7** (faster).
   - Use for **Momentum confirmation**.
   - Entry when RSI crosses above 50 (bullish) or below 50 (bearish) in trend direction?
   - OR: Divergences (as tested before).
3. **Bollinger Bands:**
   - Period: **20**, Dev: **2**.
   - Use for **Volatility**. Trade when bands expand (squeeze breakout).

### Entry Rules (Scalping M5 / M15)
- **LONG:**
  - Price > EMA 200 (Uptrend).
  - Price touches/bounces off dynamic support (Smart Trail / EMA).
  - Confirmation: RSI moves up / Bullish candle close.
- **SHORT:**
  - Price < EMA 200 (Downtrend).
  - Price rejects dynamic resistance.
  - Confirmation: RSI moves down.

### Risk Management
- **Stop Loss:** Tight! ~0.5% to 1% (or below recent swing low).
- **Take Profit:** 1.5x Risk (1.5% - 2%).
- **Risk per Trade:** 1% of account.

## Next Steps
- Implement a Python backtest for the "EMA Trend + Pullback" strategy.
- Focus on M5/M15 timeframe (since it's scalping).
