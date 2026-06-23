#!/usr/bin/env python3
"""
Microgrid Load Profile Generator
Generate synthetic load profiles for microgrid simulation studies.
"""

import numpy as np
import json
import sys
from datetime import datetime, timedelta

def generate_load_profile(
    peak_kw: float = 100,
    base_load_pct: float = 0.3,
    residential_pct: float = 0.4,
    commercial_pct: float = 0.4,
    industrial_pct: float = 0.2,
    season: str = "summer",
    resolution_min: int = 15,
    noise_std: float = 0.05,
    days: int = 1
):
    """Generate a synthetic microgrid load profile."""
    
    # Seasonal factors
    season_factors = {
        "summer": {"peak_hour": 14, "ac_penalty": 1.25},
        "winter": {"peak_hour": 18, "ac_penalty": 1.15},
        "spring": {"peak_hour": 10, "ac_penalty": 1.0},
        "fall": {"peak_hour": 17, "ac_penalty": 1.05}
    }
    sf = season_factors.get(season, season_factors["summer"])
    
    points_per_day = int(24 * 60 / resolution_min)
    total_points = points_per_day * days
    t = np.linspace(0, 24 * days, total_points, endpoint=False)
    hour = t % 24
    
    # Residential profile (evening peak)
    res = np.exp(-((hour - 20) ** 2) / 8) + 0.5 * np.exp(-((hour - 12) ** 2) / 16)
    res = res / res.max()  # normalize
    
    # Commercial profile (daytime peak)
    com = np.exp(-((hour - sf["peak_hour"]) ** 2) / 6) * 0.8 + 0.2
    com[hour < 6] = 0.1
    com[hour > 20] = 0.15
    com = com / com.max()
    
    # Industrial profile (base + daytime)
    ind = 0.6 + 0.4 * np.exp(-((hour - 13) ** 2) / 36)
    ind = ind / ind.max()
    
    # Combine
    load = (residential_pct * res + commercial_pct * com + industrial_pct * ind)
    load = load / load.max()  # normalize
    load = load * (1 - base_load_pct) + base_load_pct
    load = load * peak_kw
    
    # Add noise
    noise = np.random.normal(0, noise_std * peak_kw, total_points)
    load = np.maximum(load + noise, peak_kw * 0.05)
    
    # Add AC penalty in summer
    if sf["ac_penalty"] > 1.0:
        ac_load = np.exp(-((hour - 14) ** 2) / 6)
        load = load * (1 + ac_load * (sf["ac_penalty"] - 1) * 0.3)
    
    timestamps = [(datetime(2025, 6, 1) + timedelta(minutes=i * resolution_min)).isoformat()
                  for i in range(total_points)]
    
    return {
        "metadata": {
            "peak_kw": peak_kw,
            "resolution_min": resolution_min,
            "season": season,
            "profile_mix": {
                "residential": residential_pct,
                "commercial": commercial_pct,
                "industrial": industrial_pct
            }
        },
        "statistics": {
            "peak_kw": round(float(load.max()), 2),
            "min_kw": round(float(load.min()), 2),
            "avg_kw": round(float(load.mean()), 2),
            "load_factor": round(float(load.mean() / load.max()), 3),
            "total_kwh": round(float(load.sum() * resolution_min / 60), 1)
        },
        "timestamps": timestamps,
        "loads_kw": [round(float(v), 2) for v in load]
    }


def main():
    if len(sys.argv) > 1:
        config = json.loads(sys.argv[1])
    else:
        config = {}
    
    profile = generate_load_profile(**config)
    print(json.dumps(profile, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
