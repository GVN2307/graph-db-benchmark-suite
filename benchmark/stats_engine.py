import statistics
import numpy as np
from typing import List, Dict
try:
    from hdrhistogram import HdrHistogram
except ImportError:
    import hdrh.histogram as hdrh
    HdrHistogram = hdrh.HdrHistogram

class BenchmarkStatistics:
    """
    Production-grade statistical analysis for latency benchmarking.
    Uses HDR Histogram (Gil Tene) + bootstrap confidence intervals.
    """
    
    def __init__(self):
        # 1us to 1hr (3600000000us), 3 significant figures
        self.histogram = HdrHistogram(1, 3600000000, 3)
    
    def record(self, latency_ms: float):
        # Convert ms to microseconds for the histogram
        microsec = int(latency_ms * 1000)
        if microsec < 1:
            microsec = 1
        elif microsec > 3600000000:
            microsec = 3600000000
        self.histogram.record_value(microsec)
    
    def get_report(self) -> Dict:
        h = self.histogram
        total_count = h.get_total_count()
        if total_count == 0:
            # No latency samples recorded – return an explicit error to avoid misleading zero metrics
            return {"error": "no_samples", "count": 0}
        
        return {
            "count": total_count,
            "mean_ms": round(h.get_mean_value() / 1000.0, 3),
            "stddev_ms": round(h.get_stddev() / 1000.0, 3),
            "cv": round(h.get_stddev() / h.get_mean_value(), 3) if h.get_mean_value() > 0 else 0,
            "min_ms": round(h.get_min_value() / 1000.0, 3),
            "p50_ms": round(h.get_value_at_percentile(50.0) / 1000.0, 3),
            "p75_ms": round(h.get_value_at_percentile(75.0) / 1000.0, 3),
            "p90_ms": round(h.get_value_at_percentile(90.0) / 1000.0, 3),
            "p95_ms": round(h.get_value_at_percentile(95.0) / 1000.0, 3),
            "p99_ms": round(h.get_value_at_percentile(99.0) / 1000.0, 3),
            "p99_9_ms": round(h.get_value_at_percentile(99.9) / 1000.0, 3),
            "p99_99_ms": round(h.get_value_at_percentile(99.99) / 1000.0, 3),
            "max_ms": round(h.get_max_value() / 1000.0, 3),
        }
    
    @staticmethod
    def bootstrap_ci(latencies_ms: List[float], confidence: float = 0.95, n_bootstrap: int = 1000) -> Dict:
        """Bootstrap confidence intervals for mean and p95."""
        if len(latencies_ms) < 30:
            return {"mean_ci": (0, 0), "p95_ci": (0, 0), "note": "insufficient_samples"}
        
        samples = np.array(latencies_ms)
        boot_means = []
        boot_p95s = []
        
        for _ in range(n_bootstrap):
            boot = np.random.choice(samples, size=len(samples), replace=True)
            boot_means.append(np.mean(boot))
            boot_p95s.append(np.percentile(boot, 95))
        
        alpha = 1 - confidence
        mean_low = np.percentile(boot_means, alpha/2 * 100)
        mean_high = np.percentile(boot_means, (1 - alpha/2) * 100)
        p95_low = np.percentile(boot_p95s, alpha/2 * 100)
        p95_high = np.percentile(boot_p95s, (1 - alpha/2) * 100)
        
        return {
            "mean_ci": (round(mean_low, 3), round(mean_high, 3)),
            "p95_ci": (round(p95_low, 3), round(p95_high, 3)),
            "ci_width_pct": round((mean_high - mean_low) / np.mean(samples) * 100, 2)
        }
    
    @staticmethod
    def mann_whitney_u(group_a: List[float], group_b: List[float]) -> Dict:
        """
        Test if two platforms have statistically different latency distributions.
        Returns p-value. p < 0.05 means significantly different.
        """
        from scipy import stats
        if not group_a or not group_b:
            return {"statistic": 0.0, "p_value": 1.0, "significant": False, "winner": "None"}
        statistic, p_value = stats.mannwhitneyu(group_a, group_b, alternative='two-sided')
        return {
            "statistic": statistic,
            "p_value": round(p_value, 6),
            "significant": p_value < 0.05,
            "winner": "A" if np.median(group_a) < np.median(group_b) else "B"
        }
