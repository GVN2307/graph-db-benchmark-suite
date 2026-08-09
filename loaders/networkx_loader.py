import networkx as nx
from loaders.base_loader import BaseGraphLoader

class NetworkXLoader(BaseGraphLoader):
    def __init__(self):
        super().__init__()
        self.G = None

    def connect(self):
        self.G = nx.Graph()
        print(f"[{self.name}] In-memory NetworkX Graph initialized.")

    def create_schema(self):
        print(f"[{self.name}] Schema creation skipped (schema-free).")

    def load_nodes(self, nodes):
        print(f"[{self.name}] Loading {len(nodes)} nodes...")
        for node in nodes:
            nid = node['id']
            self.G.add_node(nid, label=node.get('label', 'Author'), id=nid)
        print(f"[{self.name}] Finished loading nodes.")

    def load_edges(self, edges):
        print(f"[{self.name}] Loading {len(edges)} edges...")
        for edge in edges:
            self.G.add_edge(edge['source'], edge['target'], type=edge.get('type', 'COLLABORATES'))
        print(f"[{self.name}] Finished loading edges.")

    def clear_data(self):
        if self.G is not None:
            self.G.clear()
        print(f"[{self.name}] Database cleared.")

    def close(self):
        print(f"[{self.name}] In-memory connection closed.")
