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
    prices = yf.download(tickers, start=start, end=end, interval=interval, auto_adjust=True, progress=False)['Close']

    # yfinance returns a Series (not DataFrame) when downloading a single ticker
    if isinstance(prices, pd.Series):
        prices = prices.to_frame(name=tickers[0])

    prices = prices.ffill().dropna()

    if prices.empty:
        raise ValueError(f'No valid data returned for {tickers} between {start} and {end}')
    
    # minimum window of 30 days
    # 2 * assets ensures covariance matrix stability
    min_required = max(30, len(prices.columns) * 2)
    if len(prices) < min_required:
        raise ValueError(f'Insufficient data: Need at least {min_required} days for {len(prices.columns)} tickers. Got {len(prices)}')

    return prices
