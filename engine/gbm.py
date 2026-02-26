import numpy as np

def simulate_gbm(S0: np.ndarray, mu: np.ndarray, cov: np.ndarray, dt: float, n_steps: int, n_sims: int) -> np.ndarray:
    """
    simulate geometric brownian motion via monte carlo simulations
    
    :param S0: (n_assets,) array of initial asset prices
    :param mu: (n_assets,) array of mean log asset drifts annualized
    :param cov: (n_assets, n_assets) covariance matrix of log returns annualized
    :param dt: time step as a fraction of a year (e.g. 1/252)
    :param n_steps: number of time steps
    :param n_sims: number of simulations
    :returns: (n_sims, n_steps+1, n_assets) array of simulated price paths
    """

    # convert to numpy arrays
    S0 = np.asarray(S0)
    mu = np.asarray(mu)
    cov = np.asarray(cov)

    n_assets = len(S0)

    try:
        chol_factor = np.linalg.cholesky(cov) * np.sqrt(dt)
    except np.linalg.LinAlgError:
        raise ValueError(f'The assets selected are too highly correlated. Try removing duplicate assets or increasing the date range.')
    
    Z = np.random.normal(size=(n_sims, n_steps, n_assets))
    diffusion = Z @ chol_factor.T

    # simulate gbm
    log_increments = mu * dt + diffusion

    # build log paths + add initial zero term
    log_paths = np.cumsum(log_increments, axis=1)
    log_paths = np.concat([np.zeros((n_sims, 1, n_assets)), log_paths], axis=1)
    
    # convert to price paths
    price_paths = S0 * np.exp(log_paths)

    return price_paths
