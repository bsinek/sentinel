import numpy as np

def _calculate_terminal_returns(portfolio_paths):
    """
    Compute the total return for each path from first to last time step.

    :param portfolio_paths: (n_simulations, n_steps) array of portfolio values
    :returns: (n_simulations,) array of terminal returns as decimals
    """
    portfolio_paths = np.asarray(portfolio_paths)

    initial = portfolio_paths[:, 0]
    final = portfolio_paths[:, -1]
    return (final - initial) / initial


def mean_return(portfolio_paths):
    """
    Compute the mean return across all simulation paths.

    :param portfolio_paths: (n_simulations, n_steps) array of portfolio values
    :returns: scalar mean return as a decimal
    """
    portfolio_paths = np.asarray(portfolio_paths)

    return _calculate_terminal_returns(portfolio_paths).mean()


def median_return(portfolio_paths):
    """
    Compute the median return across all simulation paths.

    :param portfolio_paths: (n_simulations, n_steps) array of portfolio values
    :returns: scalar median return as a decimal
    """
    portfolio_paths = np.asarray(portfolio_paths)

    return np.median(_calculate_terminal_returns(portfolio_paths))


def var(portfolio_paths, alpha=0.95):
    """
    Compute Value at Risk (VaR) at the given confidence level.

    Returns the minimum terminal return in the worst (1 - alpha) fraction of simulations.
    E.g. at alpha=0.95, this is the 5th percentile of terminal returns.

    :param portfolio_paths: (n_simulations, n_steps) array of portfolio values
    :param alpha: confidence level (default 0.95)
    :returns: scalar VaR as a decimal return (negative = loss)
    """
    portfolio_paths = np.asarray(portfolio_paths)

    terminal_returns = _calculate_terminal_returns(portfolio_paths)
    var = np.percentile(terminal_returns, (1 - alpha) * 100)
    return var


def cvar(portfolio_paths, alpha=0.95):
    """
    Compute Conditional Value at Risk (CVaR / Expected Shortfall) at the given confidence level.

    Returns the mean terminal return across all simulations that fall at or below the VaR threshold.
    Represents the expected loss in the tail beyond VaR.

    :param portfolio_paths: (n_simulations, n_steps) array of portfolio values
    :param alpha: confidence level (default 0.95)
    :returns: scalar CVaR as a decimal return (negative = loss)
    """
    portfolio_paths = np.asarray(portfolio_paths)
    
    terminal_returns = _calculate_terminal_returns(portfolio_paths)
    var_threshold = np.percentile(terminal_returns, (1 - alpha) * 100)
    cvar = terminal_returns[terminal_returns <= var_threshold].mean()
    return cvar


def cagr(portfolio_paths, dt):
    """
    Compute the Compound Annual Growth Rate (CAGR) for each simulation path.

    :param portfolio_paths: (n_simulations, n_steps) array of portfolio values
    :param dt: time delta between steps in years (e.g. 1/252 for daily)
    :returns: (n_simulations,) array of annualized growth rates as decimals
    """
    portfolio_paths = np.asarray(portfolio_paths)

    years = (portfolio_paths.shape[1] - 1) * dt
    initial = portfolio_paths[:, 0]
    final = portfolio_paths[:, -1]
    return (final / initial) ** (1 / years) - 1


def volatility(portfolio_paths, dt):
    """
    Compute annualized volatility across all simulation paths.

    Calculates per-step simple returns across all paths, takes the standard deviation,
    then annualizes by dividing by sqrt(dt).

    :param portfolio_paths: (n_simulations, n_steps) array of portfolio values
    :param dt: time delta between steps in years (e.g. 1/252 for daily)
    :returns: scalar annualized volatility as a decimal
    """
    portfolio_paths = np.asarray(portfolio_paths)

    returns = portfolio_paths[:, 1:] / portfolio_paths[:, :-1] - 1
    vol_per_step = returns.std(ddof=1)
    return vol_per_step / np.sqrt(dt)


def sharpe(portfolio_paths, dt, risk_free_rate=0.0):
    """
    Compute the annualized Sharpe ratio across all simulation paths.

    :param portfolio_paths: (n_simulations, n_steps) array of portfolio values
    :param dt: time delta between steps in years (e.g. 1/252 for daily)
    :param risk_free_rate: annualized risk-free rate as a decimal (default 0.0)
    :returns: scalar Sharpe ratio
    """
    portfolio_paths = np.asarray(portfolio_paths)

    returns = portfolio_paths[:, 1:] / portfolio_paths[:, :-1] - 1
    ann_vol = returns.std(ddof=1) / np.sqrt(dt)
    ann_return = returns.mean() / dt
    return (ann_return - risk_free_rate) / ann_vol


def max_drawdown(portfolio_paths):
    """
    Compute the maximum drawdown for each simulation path.

    :param portfolio_paths: (n_simulations, n_steps) array of portfolio values
    :returns: (n_simulations,) array of maximum drawdowns as decimals (negative = drawdown)
    """
    portfolio_paths = np.asarray(portfolio_paths)

    running_peak = np.maximum.accumulate(portfolio_paths, axis=1)
    drawdowns = (portfolio_paths - running_peak) / running_peak
    return drawdowns.min(axis=1)


def prob_loss(portfolio_paths):
    """
    Compute the probability of a loss across all simulation paths.

    :param portfolio_paths: (n_simulations, n_steps) array of portfolio values
    :returns: scalar probability in [0, 1]
    """
    portfolio_paths = np.asarray(portfolio_paths)

    terminal_returns = _calculate_terminal_returns(portfolio_paths)
    return (terminal_returns < 0).mean()
