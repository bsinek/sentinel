import numpy as np
import pandas as pd

def estimate_params(prices: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    estimates the annual mu and covariance matrix 

    :param prices: DataFrame with dates as indices and tickers as columns
    :returns: tuple of (S0, mu, cov)
        - S0: (n_assets,) initial prices for simulation
        - mu: (n_assets,) mean log returns annualized
        - cov: (n_assets, n_assets) covariance matrix of log returns annualized
    """
    log_returns = np.log(prices / prices.shift(1)).dropna()

    mu = log_returns.mean().values * 252
    cov = log_returns.cov().values * 252
    S0 = prices.iloc[-1].values

    return S0, mu, cov
