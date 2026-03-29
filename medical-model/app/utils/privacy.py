import numpy as np
from typing import Tuple

def laplace_noise(shape: Tuple[int, ...], epsilon: float, sensitivity: float = 1.0) -> np.ndarray:
    scale = sensitivity / epsilon
    return np.random.laplace(0, scale, shape)

def gaussian_noise(shape: Tuple[int, ...], epsilon: float, delta: float, sensitivity: float = 1.0) -> np.ndarray:
    sigma = sensitivity * np.sqrt(2 * np.log(1.25 / delta)) / epsilon
    return np.random.normal(0, sigma, shape)

def clip_gradient(gradient: np.ndarray, max_norm: float) -> np.ndarray:
    norm = np.linalg.norm(gradient)
    if norm > max_norm:
        gradient = gradient * (max_norm / norm)
    return gradient

def compute_epsilon_spent(steps: int, batch_size: int, dataset_size: int, 
                          noise_multiplier: float, delta: float) -> float:
    q = batch_size / dataset_size
    orders = [1 + x / 10.0 for x in range(1, 100)] + list(range(12, 64))
    rdp = compute_rdp(q, noise_multiplier, steps, orders)
    eps, _, _ = get_privacy_spent(orders, rdp, target_delta=delta)
    return eps

def compute_rdp(q, noise_multiplier, steps, orders):
    if q == 0:
        return np.inf
    if noise_multiplier == 0:
        return np.inf
    rdp = np.zeros_like(orders, dtype=float)
    for i, order in enumerate(orders):
        if order == 1:
            rdp[i] = np.inf
        else:
            rdp[i] = order * q ** 2 / (noise_multiplier ** 2)
    return rdp * steps

def get_privacy_spent(orders, rdp, target_delta):
    orders = np.atleast_1d(orders)
    rdp = np.atleast_1d(rdp)
    deltas = np.exp((rdp - np.log(target_delta)) * (orders - 1) - np.log(orders - 1))
    idx = np.argmin(deltas)
    return deltas[idx], orders[idx], target_delta
