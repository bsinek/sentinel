import numpy as np

def aggregate_portfolio(price_paths: np.ndarray, weights: np.ndarray | None = None) -> np.ndarray:
    """
    aggregates asset prices paths into portfolio price paths
    
    :param price_paths: (n_sims, n_steps+1, n_assets) array of asset price paths
    :param weights: (n_assets,) array of portfolio allocation weights
    :returns: (n_sims, n_steps+1) array of portfolio value paths
    """
    # convert to numpy array
    price_paths = np.asarray(price_paths)

    n_assets = price_paths.shape[2]

    if weights is None:
        weights = np.ones(n_assets) / n_assets
    else:
        # convert to numpy array
        weights = np.asarray(weights)
        
        if len(weights) != n_assets:
            raise ValueError('weights length must match number of assets')
        if not np.isclose(weights.sum(), 1.0):
            raise ValueError('weights must sum to 1')
    
    # matrix mutliplication along assets axis
    portfolio_paths = price_paths @ weights

    return portfolio_paths
