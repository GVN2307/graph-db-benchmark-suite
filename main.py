import os
import sys
import csv
import json
import socket
from dotenv import load_dotenv

# Set default socket timeout globally to prevent infinite hangs on defunct connections,
# but make it large enough to handle queue delays under concurrent stress testing on free tiers.
socket.setdefaulttimeout(180.0)

from loaders.cognodb_loader import CognoDBLoader
from loaders.neo4j_loader import Neo4jLoader
from loaders.falkordb_loader import FalkorDBLoader
from loaders.typedb_loader import TypeDBLoader
from loaders.networkx_loader import NetworkXLoader

from queries.cypher_queries import CypherQuerySet
from queries.typedb_queries import TypeDBQuerySet
from queries.networkx_queries import NetworkXQuerySet

from benchmark.harness import BenchmarkHarness

load_dotenv()

PLATFORMS = [
    ("CognoDB", CognoDBLoader, CypherQuerySet),
    ("FalkorDB", FalkorDBLoader, CypherQuerySet),
    ("NetworkX", NetworkXLoader, NetworkXQuerySet),
    ("Neo4jAura", Neo4jLoader, CypherQuerySet),
    ("TypeDB", TypeDBLoader, TypeDBQuerySet),
]

def generate_summary():
    sample_percent = os.getenv("SAMPLE_PERCENT", "100")
    results_dir = os.path.join("results", sample_percent)
    summary_path = os.path.join(results_dir, "summary.csv")
    
    if not os.path.exists(results_dir):
        print(f"No results directory found at {results_dir}.")
        return
        
    data = []
    for filename in os.listdir(results_dir):
        if filename.endswith("_results.json"):
            filepath = os.path.join(results_dir, filename)
            with open(filepath, "r") as f:
                try:
                    res = json.load(f)
                    data.append(res)
                except Exception as e:
                    print(f"Error loading {filename}: {e}")
                    
    if not data:
        print("No results found to summarize.")
        return

    headers = [
        "Platform", "Node Load Time (s)", "Edge Load Time (s)",
        "1-Hop p50 (ms)", "1-Hop p95 (ms)", "2-Hop p50 (ms)", "2-Hop p95 (ms)", "3-Hop p50 (ms)", "3-Hop p95 (ms)",
        "Point Lookup p50 (ms)", "Point Lookup p95 (ms)", "Indexed Lookup p50 (ms)", "Indexed Lookup p95 (ms)",
        "Count Nodes p50 (ms)", "Count Nodes p95 (ms)", "Count Edges p50 (ms)", "Count Edges p95 (ms)",
        "Concurrent QPS", "Concurrent p50 (ms)", "Concurrent p95 (ms)"
    ]
    
    rows = []
    for platform_res in data:
        name = platform_res.get("platform", "Unknown")
        metrics = platform_res.get("metrics", {})
        
        load_nodes = metrics.get("data_loading", {}).get("node_load_time_sec", "N/A")
        load_edges = metrics.get("data_loading", {}).get("edge_load_time_sec", "N/A")
        
        hop_1_p50 = metrics.get("1_hop_traversal", {}).get("p50_latency_ms", "N/A")
        hop_1_p95 = metrics.get("1_hop_traversal", {}).get("p95_latency_ms", "N/A")
        hop_2_p50 = metrics.get("2_hop_traversal", {}).get("p50_latency_ms", "N/A")
        hop_2_p95 = metrics.get("2_hop_traversal", {}).get("p95_latency_ms", "N/A")
        hop_3_p50 = metrics.get("3_hop_traversal", {}).get("p50_latency_ms", "N/A")
        hop_3_p95 = metrics.get("3_hop_traversal", {}).get("p95_latency_ms", "N/A")
        
        point_p50 = metrics.get("point_lookup", {}).get("p50_latency_ms", "N/A")
        point_p95 = metrics.get("point_lookup", {}).get("p95_latency_ms", "N/A")
        indexed_p50 = metrics.get("indexed_lookup", {}).get("p50_latency_ms", "N/A")
        indexed_p95 = metrics.get("indexed_lookup", {}).get("p95_latency_ms", "N/A")
        
        c_nodes_p50 = metrics.get("count_nodes", {}).get("p50_latency_ms", "N/A")
        c_nodes_p95 = metrics.get("count_nodes", {}).get("p95_latency_ms", "N/A")
        c_edges_p50 = metrics.get("count_edges", {}).get("p50_latency_ms", "N/A")
        c_edges_p95 = metrics.get("count_edges", {}).get("p95_latency_ms", "N/A")
        
        concurrent_qps = metrics.get("mixed_workload", {}).get("queries_per_second", "N/A")
        concurrent_p50 = metrics.get("mixed_workload", {}).get("p50_latency_ms", "N/A")
        concurrent_p95 = metrics.get("mixed_workload", {}).get("p95_latency_ms", "N/A")
        
        rows.append([
            name, load_nodes, load_edges,
            hop_1_p50, hop_1_p95, hop_2_p50, hop_2_p95, hop_3_p50, hop_3_p95,
            point_p50, point_p95, indexed_p50, indexed_p95,
            c_nodes_p50, c_nodes_p95, c_edges_p50, c_edges_p95,
            concurrent_qps, concurrent_p50, concurrent_p95
        ])
        
    with open(summary_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"Generated comparison matrix at: {summary_path}")

def main():
    sample_percent = os.getenv("SAMPLE_PERCENT", "100")
    print("==================================================")
    print("Graph Database Cloud Benchmark Suite starting...")
    print(f"Dataset Sampling Configuration: {sample_percent}%")
    print("==================================================")
    
    # If running at 10% load, copy existing results for other databases to results/10/
    if sample_percent == "10":
        import shutil
        dest_dir = os.path.join("results", "10")
        os.makedirs(dest_dir, exist_ok=True)
        for f_name in ["cognodb_results.json", "falkordb_results.json", "neo4jaura_results.json", "typedb_results.json"]:
            src = os.path.join("results", f_name)
            dst = os.path.join(dest_dir, f_name)
            if os.path.exists(src) and not os.path.exists(dst):
                try:
                    shutil.copy2(src, dst)
                    print(f"[Main] Copied existing 10% results for {f_name} to results/10/")
                except Exception as copy_err:
                    print(f"[Main] Failed to copy {f_name} to results/10/: {copy_err}")

    platform_filter = os.getenv("PLATFORM_FILTER")
    for name, LoaderClass, QueryClass in PLATFORMS:
        if platform_filter and name != platform_filter:
            continue

        if sample_percent == "10" and name != "NetworkX":
            print(f"[{name}] Skipping benchmark for 10% load: results already exist/skipped.")
            continue

        if name == "TypeDB" and sys.version_info >= (3, 14):
            print(f"[{name}] Skipping benchmark: TypeDB driver is incompatible with Python 3.14+ (Rust FFI panic).")
            results_dir = os.path.join("results", sample_percent)
            if not os.path.exists(results_dir):
                os.makedirs(results_dir)
            filepath = os.path.join(results_dir, f"typedb_results.json")
            dummy_res = {
                "platform": "TypeDB",
                "metrics": {
                    "error": "Skipped: typedb-driver incompatible with Python 3.14+"
                }
            }
            with open(filepath, "w") as f:
                json.dump(dummy_res, f, indent=4)
            continue

        loader = None
        try:
            loader = LoaderClass()
            queries = QueryClass(loader)
            harness = BenchmarkHarness(loader, queries, name)
            harness.run_all()
        except Exception as e:
            print(f"[{name}] Fatal error running benchmark for {name}: {e}")
        finally:
            if loader:
                try:
                    loader.close()
                except Exception as close_err:
                    print(f"[{name}] Warning: Failed to close loader: {close_err}")
    
    print("\n==================================================")
    print("Generating aggregate results...")
    print("==================================================")
    generate_summary()
    print("All benchmarks finished.")
    
    # Flush stdio and force exit to bypass any hanging background socket or driver threads
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
