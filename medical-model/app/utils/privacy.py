import numpy as np
from typing import Tuple


def laplace_noise(shape: Tuple[int, ...], epsilon: float, sensitivity: float = 1.0) -> np.ndarray:
    """Laplace 噪声机制"""
    scale = sensitivity / epsilon
    return np.random.laplace(0, scale, shape)


def gaussian_noise(shape: Tuple[int, ...], epsilon: float, delta: float,
                   sensitivity: float = 1.0) -> np.ndarray:
    """Gaussian 噪声机制"""
    sigma = sensitivity * np.sqrt(2 * np.log(1.25 / delta)) / epsilon
    return np.random.normal(0, sigma, shape)