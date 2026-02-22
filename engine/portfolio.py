import numpy as np

def aggregate_portfolio(price_paths, weights):
    """
    aggregates asset prices paths into portfolio price paths
    
    :param price_paths: price paths of assets
    :param weights: portfolio allocation weights
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
