from typedb.driver import TransactionType
from queries.base_queries import BaseQuerySet

class TypeDBQuerySet(BaseQuerySet):
    def __init__(self, loader):
        super().__init__(loader)

    def _run_aggregate(self, query):
        with self.loader.driver.transaction(self.loader.database_name, TransactionType.READ) as tx:
            promise = tx.query(query)
            res = list(promise.resolve())
            if res:
                concept = res[0].get("c")
                if concept:
                    return int(concept.get())
            return 0

    def _run_fetch(self, query):
        with self.loader.driver.transaction(self.loader.database_name, TransactionType.READ) as tx:
            promise = tx.query(query)
            res = promise.resolve()
            return list(res)

    def hop_1(self, start_node):
        start_id = str(start_node)
        query = f'match $p isa person, has uid "{start_id}"; (collaborator: $p, collaborator: $n) isa collaborates; $n has uid $uid;'
        res = self._run_fetch(query)
        neighbors = {row.get("uid").get_value() for row in res}
        return len(neighbors - {start_id})

    def hop_2(self, start_node):
        start_id = str(start_node)
        query = f'match $p isa person, has uid "{start_id}"; {{ (collaborator: $p, collaborator: $n) isa collaborates; }} or {{ (collaborator: $p, collaborator: $n1) isa collaborates; (collaborator: $n1, collaborator: $n) isa collaborates; }}; $n has uid $uid;'
        res = self._run_fetch(query)
        neighbors = {row.get("uid").get_value() for row in res}
        return len(neighbors - {start_id})

    def hop_3(self, start_node):
        start_id = str(start_node)
        query = f'match $p isa person, has uid "{start_id}"; {{ (collaborator: $p, collaborator: $n) isa collaborates; }} or {{ (collaborator: $p, collaborator: $n1) isa collaborates; (collaborator: $n1, collaborator: $n) isa collaborates; }} or {{ (collaborator: $p, collaborator: $n1) isa collaborates; (collaborator: $n1, collaborator: $n2) isa collaborates; (collaborator: $n2, collaborator: $n) isa collaborates; }}; $n has uid $uid;'
        res = self._run_fetch(query)
        neighbors = {row.get("uid").get_value() for row in res}
        return len(neighbors - {start_id})

    def point_lookup(self, node_id):
        node_id_str = str(node_id)
        query = f'match $p isa person, has uid "{node_id_str}";'
        return self._run_fetch(query)

    def indexed_lookup(self, node_id):
        node_id_str = str(node_id)
        query = f'match $p isa person, has uid "{node_id_str}";'
        return self._run_fetch(query)

    def count_nodes(self):
        query = "match $p isa person; reduce $c = count;"
        return self._run_aggregate(query)

    def count_edges(self):
        query = "match $r isa collaborates; reduce $c = count;"
        return self._run_aggregate(query)

    def insert_edge(self, source_id, target_id):
        src_id = str(source_id)
        tgt_id = str(target_id)
        query = f'match $p1 isa person, has uid "{src_id}"; $p2 isa person, has uid "{tgt_id}"; insert (collaborator: $p1, collaborator: $p2) isa collaborates;'
        with self.loader.driver.transaction(self.loader.database_name, TransactionType.WRITE) as tx:
            tx.query(query).resolve()
            tx.commit()

    def shortest_path(self, src_id, tgt_id):
        s_id = str(src_id)
        t_id = str(tgt_id)
        if s_id == t_id:
            return 0
        with self.loader.driver.transaction(self.loader.database_name, TransactionType.READ) as tx:
            # 1-hop
            q1 = f'match $p1 isa person, has uid "{s_id}"; $p2 isa person, has uid "{t_id}"; (collaborator: $p1, collaborator: $p2) isa collaborates;'
            if list(tx.query(q1).resolve()):
                return 1
            # 2-hop
            q2 = f'match $p1 isa person, has uid "{s_id}"; $p2 isa person, has uid "{t_id}"; (collaborator: $p1, collaborator: $n) isa collaborates; (collaborator: $n, collaborator: $p2) isa collaborates;'
            if list(tx.query(q2).resolve()):
                return 2
            # 3-hop
            q3 = f'match $p1 isa person, has uid "{s_id}"; $p2 isa person, has uid "{t_id}"; (collaborator: $p1, collaborator: $n1) isa collaborates; (collaborator: $n1, collaborator: $n2) isa collaborates; (collaborator: $n2, collaborator: $p2) isa collaborates;'
            if list(tx.query(q3).resolve()):
                return 3
        return 0

    def triangle_count(self, node_id):
        n_id = str(node_id)
        query = f'match $p isa person, has uid "{n_id}"; (collaborator: $p, collaborator: $b) isa collaborates; (collaborator: $b, collaborator: $c) isa collaborates; (collaborator: $c, collaborator: $p) isa collaborates; reduce $c = count;'
        return self._run_aggregate(query) // 2

    def common_neighbors(self, a_id, b_id):
        a = str(a_id)
        b = str(b_id)
        query = f'match $p1 isa person, has uid "{a}"; $p2 isa person, has uid "{b}"; (collaborator: $p1, collaborator: $n) isa collaborates; (collaborator: $n, collaborator: $p2) isa collaborates; reduce $c = count;'
        return self._run_aggregate(query)

