from queries.base_queries import BaseQuerySet

class CypherQuerySet(BaseQuerySet):
    def __init__(self, loader):
        super().__init__(loader)
        # Determine database provider name from loader class name
        if "Falkor" in loader.__class__.__name__:
            self.provider = "FalkorDB"
        elif "Cogno" in loader.__class__.__name__:
            self.provider = "CognoDB"
        else:
            self.provider = "Neo4j"

    def _run_scalar(self, query, params=None):
        if self.provider == "FalkorDB":
            with self.loader.lock:
                res = self.loader.graph.query(query, params)
            if res.result_set:
                return res.result_set[0][0]
            return 0
        else:
            # Use list conversion to safely handle cases where the query returns multiple records
            with self.loader.driver.session() as session:
                res = session.run(query, params)
                records = list(res)
                if records:
                    return records[0][0]
                return 0

    def _run_query(self, query, params=None):
        if self.provider == "FalkorDB":
            with self.loader.lock:
                return self.loader.graph.query(query, params)
        else:
            with self.loader.driver.session() as session:
                return list(session.run(query, params))

    def hop_1(self, start_node):
        query = """
        MATCH (n:Author {id: $start})
        OPTIONAL MATCH (n)-[:COLLABORATES]-(m)
        RETURN count(distinct m)
        """
        return self._run_scalar(query, {"start": int(start_node)})

    def hop_2(self, start_node):
        query = """
        MATCH (n:Author {id: $start})
        OPTIONAL MATCH (n)-[:COLLABORATES]-(m1)
        WITH n, [x in collect(distinct m1) WHERE x IS NOT NULL] as lvl1
        UNWIND (lvl1 + [null]) as a1
        OPTIONAL MATCH (a1)-[:COLLABORATES]-(m2)
        WHERE m2 IS NOT NULL AND m2 <> n AND not m2 in lvl1
        WITH lvl1, [y in collect(distinct m2) WHERE y IS NOT NULL] as lvl2
        RETURN size(lvl1) + size(lvl2)
        """
        return self._run_scalar(query, {"start": int(start_node)})

    def hop_3(self, start_node):
        query = """
        MATCH (n:Author {id: $start})
        OPTIONAL MATCH (n)-[:COLLABORATES]-(m1)
        WITH n, [x in collect(distinct m1) WHERE x IS NOT NULL] as lvl1
        UNWIND (lvl1 + [null]) as a1
        OPTIONAL MATCH (a1)-[:COLLABORATES]-(m2)
        WHERE m2 IS NOT NULL AND m2 <> n AND not m2 in lvl1
        WITH n, lvl1, [y in collect(distinct m2) WHERE y IS NOT NULL] as lvl2
        UNWIND (lvl2 + [null]) as a2
        OPTIONAL MATCH (a2)-[:COLLABORATES]-(m3)
        WHERE m3 IS NOT NULL AND m3 <> n AND not m3 in lvl1 AND not m3 in lvl2
        WITH lvl1, lvl2, [z in collect(distinct m3) WHERE z IS NOT NULL] as lvl3
        RETURN size(lvl1) + size(lvl2) + size(lvl3)
        """
        return self._run_scalar(query, {"start": int(start_node)})

    def point_lookup(self, node_id):
        # Point lookup: fetch a node by its original ID (Author node properties)
        query = "MATCH (n:Author) WHERE n.id = $node_id RETURN n"
        return self._run_query(query, {"node_id": int(node_id)})

    def indexed_lookup(self, node_id):
        # Indexed lookup: fetch nodes where a property matches (Author id property)
        query = "MATCH (n:Author) WHERE n.id = $node_id RETURN n.id"
        return self._run_query(query, {"node_id": int(node_id)})

    def count_nodes(self):
        query = "MATCH (n:Author) RETURN count(n)"
        return self._run_scalar(query)

    def count_edges(self):
        # In undirected dataset parsed as directed, we return count / 2 or full count depending on definition.
        # Let's return total collaborates relationships.
        query = "MATCH ()-[r:COLLABORATES]->() RETURN count(r)"
        return self._run_scalar(query)

    def insert_edge(self, source_id, target_id):
        # Used for the write parts of concurrent read/write test
        query = """
        MATCH (src:Author {id: $source})
        MATCH (tgt:Author {id: $target})
        CREATE (src)-[:COLLABORATES]->(tgt)
        """
        self._run_query(query, {"source": int(source_id), "target": int(target_id)})

    def shortest_path(self, src_id, tgt_id):
        if self.provider == "FalkorDB":
            query = "MATCH (src:Author {id: $src}), (tgt:Author {id: $tgt}) RETURN length(shortestPath((src)-[:COLLABORATES*..4]->(tgt)))"
        else:
            query = "MATCH p = shortestPath((src:Author {id: $src})-[:COLLABORATES*..4]-(tgt:Author {id: $tgt})) RETURN length(p)"
        return self._run_scalar(query, {"src": int(src_id), "tgt": int(tgt_id)})

    def triangle_count(self, node_id):
        query = "MATCH (a:Author {id: $id})-[:COLLABORATES]-(b)-[:COLLABORATES]-(c)-[:COLLABORATES]-(a) WHERE b.id < c.id RETURN count(*)"
        return self._run_scalar(query, {"id": int(node_id)})

    def common_neighbors(self, a_id, b_id):
        query = "MATCH (a:Author {id: $a})-[:COLLABORATES]-(n)-[:COLLABORATES]-(b:Author {id: $b}) RETURN count(distinct n)"
        return self._run_scalar(query, {"a": int(a_id), "b": int(b_id)})


