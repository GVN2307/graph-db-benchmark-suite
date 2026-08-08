import psutil
import time
import threading
import statistics
from typing import Dict, List

class SystemMonitor:
    """Monitor client-side resources during benchmark execution."""
    
    def __init__(self, interval_sec: float = 1.0):
        self.interval = interval_sec
        self.samples: List[Dict] = []
        self._stop = threading.Event()
        self._thread = None
        self.process = psutil.Process()
    
    def start(self):
        self.samples = []
        self._stop.clear()
        self._thread = threading.Thread(target=self._collect)
        self._thread.start()
    
    def _collect(self):
        # Initial call to cpu_percent to initialize
        psutil.cpu_percent(interval=None)
        while not self._stop.is_set():
            sample = {
                "timestamp": time.time(),
                "cpu_percent": psutil.cpu_percent(interval=None),
                "mem_rss_mb": self.process.memory_info().rss / 1024 / 1024,
                "mem_vms_mb": self.process.memory_info().vms / 1024 / 1024,
                "net_sent_mb": psutil.net_io_counters().bytes_sent / 1024 / 1024,
                "net_recv_mb": psutil.net_io_counters().bytes_recv / 1024 / 1024,
                "open_fds": self.process.num_fds() if hasattr(self.process, 'num_fds') else 0,
                "thread_count": self.process.num_threads(),
            }
            self.samples.append(sample)
            time.sleep(self.interval)
    
    def stop(self) -> Dict:
        self._stop.set()
        if self._thread:
            self._thread.join()
        
        if not self.samples:
            return {}
        
        return {
            "peak_cpu": max(s["cpu_percent"] for s in self.samples) if self.samples else 0.0,
            "peak_mem_rss_mb": max(s["mem_rss_mb"] for s in self.samples) if self.samples else 0.0,
            "avg_cpu": statistics.mean(s["cpu_percent"] for s in self.samples) if self.samples else 0.0,
            "total_net_sent_mb": round(self.samples[-1]["net_sent_mb"] - self.samples[0]["net_sent_mb"], 3) if len(self.samples) > 1 else 0.0,
            "total_net_recv_mb": round(self.samples[-1]["net_recv_mb"] - self.samples[0]["net_recv_mb"], 3) if len(self.samples) > 1 else 0.0,
            "duration_sec": round(self.samples[-1]["timestamp"] - self.samples[0]["timestamp"], 3) if self.samples else 0.0,
        }

class CostAnalyzer:
    """
    Extrapolate free-tier performance to paid-tier costs.
    """
    
    PRICING = {
        "Neo4jAura": {"tier": "AuraDB Professional", "hourly": 0.18, "storage_gb_month": 0.25},
        "CognoDB": {"tier": "Standard", "hourly": 0.12, "storage_gb_month": 0.15},
        "FalkorDB": {"tier": "Pro 250MB", "hourly": 0.08, "storage_gb_month": 0.10},
        "TypeDB": {"tier": "Cloud Standard", "hourly": 0.15, "storage_gb_month": 0.20},
        "NebulaGraph": {"tier": "Cloud Enterprise", "hourly": 0.22, "storage_gb_month": 0.30},
    }
    
    @classmethod
    def analyze(cls, platform: str, total_queries: int, duration_hours: float, data_size_gb: float) -> Dict:
        pricing = cls.PRICING.get(platform, {})
        compute_cost = pricing.get("hourly", 0.0) * duration_hours
        storage_cost = pricing.get("storage_gb_month", 0.0) * data_size_gb / 730.0  # hourly storage
        
        total_cost = compute_cost + storage_cost
        cost_per_1k = (total_cost / total_queries) * 1000.0 if total_queries > 0 else 0.0
        
        return {
            "platform": platform,
            "compute_cost_usd": round(compute_cost, 4),
            "storage_cost_usd": round(storage_cost, 6),
            "total_cost_usd": round(total_cost, 4),
            "cost_per_1k_queries_usd": round(cost_per_1k, 6),
            "cost_per_million_queries_usd": round(cost_per_1k * 1000.0, 2),
        }
