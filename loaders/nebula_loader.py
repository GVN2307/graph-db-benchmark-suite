import os
import time
from nebula3.Config import Config
from nebula3.gclient.net import ConnectionPool


from loaders.base_loader import BaseGraphLoader

class NebulaLoader(BaseGraphLoader):
    def __init__(self):
        super().__init__()
        self.pool = None
        self.client = None

    def connect(self):
        host = os.getenv("NEBULA_HOST")
        port = int(os.getenv("NEBULA_PORT", 9669))
        user = os.getenv("NEBULA_USER", "root")
        password = os.getenv("NEBULA_PASSWORD", "nebula")
        
        config = Config()
        # Initialize ConnectionPool and then init with addresses
        self.pool = ConnectionPool()
        if not self.pool.init([ (host, port) ], config):
            raise RuntimeError(f"[{self.name}] Failed to initialize ConnectionPool")
        self.client = self.pool.get_session(user, password)
        print(f"[{self.name}] Connected to NebulaGraph at {host}:{port}")

    def create_schema(self):
        print(f"[{self.name}] Creating property graph nebulabenchmarking...")
        query = (
            "CREATE PROPERTY GRAPH nebulabenchmarking {"
            "  NODE Author (:Author { id STRING PRIMARY KEY }),"
            "  EDGE COLLABORATES (Author)-[:COLLABORATES]->(Author)"
            "}"
        )
        res = self.client.execute(query)
        if not res.is_succeeded:
            raise RuntimeError(f"Failed to create property graph: {res.status_message}")
            
        print(f"[{self.name}] Waiting 20 seconds for graph schema propagation...")
        time.sleep(20)
        
        # After creating the graph, set the active graph for the session
        res = self.client.execute("USE GRAPH nebulabenchmarking")
        if not res.is_succeeded:
            raise RuntimeError(f"Failed to switch to graph: {res.status_message}")
        print(f"[{self.name}] Switched to graph 'nebulabenchmarking' for subsequent operations.")

    def load_nodes(self, nodes):
        print(f"[{self.name}] Starting node loading of {len(nodes)} nodes...")
        batch_size = 1000
        for i in range(0, len(nodes), batch_size):
            batch = nodes[i:i+batch_size]
            patterns = [f"(:Author {{id: '{node['id']}'}})" for node in batch]
            query = f"INSERT {', '.join(patterns)}"
            res = self.client.execute(query)
            if not res.is_succeeded:
                raise RuntimeError(f"Failed to insert vertices: {res.status_message}")
        print(f"[{self.name}] Finished loading nodes.")

    def load_edges(self, edges):
        print(f"[{self.name}] Starting edge loading of {len(edges)} edges in parallel...")
        num_threads = 20
        chunk_size = (len(edges) + num_threads - 1) // num_threads
        chunks = [edges[i:i+chunk_size] for i in range(0, len(edges), chunk_size)]
        
        from concurrent.futures import ThreadPoolExecutor
        
        def worker(thread_idx, chunk):
            batch_size = 5
            for i in range(0, len(chunk), batch_size):
                batch = chunk[i:i+batch_size]
                match_clauses = []
                insert_clauses = []
                for idx, edge in enumerate(batch):
                    src_var = f"s{idx}"
                    dst_var = f"d{idx}"
                    match_clauses.append(f"({src_var}:Author {{id: '{edge['source']}'}})")
                    match_clauses.append(f"({dst_var}:Author {{id: '{edge['target']}'}})")
                    insert_clauses.append(f"({src_var})-[:COLLABORATES]->({dst_var})")
                
                query = f"MATCH {', '.join(match_clauses)} INSERT {', '.join(insert_clauses)}"
                try:
                    res = self.client.execute(query)
                    if not res.is_succeeded:
                        raise RuntimeError(res.status_message)
                except Exception as e:
                    # Fallback to single insertions
                    for edge in batch:
                        single_query = (
                            f"MATCH (s:Author {{id: '{edge['source']}'}}), "
                            f"(d:Author {{id: '{edge['target']}'}}) "
                            f"INSERT (s)-[:COLLABORATES]->(d)"
                        )
                        try:
                            self.client.execute(single_query)
                        except Exception as inner_e:
                            if "NR206" not in str(inner_e):
                                print(f"[{self.name} Thread-{thread_idx}] Warning: edge insert failed: {inner_e}")
            print(f"[{self.name} Thread-{thread_idx}] Finished chunk.")

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker, idx, chunk) for idx, chunk in enumerate(chunks)]
            for future in futures:
                future.result()
        print(f"[{self.name}] Finished loading edges.")

    def clear_data(self):
        print(f"[{self.name}] Dropping graph nebulabenchmarking to clear all data...")
        try:
            res = self.client.execute("DROP GRAPH nebulabenchmarking")
            if not res.is_succeeded:
                print(f"[{self.name}] Warning: Graph drop failed: {res.status_message}")
        except Exception as e:
            print(f"[{self.name}] Note: Graph drop skipped or failed: {e}")
            
        print(f"[{self.name}] Reconnecting client after drop...")
        self.connect()
        print(f"[{self.name}] Reconnected and ready for loading.")

    def close(self):
        if self.client:
            self.client.release()
            print(f"[{self.name}] Session released.")
        if hasattr(self, "pool") and self.pool:
            self.pool.close()
            print(f"[{self.name}] Connection pool closed.")
