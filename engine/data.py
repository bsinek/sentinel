import yfinance as yf
import pandas as pd

def fetch_prices(tickers: list[str], start: str, end: str, interval: str = '1d') -> pd.DataFrame:
    """
    Fetch historical closing prices for a list of tickers.

    :param tickers: list of ticker symbols (e.g. ["AAPL", "MSFT"])
    :param start: start date string (e.g. "2022-01-01")
    :param end: end date string (e.g. "2024-01-01")
    :param interval: data frequency — "1d", "1wk", or "1mo" (default "1d")
    :returns: DataFrame with dates as index and tickers as columns, forward-filled and NaN rows dropped
    """
    raw = yf.download(tickers, start=start, end=end, interval=interval, auto_adjust=True)
    prices = raw['Close']
    
    # yfinance returns Series when only 1 ticker
    if isinstance(raw.columns, pd.Series):
        prices = raw[['Close']]
        prices.columns = tickers

    prices = prices.ffill().dropna()

    return prices
