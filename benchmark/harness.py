import os
import json
import time
import random
from data.download import parse_dataset
from benchmark.stats_engine import BenchmarkStatistics
from benchmark.steady_state import SteadyStateDetector
from benchmark.observability import SystemMonitor, CostAnalyzer
from benchmark.correctness_engine import CorrectnessEngine
from benchmark.concurrent_runner import ConcurrentRunner
from benchmark.dashboard_generator import generate_dashboard

class BenchmarkHarness:
    def __init__(self, loader, query_set, platform_name):
        self.loader = loader
        self.queries = query_set
        self.platform = platform_name
        self.results = {
            "platform": platform_name,
            "metrics": {}
        }
        self.monitor = SystemMonitor(interval_sec=0.5)

    def _execute_with_reconnect(self, func, *args, **kwargs):
        """Execute a query function, reconnecting on connection errors.
        Returns the function result or raises if second attempt fails.
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if self._is_connection_error(e):
                print(f"[{self.platform}] Connection error detected: {e}. Reconnecting...")
                try:
                    self.loader.close()
                except Exception:
                    pass
                self.loader.connect()
                # retry once
                return func(*args, **kwargs)
            else:
                raise

    def run_all(self):
        print(f"\n==================================================")
        print(f"Starting Benchmark Suite for: {self.platform}")
        print(f"==================================================")
        
        # Start CPU/Memory System Monitor
        self.monitor.start()
        
        # 1. Connect
        try:
            self.loader.connect()
        except Exception as e:
            print(f"[{self.platform}] Connection failed: {e}. Skipping benchmark.")
            self.results["error"] = f"Connection failed: {e}"
            self.monitor.stop()
            self.save_results()
            return

        # Load Dataset once for all benchmarks
        try:
            nodes, edges = parse_dataset()
            # Determine sampling percentage from environment (default 100% – i.e., full dataset)
            try:
                sample_percent = int(os.getenv("SAMPLE_PERCENT", "100"))
            except ValueError:
                sample_percent = 100
            if sample_percent not in (10, 50, 100):
                print(f"[{self.platform}] Invalid SAMPLE_PERCENT={sample_percent}, falling back to 100%.")
                sample_percent = 100
            if sample_percent < 100:
                print(f"[{self.platform}] Sampling dataset to {sample_percent}% for stable benchmarking.")
                step = max(1, int(100 / sample_percent))
                sampled_edges = edges[::step]
                # Gather referenced node IDs from sampled edges
                referenced_node_ids = {e["source"] for e in sampled_edges} | {e["target"] for e in sampled_edges}
                sampled_nodes = [n for n in nodes if n["id"] in referenced_node_ids]
                nodes = sampled_nodes
                edges = sampled_edges
                print(f"[{self.platform}] Sampled size: {len(nodes)} nodes, {len(edges)} edges.")
            node_ids = [n["id"] for n in nodes]
        except Exception as e:
            print(f"[{self.platform}] Failed to load/parse dataset: {e}")
            self.results["error"] = f"Dataset error: {e}"
            self.monitor.stop()
            self.save_results()
            self.loader.close()
            return

        # Initialize Ground Truth Correctness Engine
        correctness = CorrectnessEngine(nodes, edges)

        # Check if dataset is already loaded and count matches exactly
        skip_loading = False
        try:
            db_nodes = self.queries.count_nodes()
            db_edges = self.queries.count_edges()
            if db_nodes == len(nodes) and db_edges == len(edges):
                print(f"[{self.platform}] Data already loaded (Nodes: {db_nodes}, Edges: {db_edges}). Skipping clear and load steps.")
                skip_loading = True
        except Exception as e:
            pass

        if not skip_loading:
            # 2. Clear old data
            try:
                self.loader.clear_data()
            except Exception as e:
                print(f"[{self.platform}] Clear data failed: {e}. Continuing...")

            # 3. Create schema + indexes
            try:
                self.loader.create_schema()
            except Exception as e:
                print(f"[{self.platform}] Create schema failed: {e}. Continuing...")

            # 4. Load data (time it)
            print(f"[{self.platform}] Loading dataset...")
            t_start_load = time.perf_counter()
            
            # Load Nodes
            t_start_nodes = time.perf_counter()
            nodes_loaded = True
            try:
                self.loader.load_nodes(nodes)
            except Exception as e:
                print(f"[{self.platform}] Load nodes failed: {e}")
                nodes_loaded = False
            t_nodes_duration = time.perf_counter() - t_start_nodes
            
            # Load Edges
            t_start_edges = time.perf_counter()
            edges_loaded = True
            try:
                self.loader.load_edges(edges)
            except Exception as e:
                print(f"[{self.platform}] Load edges failed: {e}")
                edges_loaded = False
            t_edges_duration = time.perf_counter() - t_start_edges
            
            total_load_duration = time.perf_counter() - t_start_load
            node_throughput = len(nodes) / t_nodes_duration if nodes_loaded and t_nodes_duration > 0 else 0
            edge_throughput = len(edges) / t_edges_duration if edges_loaded and t_edges_duration > 0 else 0
        else:
            total_load_duration = 0.0
            t_nodes_duration = 0.0
            t_edges_duration = 0.0
            node_throughput = 0.0
            edge_throughput = 0.0

        print(f"[{self.platform}] Data Loading Completed. Total Time: {total_load_duration:.2f}s")
        self.results["metrics"]["data_loading"] = {
            "total_load_time_sec": round(total_load_duration, 3),
            "node_load_time_sec": round(t_nodes_duration, 3),
            "edge_load_time_sec": round(t_edges_duration, 3),
            "node_throughput_nodes_sec": round(node_throughput, 3),
            "edge_throughput_edges_sec": round(edge_throughput, 3)
        }

        # 5. Warm up (50 iterations of each query to allow JIT / cache warming)
        print(f"[{self.platform}] Performing warm-up...")
        warmup_nodes = [random.choice(node_ids) for _ in range(50)]
        for node in warmup_nodes:
            try: self.queries.hop_1(node)
            except Exception as e:
                if self._is_connection_error(e): raise e
            try: self.queries.hop_2(node)
            except Exception as e:
                if self._is_connection_error(e): raise e
            try: self.queries.hop_3(node)
            except Exception as e:
                if self._is_connection_error(e): raise e
            try: self.queries.point_lookup(node)
            except Exception as e:
                if self._is_connection_error(e): raise e
            try: self.queries.indexed_lookup(node)
            except Exception as e:
                if self._is_connection_error(e): raise e
            try: self.queries.shortest_path(node, random.choice(node_ids))
            except Exception as e:
                if self._is_connection_error(e): raise e
            try: self.queries.triangle_count(node)
            except Exception as e:
                if self._is_connection_error(e): raise e
            try: self.queries.common_neighbors(node, random.choice(node_ids))
            except Exception as e:
                if self._is_connection_error(e): raise e
        try: self.queries.count_nodes()
        except Exception as e:
            if self._is_connection_error(e): raise e
        try: self.queries.count_edges()
        except Exception as e:
            if self._is_connection_error(e): raise e
        print(f"[{self.platform}] Warm-up completed.")

        # 6. Run Correctness Engine Verification (before modifying data)
        print(f"[{self.platform}] Verifying correctness against ground truth...")
        try:
            v_hop1 = correctness.verify_hop_k(lambda n: self.queries.hop_1(n), k=1, sample_size=30)
            v_hop2 = correctness.verify_hop_k(lambda n: self.queries.hop_2(n), k=2, sample_size=30)
            v_edges = correctness.verify_edge_count(lambda: self.queries.count_edges())
            
            self.results["metrics"]["correctness"] = {
                "1_hop_verified": v_hop1["verified"],
                "2_hop_verified": v_hop2["verified"],
                "edge_count_expected": v_edges["expected"],
                "edge_count_actual": v_edges["actual"],
                "ratio": round(v_edges["ratio"], 3)
            }
            print(f"[{self.platform}] Correctness verification: 1-hop={v_hop1['verified']}, 2-hop={v_hop2['verified']}")
        except Exception as e:
            print(f"[{self.platform}] Correctness verification failed: {e}")
            self.results["metrics"]["correctness"] = {"error": str(e)}

        # 7. Run traversal benchmarks (1/2/3 hop, 100 iterations each)
        test_nodes = [random.choice(node_ids) for _ in range(100)]
        
        for hop in [1, 2, 3]:
            print(f"[{self.platform}] Running {hop}-hop traversals (100 iterations)...")
            stats = BenchmarkStatistics()
            raw_latencies = []
            failures = 0
            for node in test_nodes:
                start_t = time.perf_counter()
                try:
                    getattr(self.queries, f"hop_{hop}")(node)
                    latency = (time.perf_counter() - start_t) * 1000.0
                    raw_latencies.append(latency)
                    stats.record(latency)
                except Exception as e:
                    failures += 1
                    if self._is_connection_error(e):
                        print(f"[{self.platform}] Connection lost during traversal: {e}")
                        raise e
            
            # CUSUM Steady state cutoff filter
            steady_detector = SteadyStateDetector(window_size=10)
            cutoff_idx, is_steady = steady_detector.detect(raw_latencies)
            if is_steady and cutoff_idx > 0:
                # Re-record using steady-state samples
                stats = BenchmarkStatistics()
                for lat in raw_latencies[cutoff_idx:]:
                    stats.record(lat)
                print(f"[{self.platform}] Steady-state reached. Discarded first {cutoff_idx} warm-up samples.")

            report = stats.get_report()
            ci = BenchmarkStatistics.bootstrap_ci(raw_latencies[cutoff_idx:] if is_steady else raw_latencies)
            
            # Safely extract metrics, handling cases with no samples
            self.results["metrics"][f"{hop}_hop_traversal"] = {
                "p50_latency_ms": report.get("p50_ms", "N/A"),
                "p95_latency_ms": report.get("p95_ms", "N/A"),
                "mean_latency_ms": report.get("mean_ms", "N/A"),
                "stddev_ms": report.get("stddev_ms", "N/A"),
                "failures": failures,
                "confidence_interval_p95": ci.get("p95_ci", (0.0, 0.0))
            }

        # 8. Run lookup benchmarks (100 iterations)
        print(f"[{self.platform}] Running point and indexed lookups (100 iterations)...")
        pt_stats = BenchmarkStatistics()
        idx_stats_obj = BenchmarkStatistics()
        pt_failures = 0
        idx_failures = 0
        pt_raw = []
        idx_raw = []
        
        for node in test_nodes:
            # Point Lookup
            start_t = time.perf_counter()
            try:
                self.queries.point_lookup(node)
                latency = (time.perf_counter() - start_t) * 1000.0
                pt_raw.append(latency)
            except Exception as e:
                pt_failures += 1
                if self._is_connection_error(e):
                    print(f"[{self.platform}] Connection lost during point lookup: {e}")
                    raise e
            
            # Indexed Lookup
            start_t = time.perf_counter()
            try:
                self.queries.indexed_lookup(node)
                latency = (time.perf_counter() - start_t) * 1000.0
                idx_raw.append(latency)
            except Exception as e:
                idx_failures += 1
                if self._is_connection_error(e):
                    print(f"[{self.platform}] Connection lost during indexed lookup: {e}")
                    raise e

        # Calculate statistics
        for lat in pt_raw: pt_stats.record(lat)
        for lat in idx_raw: idx_stats_obj.record(lat)
        
        pt_report = pt_stats.get_report()
        idx_report = idx_stats_obj.get_report()
        
        self.results["metrics"]["point_lookup"] = {
            "p50_latency_ms": pt_report.get("p50_ms", "N/A"),
            "p95_latency_ms": pt_report.get("p95_ms", "N/A"),
            "failures": pt_failures
        }
        self.results["metrics"]["indexed_lookup"] = {
            "p50_latency_ms": idx_report.get("p50_ms", "N/A"),
            "p95_latency_ms": idx_report.get("p95_ms", "N/A"),
            "failures": idx_failures
        }

        # 9. Run aggregation benchmarks (100 iterations)
        print(f"[{self.platform}] Running aggregations (100 iterations)...")
        nc_stats = BenchmarkStatistics()
        ec_stats = BenchmarkStatistics()
        node_count_failures = 0
        edge_count_failures = 0
        
        for _ in range(100):
            # Node count
            start_t = time.perf_counter()
            try:
                self.queries.count_nodes()
                nc_stats.record((time.perf_counter() - start_t) * 1000.0)
            except Exception as e:
                node_count_failures += 1
                if self._is_connection_error(e):
                    print(f"[{self.platform}] Connection lost during node count: {e}")
                    raise e
            
            # Edge count
            start_t = time.perf_counter()
            try:
                self.queries.count_edges()
                ec_stats.record((time.perf_counter() - start_t) * 1000.0)
            except Exception as e:
                edge_count_failures += 1
                if self._is_connection_error(e):
                    print(f"[{self.platform}] Connection lost during edge count: {e}")
                    raise e

        nc_report = nc_stats.get_report()
        ec_report = ec_stats.get_report()
        
        self.results["metrics"]["count_nodes"] = {
            "p50_latency_ms": nc_report["p50_ms"],
            "p95_latency_ms": nc_report["p95_ms"],
            "failures": node_count_failures
        }
        self.results["metrics"]["count_edges"] = {
            "p50_latency_ms": ec_report["p50_ms"],
            "p95_latency_ms": ec_report["p95_ms"],
            "failures": edge_count_failures
        }

        # 10. Run concurrent mixed workload (10 clients, 60s)
        try:
            runner = ConcurrentRunner(self.queries, node_ids, num_threads=10, duration_seconds=60)
            concurrent_results = runner.run()
            self.results["metrics"]["mixed_workload"] = concurrent_results
        except Exception as e:
            print(f"[{self.platform}] Concurrent mixed workload failed: {e}")
            self.results["metrics"]["mixed_workload"] = {"error": str(e)}

        # Stop CPU/Memory System Monitor
        obs_report = self.monitor.stop()
        self.results["metrics"]["observability"] = obs_report
        
        # 11. Cost Analysis Extrapolation
        total_queries = 100 * 3 + 100 * 2 + 100 * 2 + (self.results["metrics"]["mixed_workload"].get("successful_operations", 0) if isinstance(self.results["metrics"]["mixed_workload"], dict) else 0)
        dur_hours = obs_report.get("duration_sec", 0.0) / 3600.0
        # SNAP dataset file is 3MB -> 0.003 GB
        cost_report = CostAnalyzer.analyze(self.platform, total_queries, dur_hours, data_size_gb=0.003)
        self.results["metrics"]["cost"] = cost_report

        # Save results
        self.save_results()
        
        # 12. Close Connection
        try:
            self.loader.close()
        except Exception as e:
            print(f"[{self.platform}] Loader close failed: {e}")

        # 13. Re-generate Plotly HTML Dashboard
        try:
            generate_dashboard()
        except Exception as e:
            print(f"[{self.platform}] Dashboard generation failed: {e}")

    def save_results(self):
        results_dir = "results"
        if not os.path.exists(results_dir):
            os.makedirs(results_dir)
            
        filepath = os.path.join(results_dir, f"{self.platform.lower()}_results.json")
        with open(filepath, "w") as f:
            json.dump(self.results, f, indent=4)
        print(f"[{self.platform}] Results saved to: {filepath}")
