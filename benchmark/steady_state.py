import numpy as np
from typing import List, Tuple

class SteadyStateDetector:
    """
    Detects when a JVM/DB has reached steady-state performance.
    Uses CUSUM (Cumulative Sum) control charts.
    """
    
    def __init__(self, window_size: int = 50, threshold: float = 2.0):
        self.window_size = window_size
        self.threshold = threshold
    
    def detect(self, latencies: List[float]) -> Tuple[int, bool]:
        """
        Returns (cutoff_index, is_steady).
        cutoff_index: discard everything before this point.
        """
        if len(latencies) < self.window_size * 3:
            return 0, False  # Not enough data
        
        # Phase 1: Find initial steady window (last N points with low variance)
        windows = []
        for i in range(len(latencies) - self.window_size + 1):
            window = latencies[i:i + self.window_size]
            windows.append((i, np.mean(window), np.std(window)))
        
        # Find window with minimum CV
        best_window = min(windows, key=lambda x: x[2] / x[1] if x[1] > 0 else float('inf'))
        steady_mean = best_window[1]
        steady_std = best_window[2]
        if steady_std == 0:
            steady_std = 1e-9
        
        # Phase 2: CUSUM forward detection
        cusum_pos = 0
        cusum_neg = 0
        cutoff = 0
        
        for i, val in enumerate(latencies):
            cusum_pos = max(0, cusum_pos + (val - steady_mean) / steady_std - 0.5)
            cusum_neg = max(0, cusum_neg - (val - steady_mean) / steady_std - 0.5)
            
            if cusum_pos > self.threshold or cusum_neg > self.threshold:
                cutoff = i
        
        return cutoff, cutoff < len(latencies) * 0.8  # Must reach steady state within 80% of run
