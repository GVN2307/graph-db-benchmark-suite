import networkx as nx
from queries.base_queries import BaseQuerySet

class NetworkXQuerySet(BaseQuerySet):
    def __init__(self, loader):
        super().__init__(loader)

    def hop_1(self, start_node):
        G = self.loader.G
        if start_node not in G:
            return 0
        return len(list(G.neighbors(start_node)))

    def hop_2(self, start_node):
        G = self.loader.G
        if start_node not in G:
            return 0
        
        visited = {start_node}
        neighbors_1 = set(G.neighbors(start_node))
        neighbors_2 = set()
        for n in neighbors_1:
            neighbors_2.update(G.neighbors(n))
        all_reached = (neighbors_1 | neighbors_2) - visited
        return len(all_reached)

    def hop_3(self, start_node):
        G = self.loader.G
        if start_node not in G:
            return 0
        
        visited = {start_node}
        neighbors_1 = set(G.neighbors(start_node))
        neighbors_2 = set()
        for n in neighbors_1:
            neighbors_2.update(G.neighbors(n))
        neighbors_3 = set()
        for n in neighbors_2:
            neighbors_3.update(G.neighbors(n))
        all_reached = (neighbors_1 | neighbors_2 | neighbors_3) - visited
        return len(all_reached)

    def point_lookup(self, node_id):
        G = self.loader.G
        if node_id not in G:
            return None
        return G.nodes[node_id]

    def indexed_lookup(self, node_id):
        G = self.loader.G
        if node_id not in G:
            return None
        return G.nodes[node_id].get('id')

    def count_nodes(self):
        return self.loader.G.number_of_nodes()

    def count_edges(self):
        return self.loader.G.number_of_edges()

    def insert_edge(self, source_id, target_id):
        G = self.loader.G
        # Add nodes implicitly if not already present
        if source_id not in G:
            G.add_node(source_id, label='Author', id=source_id)
        if target_id not in G:
            G.add_node(target_id, label='Author', id=target_id)
        G.add_edge(source_id, target_id, type='COLLABORATES')

    def shortest_path(self, src_id, tgt_id):
        G = self.loader.G
        if src_id not in G or tgt_id not in G:
            return 0
        try:
            return nx.shortest_path_length(G, src_id, tgt_id)
        except nx.NetworkXNoPath:
            return 0

    def triangle_count(self, node_id):
        G = self.loader.G
        if node_id not in G:
            return 0
        return nx.triangles(G, node_id)

    def common_neighbors(self, a_id, b_id):
        G = self.loader.G
        if a_id not in G or b_id not in G:
            return 0
        return len(list(nx.common_neighbors(G, a_id, b_id)))
