import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# --- Configuration ---
# To scan all 500, you would read a CSV from NSE. 
# For demonstration, here is a small list of Nifty stocks. 
# Note: Indian stocks on Yahoo Finance require the '.NS' suffix.
NIFTY_TICKERS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", 
    "HUL.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS",
    "TATAMOTORS.NS", "M&M.NS", "ASIANPAINT.NS", "MARUTI.NS", "SUNPHARMA.NS"
]

# Parameters
LOOKBACK_DAYS = 120  # ~6 months of trading days
PROXIMITY_PCT = 0.02 # Within 2% of the resistance level

def find_breakout_candidates(tickers):
    candidates = []
    
    print(f"Fetching data for {len(tickers)} tickers...")
    # Fetch data in bulk for efficiency
    data = yf.download(tickers, period="1y", interval="1d", group_by="ticker", threads=True)
    
    for ticker in tickers:
        try:
            # Handle single vs multiple ticker download structures
            if len(tickers) == 1:
                df = data.copy()
            else:
                df = data[ticker].copy()
                
            df = df.dropna()
            
            if len(df) < LOOKBACK_DAYS:
                continue
                
            # Get the closing prices for the lookback period
            recent_data = df.tail(LOOKBACK_DAYS)
            
            current_price = recent_data['Close'].iloc[-1]
            resistance_level = recent_data['Close'].max()
            
            # Check if the current price is nearing the resistance
            distance_to_resistance = (resistance_level - current_price) / resistance_level
            
            # Criteria: Price is below resistance, but within the 2% proximity threshold
            # Also ensure the price isn't actively crashing (e.g., current price > 20 day SMA)
            sma_20 = recent_data['Close'].tail(20).mean()
            
            if 0 <= distance_to_resistance <= PROXIMITY_PCT and current_price > sma_20:
                candidates.append({
                    'Ticker': ticker.replace('.NS', ''),
                    'Current Price': round(current_price, 2),
                    'Resistance Level': round(resistance_level, 2),
                    'Distance (%)': round(distance_to_resistance * 100, 2)
                })
        except Exception as e:
            print(f"Error processing {ticker}: {e}")
            
    return pd.DataFrame(candidates)

if __name__ == "__main__":
    # In a real scenario, load your 500 tickers from a CSV:
    # df_nifty500 = pd.read_csv('ind_nifty500list.csv')
    # NIFTY_TICKERS = [symbol + '.NS' for symbol in df_nifty500['Symbol'].tolist()]
    
    print(f"Starting Scan at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    results = find_breakout_candidates(NIFTY_TICKERS)
    
    if not results.empty:
        # Sort by closest to resistance
        results = results.sort_values(by='Distance (%)', ascending=True)
        print("\n🚀 STOCKS NEARING BREAKOUT 🚀")
        print("-" * 50)
        print(results.to_string(index=False))
        print("-" * 50)
    else:
        print("\nNo stocks meeting the breakout criteria today.")
