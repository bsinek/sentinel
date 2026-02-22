import numpy as np

def simulate_gbm(S0, mu, cov, dt, n_steps, n_sims):
    """
    simulate geometric brownian motion via monte carlo simulations
    
    :param S0: initial asset prices
    :param mu: mean log asset drifts
    :param cov: covariance matrix
    :param dt: time step size
    :param n_steps: number of time steps
    :param n_sims: number of simulations
    :returns: (n_sims, n_steps+1, n_assets) array of simulated price paths
    """

    # convert to numpy arrays
    S0 = np.asarray(S0)
    mu = np.asarray(mu)
    cov = np.asarray(cov)

    n_assets = len(S0)

    # ito-adjusted drift
    variance = np.diag(cov)
    drift = (mu - 0.5 * variance) * dt

    # correlated diffusion
    chol_factor = np.linalg.cholesky(covariance)
    Z = np.random.normal(size=(n_sims, n_steps, n_assets))
    diffusion = Z @ chol_factor.T

    # simulate gbm
    log_increments = drift + diffusion * np.sqrt(dt)

    # build log paths + add initial zero term
    log_paths = np.cumsum(log_increments, axis=1)
    log_paths = np.concat([np.zeros((n_sims, 1, n_assets)), log_paths], axis=1)
    
    # convert to price paths
    price_paths = S0 * np.exp(log_paths)

    return price_paths
