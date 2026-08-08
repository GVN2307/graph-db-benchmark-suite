from queries.base_queries import BaseQuerySet

class NebulaQuerySet(BaseQuerySet):
    def __init__(self, loader):
        super().__init__(loader)

    def _get_scalar(self, query):
        res = self.loader.client.execute(query)
        if not res.is_succeeded:
            print(f"[{self.name}] Query failed: {query} Error: {res.status_message}")
            return 0
        if res.size > 0:
            row = res.one()
            val = row[0].cast_primitive()
            return int(val)
        return 0

    def _run_query(self, query):
        res = self.loader.client.execute(query)
        if not res.is_succeeded:
            print(f"[{self.name}] Query failed: {query} Error: {res.status_message}")
            return None
        return res

    def hop_1(self, start_node):
        # nGQL GO 1 STEP for 1-hop neighbors, distinct count
        query = f"GO 1 STEP FROM {start_node} OVER COLLABORATES YIELD $^.id AS neighbor_id | COUNT(DISTINCT $^.id)"
        return self._get_scalar(query)

    def hop_2(self, start_node):
        # nGQL GO 2 STEP for 2-hop neighbors, distinct count
        query = f"GO 2 STEP FROM {start_node} OVER COLLABORATES YIELD $^.id AS neighbor_id | COUNT(DISTINCT $^.id)"
        return self._get_scalar(query)

    def hop_3(self, start_node):
        # nGQL GO 3 STEP for 3-hop neighbors, distinct count
        query = f"GO 3 STEP FROM {start_node} OVER COLLABORATES YIELD $^.id AS neighbor_id | COUNT(DISTINCT $^.id)"
        return self._get_scalar(query)

    def point_lookup(self, node_id):
        query = f"MATCH (a:Author {{id: '{node_id}'}}) RETURN a"
        return self._run_query(query)

    def indexed_lookup(self, node_id):
        query = f"MATCH (a:Author {{id: '{node_id}'}}) RETURN a.id"
        return self._run_query(query)

    def count_nodes(self):
        query = "MATCH (a:Author) RETURN count(*)"
        return self._get_scalar(query)

    def count_edges(self):
        query = "MATCH ()-[e:COLLABORATES]->() RETURN count(*)"
        return self._get_scalar(query)

    def insert_edge(self, source_id, target_id):
        query = f"MATCH (s:Author {{id: '{source_id}'}}), (d:Author {{id: '{target_id}'}}) INSERT (s)-[:COLLABORATES]->(d)"
        self._run_query(query)

    def shortest_path(self, src_id, tgt_id):
        query = f"MATCH p = shortestPath((src:Author {{id: '{src_id}'}})-[:COLLABORATES*..10]-(tgt:Author {{id: '{tgt_id}'}})) RETURN length(p)"
        return self._get_scalar(query)

    def triangle_count(self, node_id):
        query = f"MATCH (a:Author {{id: '{node_id}'}})-[:COLLABORATES]-(b)-[:COLLABORATES]-(c)-[:COLLABORATES]-(a) WHERE id(b) < id(c) RETURN count(*)"
        return self._get_scalar(query)

    def common_neighbors(self, a_id, b_id):
        query = f"MATCH (a:Author {{id: '{a_id}'}})-[:COLLABORATES]-(n)-[:COLLABORATES]-(b:Author {{id: '{b_id}'}}) RETURN count(distinct n)"
        return self._get_scalar(query)

