from abc import ABC, abstractmethod

class BaseQuerySet(ABC):
    """Abstract base for executing benchmark queries on a platform."""
    
    def __init__(self, loader):
        self.loader = loader
        self.name = self.__class__.__name__

    @abstractmethod
    def hop_1(self, start_node):
        """1-hop traversal from a start node, returns count of reached nodes."""
        pass

    @abstractmethod
    def hop_2(self, start_node):
        """2-hop traversal from a start node, returns count of reached nodes."""
        pass

    @abstractmethod
    def hop_3(self, start_node):
        """3-hop traversal from a start node, returns count of reached nodes."""
        pass

    @abstractmethod
    def point_lookup(self, node_id):
        """Fetch all properties of a node by ID, returns the node."""
        pass

    @abstractmethod
    def indexed_lookup(self, node_id):
        """Fetch a specific property (e.g. id) of a node, using the index."""
        pass

    @abstractmethod
    def count_nodes(self):
        """Aggregate: count total nodes, returns integer count."""
        pass

    @abstractmethod
    def count_edges(self):
        """Aggregate: count total edges, returns integer count."""
        pass

    @abstractmethod
    def insert_edge(self, source_id, target_id):
        """Insert a single edge (for the concurrent read/write test)."""
        pass

    def shortest_path(self, src_id, tgt_id):
        """Unweighted shortest path length."""
        return 0

    def triangle_count(self, node_id):
        """Count triangles involving this node."""
        return 0

    def common_neighbors(self, a_id, b_id):
        """Intersection of neighbor sets."""
        return 0

    def page_rank_iteration(self, damping=0.85, iterations=5):
        """Run multiple iterations of PageRank."""
        return 0

    def streaming_ingestion(self, edges_per_second: int, duration: int):
        """Sustained write stream."""
        return 0

