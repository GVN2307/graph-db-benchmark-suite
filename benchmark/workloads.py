from abc import ABC, abstractmethod
from typing import List, Tuple
import random

class Workload(ABC):
    @property
    @abstractmethod
    def name(self) -> str: pass
    
    @property
    @abstractmethod
    def read_ratio(self) -> float: pass
    
    @abstractmethod
    def next_operation(self) -> Tuple[str, dict]: pass

class SocialNetworkWorkload(Workload):
    """70% reads, 20% writes, 10% analytics — realistic social graph"""
    name = "social_network"
    read_ratio = 0.70
    
    def __init__(self, nodes: List[str]):
        self.nodes = nodes
    
    def next_operation(self) -> Tuple[str, dict]:
        r = random.random()
        if r < 0.35:
            return ("hop_2", {"node": random.choice(self.nodes)})
        elif r < 0.55:
            return ("point_lookup", {"node": random.choice(self.nodes)})
        elif r < 0.65:
            return ("shortest_path", {"src": random.choice(self.nodes), "tgt": random.choice(self.nodes)})
        elif r < 0.75:
            return ("common_neighbors", {"a": random.choice(self.nodes), "b": random.choice(self.nodes)})
        elif r < 0.85:
            return ("insert_edge", {"src": random.choice(self.nodes), "tgt": random.choice(self.nodes)})
        elif r < 0.90:
            return ("delete_edge", {"src": random.choice(self.nodes), "tgt": random.choice(self.nodes)})
        else:
            return ("triangle_count_sample", {"node": random.choice(self.nodes)})

class FraudDetectionWorkload(Workload):
    """50% path existence, 30% pattern match, 20% insert — financial fraud"""
    name = "fraud_detection"
    read_ratio = 0.80
    
    def __init__(self, nodes: List[str]):
        self.nodes = nodes
    
    def next_operation(self) -> Tuple[str, dict]:
        r = random.random()
        if r < 0.30:
            return ("path_exists", {"src": random.choice(self.nodes), "tgt": random.choice(self.nodes), "max_depth": 4})
        elif r < 0.50:
            return ("pattern_match", {"template": "triangle_with_high_degree"})
        elif r < 0.65:
            return ("centrality_sample", {"node": random.choice(self.nodes)})
        elif r < 0.80:
            return ("insert_edge", {"src": random.choice(self.nodes), "tgt": random.choice(self.nodes)})
        else:
            return ("batch_insert", {"count": 10})
