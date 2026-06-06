import math
import numpy as np
from typing import Dict, Tuple

# High-altitude countries native elevations (metres)
NATIVE_ALTITUDES = {
    "bolivia": 3640.0,
    "ecuador": 2850.0,
    "colombia": 2640.0,
    "mexico": 2240.0,
    "peru": 1500.0,
    "south africa": 1700.0,
    "nepal": 1400.0,
    "switzerland": 540.0,
    "austria": 560.0,
}

def get_native_altitude(team_name: str) -> float:
    """Returns the native training altitude of a team's country."""
    if not team_name:
        return 0.0
    return NATIVE_ALTITUDES.get(team_name.lower().strip(), 0.0)

def get_match_xg(
    elo_a: float,
    elo_b: float,
    is_host_a: bool,
    is_host_b: bool,
    venue_alt: float,
    native_alt_a: float,
    native_alt_b: float,
    travel_a_km: float,
    travel_b_km: float,
    rest_a: float,
    rest_b: float
) -> Tuple[float, float]:
    """
    Computes expected goals (lambda and mu) for Team A and Team B.
    Formula:
      lam = exp(log(1.25) + 0.0016 * (elo_a - elo_b) + host_effect_a + alt_effect_a + travel_effect_a + rest_effect_a)
      mu  = exp(log(1.05) - 0.0016 * (elo_a - elo_b) + host_effect_b + alt_effect_b + travel_effect_b + rest_effect_b)
    """
    # Elo difference effect
    elo_diff = elo_a - elo_b
    elo_effect = 0.0016 * elo_diff

    # Host effects
    host_effect_a = 0.15 if is_host_a else 0.0
    host_effect_b = 0.15 if is_host_b else 0.0

    # Altitude friction effect (reduces goal expectation at high altitudes if not acclimated)
    alt_diff_a = max(0.0, venue_alt - native_alt_a)
    alt_diff_b = max(0.0, venue_alt - native_alt_b)
    alt_effect_a = -0.00008 * alt_diff_a
    alt_effect_b = -0.00008 * alt_diff_b

    # Travel distance fatigue effect
    travel_effect_a = -0.00005 * travel_a_km
    travel_effect_b = -0.00005 * travel_b_km

    # Rest asymmetry fatigue effect (penalize if rest days are under 4)
    rest_effect_a = -0.05 * max(0.0, 4.0 - rest_a)
    rest_effect_b = -0.05 * max(0.0, 4.0 - rest_b)

    # Exponents
    exponent_a = math.log(1.25) + elo_effect + host_effect_a + alt_effect_a + travel_effect_a + rest_effect_a
    exponent_b = math.log(1.05) - elo_effect + host_effect_b + alt_effect_b + travel_effect_b + rest_effect_b

    # Clip exponents to prevent overflow
    exponent_a = np.clip(exponent_a, -3.0, 3.0)
    exponent_b = np.clip(exponent_b, -3.0, 3.0)

    lam = math.exp(exponent_a)
    mu = math.exp(exponent_b)

    return float(lam), float(mu)

def dixon_coles_tau(x: int, y: int, lam: float, mu: float, rho: float = -0.13) -> float:
    """
    Calculates the Dixon-Coles tau adjustment factor to correct for correlation 
    in low-scoring match outcomes.
    """
    if x == 0 and y == 0:
        return 1.0 - lam * mu * rho
    elif x == 0 and y == 1:
        return 1.0 + lam * rho
    elif x == 1 and y == 0:
        return 1.0 + mu * rho
    elif x == 1 and y == 1:
        return 1.0 - rho
    else:
        return 1.0

def get_poisson_probs(lam: float, max_goals: int = 10) -> np.ndarray:
    """Computes a vector of Poisson probabilities for goals from 0 to max_goals."""
    probs = np.zeros(max_goals + 1)
    if lam <= 0:
        probs[0] = 1.0
        return probs
    
    # Calculate iteratively to prevent factorial overflow: P(k) = P(k-1) * lam / k
    probs[0] = math.exp(-lam)
    for k in range(1, max_goals + 1):
        probs[k] = probs[k-1] * lam / k
    return probs

def build_scoreline_grid(lam: float, mu: float, rho: float = -0.13, max_goals: int = 10) -> np.ndarray:
    """
    Builds a normalized joint probability grid for goals up to max_goals.
    Applies the Dixon-Coles tau correlation correction.
    """
    probs_a = get_poisson_probs(lam, max_goals)
    probs_b = get_poisson_probs(mu, max_goals)
    
    # Outer product to get independent Poisson joint probabilities
    grid = np.outer(probs_a, probs_b)
    
    # Apply tau correction for low scores (x in [0, 1] and y in [0, 1])
    grid[0, 0] *= dixon_coles_tau(0, 0, lam, mu, rho)
    grid[0, 1] *= dixon_coles_tau(0, 1, lam, mu, rho)
    grid[1, 0] *= dixon_coles_tau(1, 0, lam, mu, rho)
    grid[1, 1] *= dixon_coles_tau(1, 1, lam, mu, rho)
    
    # Clip negative probabilities if any (due to extreme rho/lambda values)
    grid = np.clip(grid, 0.0, None)
    
    # Normalize grid so sum of all cells is exactly 1.0
    grid_sum = np.sum(grid)
    if grid_sum > 0:
        grid /= grid_sum
    else:
        grid[0, 0] = 1.0
        
    return grid

def sample_scoreline(lam: float, mu: float, rho: float = -0.13, max_goals: int = 10) -> Tuple[int, int]:
    """
    Samples a scoreline (goals_a, goals_b) from the Dixon-Coles joint distribution.
    """
    grid = build_scoreline_grid(lam, mu, rho, max_goals)
    flat_grid = grid.flatten()
    
    # Draw index from flat grid using probabilities
    idx = np.random.choice(len(flat_grid), p=flat_grid)
    
    # Unflatten index to get goals_a (row) and goals_b (column)
    goals_a = int(idx // (max_goals + 1))
    goals_b = int(idx % (max_goals + 1))
    
    return goals_a, goals_b
