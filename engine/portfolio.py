import numpy as np

def aggregate_portfolio(price_paths: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """
    aggregates asset prices paths into portfolio price paths
    
    :param price_paths: (n_sims, n_steps+1, n_assets) array of asset price paths
    :param weights: (n_assets,) array of portfolio allocation weights
    :returns: (n_sims, n_steps+1) array of portfolio value paths
    """

    # convert to numpy arrays
    price_paths = np.asarray(price_paths)
    weights = np.asarray(weights)

    # input validation
    if price_paths.ndim != 3:
        raise ValueError('price_paths must have shape (n_sims, n_steps + 1, n_assets)')
    
    if weights.ndim != 1:
        raise ValueError('weights must have shape of (n_assets,)')
    
    if len(weights) != price_paths.shape[2]:
        raise ValueError('weights length must match number of assets')
    
    # matrix mutliplication along assets axis
    portfolio_paths = price_paths @ weights

    return portfolio_paths
