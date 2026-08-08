import time
import random
import threading
from benchmark.metrics import calculate_percentiles

class ConcurrentRunner:
    def __init__(self, query_set, node_ids, num_threads=10, duration_seconds=60):
        self.query_set = query_set
        self.node_ids = node_ids
        self.num_threads = num_threads
        self.duration_seconds = duration_seconds
        
        self.latencies = []
        self.total_ops = 0
        self.success_ops = 0
        self.fail_ops = 0
        
        self.lock = threading.Lock()
        self.stop_event = threading.Event()

    def worker(self):
        while not self.stop_event.is_set():
            is_read = random.random() < 0.8
            start_time = time.perf_counter()
            success = False
            
            try:
                if is_read:
                    node = random.choice(self.node_ids)
                    self.query_set.hop_1(node)
                else:
                    src = random.choice(self.node_ids)
                    tgt = random.choice(self.node_ids)
                    while src == tgt:
                        tgt = random.choice(self.node_ids)
                    self.query_set.insert_edge(src, tgt)
                success = True
            except Exception as e:
                # Suppress output during load test to avoid console spamming, but count failure
                pass
            
            latency = (time.perf_counter() - start_time) * 1000.0  # convert to ms
            
            with self.lock:
                self.total_ops += 1
                if success:
                    self.success_ops += 1
                    self.latencies.append(latency)
                else:
                    self.fail_ops += 1
            
            # Removed artificial throttling to allow full throughput

    def run(self):
        print(f"[{self.query_set.loader.name} Concurrent] Starting {self.num_threads} threads for {self.duration_seconds}s...")
        threads = []
        for _ in range(self.num_threads):
            t = threading.Thread(target=self.worker)
            threads.append(t)
            t.start()
            
        time.sleep(self.duration_seconds)
        self.stop_event.set()
        
        for t in threads:
            t.join()
            
        print(f"[{self.query_set.loader.name} Concurrent] Finished load test.")
        
        qps = self.success_ops / self.duration_seconds
        percentiles = calculate_percentiles(self.latencies)
        
        return {
            "total_operations": self.total_ops,
            "successful_operations": self.success_ops,
            "failed_operations": self.fail_ops,
            "queries_per_second": round(qps, 3),
            "p50_latency_ms": percentiles["p50"],
            "p95_latency_ms": percentiles["p95"]
        }
