import numpy as np
import pandas as pd

def estimate_params(prices: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    log_returns = np.log(prices / prices.shift(1)).dropna()

    if len(log_returns) < 2:
        raise ValueError('not enough data to estimate parameters')

    mu = log_returns.mean().values
    cov = log_returns.cov().values
    S0 = prices.iloc[-1].values

    if np.isnan(cov).any():
        raise ValueError('covariance matrix contains NaN')

    return S0, mu, cov
