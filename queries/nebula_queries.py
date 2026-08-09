from queries.base_queries import BaseQuerySet

class NebulaQuerySet(BaseQuerySet):
    def __init__(self, loader):
        super().__init__(loader)

    def _get_scalar(self, query):
        res = self.loader.client.execute(query)
        if not res.is_succeeded:
            print(f"[{self.name}] Query failed: {query} Error: {res.status_message}")
            return 0
        if res.row_size() > 0:
            try:
                return res.row_values(0)[0].as_int()
            except Exception:
                try:
                    return int(res.row_values(0)[0].cast_primitive())
                except Exception:
                    return 0
        return 0

    def _run_query(self, query):
        res = self.loader.client.execute(query)
        if not res.is_succeeded:
            print(f"[{self.name}] Query failed: {query} Error: {res.status_message}")
            return None
        return res

    def hop_1(self, start_node):
        query = f"GO 1 STEP FROM '{start_node}' OVER COLLABORATES BIDIRECT YIELD DISTINCT id($$) AS id | YIELD COUNT($-.id)"
        return self._get_scalar(query)

    def hop_2(self, start_node):
        query = f"GO 1 TO 2 STEPS FROM '{start_node}' OVER COLLABORATES BIDIRECT YIELD id($$) AS id | YIELD DISTINCT $-.id AS id WHERE $-.id != '{start_node}' | YIELD COUNT($-.id)"
        return self._get_scalar(query)

    def hop_3(self, start_node):
        query = f"GO 1 TO 3 STEPS FROM '{start_node}' OVER COLLABORATES BIDIRECT YIELD id($$) AS id | YIELD DISTINCT $-.id AS id WHERE $-.id != '{start_node}' | YIELD COUNT($-.id)"
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
        query = f"INSERT EDGE COLLABORATES() VALUES '{source_id}' -> '{target_id}':()"
        self._run_query(query)

    def shortest_path(self, src_id, tgt_id):
        query = (
            f"FIND SHORTEST PATH FROM '{src_id}' TO '{tgt_id}' "
            f"OVER COLLABORATES BIDIRECT UPTO 10 STEPS YIELD path AS p "
            f"| YIELD length($-.p)"
        )
        return self._get_scalar(query)

    def triangle_count(self, node_id):
        query = f"MATCH (a:Author {{id: '{node_id}'}})-[:COLLABORATES]-(b)-[:COLLABORATES]-(c)-[:COLLABORATES]-(a) WHERE id(b) < id(c) RETURN count(*)"
        return self._get_scalar(query)

    def common_neighbors(self, a_id, b_id):
        query = f"MATCH (a:Author {{id: '{a_id}'}})-[:COLLABORATES]-(n)-[:COLLABORATES]-(b:Author {{id: '{b_id}'}}) RETURN count(distinct n)"
        return self._get_scalar(query)

