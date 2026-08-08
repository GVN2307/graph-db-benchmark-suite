import networkx as nx
from typing import Dict, List, Callable
import random

class CorrectnessEngine:
    def __init__(self, nodes: List[dict], edges: List[dict]):
        self.ground_truth = nx.Graph()
        for n in nodes:
            self.ground_truth.add_node(str(n["id"]))
        for e in edges:
            self.ground_truth.add_edge(str(e["source"]), str(e["target"]))
    
    def verify_hop_k(self, platform_query_fn: Callable, k: int, sample_size: int = 100) -> Dict:
        """Verify k-hop counts match NetworkX BFS ground truth."""
        test_nodes = random.sample(list(self.ground_truth.nodes), min(sample_size, len(self.ground_truth.nodes)))
        mismatches = []
        for node in test_nodes:
            # Ground truth: BFS depth-limited
            gt_count = len(nx.single_source_shortest_path_length(
                self.ground_truth, node, cutoff=k
            )) - 1  # exclude self
            
            # Platform result
            platform_count = platform_query_fn(node)
            
            if gt_count != platform_count:
                mismatches.append({
                    "node": node, "expected": gt_count, 
                    "actual": platform_count, "hop": k
                })
        
        return {
            "verified": len(mismatches) == 0,
            "mismatch_count": len(mismatches),
            "mismatches": mismatches[:10]  # cap for reporting
        }
    
    def verify_edge_count(self, platform_count_fn: Callable) -> Dict:
        gt_edges = self.ground_truth.number_of_edges()
        platform_count = platform_count_fn()
        return {
            "expected": gt_edges,
            "actual": platform_count,
            "ratio": platform_count / gt_edges if gt_edges else 0
        }
