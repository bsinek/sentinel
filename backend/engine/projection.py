import numpy as np

def prepare_projection(portfolio_paths: np.ndarray, alpha: float = 0.95, n_samples: int = 50) -> dict:
    norm_paths = normalize_paths(portfolio_paths)

    return {
        'confidence_bands': confidence_bands(norm_paths, alpha),
        'sample_paths': sample_paths(norm_paths, n_samples),
    }


def normalize_paths(portfolio_paths: np.ndarray) -> np.ndarray:
    return portfolio_paths / portfolio_paths[:, 0:1]


def confidence_bands(norm_paths: np.ndarray, alpha: float = 0.95) -> dict:
    return {
        'upper_band': np.percentile(norm_paths, alpha * 100, axis=0),
        'median_band': np.median(norm_paths, axis=0),
        'lower_band': np.percentile(norm_paths, (1 - alpha) * 100, axis=0),
    }


def sample_paths(norm_paths: np.ndarray, n_samples: int = 50) -> np.ndarray:
    n_total = norm_paths.shape[0]

    if n_total <= n_samples:
        return norm_paths
    
    sample_indices = np.random.choice(n_total, n_samples, replace=False)
    return norm_paths[sample_indices, :]
