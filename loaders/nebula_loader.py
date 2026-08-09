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
        use_ssl = os.getenv("NEBULA_USE_SSL", "false").lower() in ("true", "1")
        if not use_ssl and (host and (".nebula-graph.io" in host or ".nebula-db.com" in host)):
            use_ssl = True
            
        if use_ssl:
            import ssl
            from nebula3.Config import SSL_config
            ssl_config = SSL_config()
            ssl_config.cert_reqs = ssl.CERT_NONE
            ssl_config.verify_name = host
            config.ssl_config = ssl_config
            print(f"[{self.name}] SSL connection with SNI enabled for {host}")

        self.pool = ConnectionPool()
        if not self.pool.init([ (host, port) ], config):
            raise RuntimeError(f"[{self.name}] Failed to initialize ConnectionPool")
        self.client = self.pool.get_session(user, password)
        print(f"[{self.name}] Connected to NebulaGraph at {host}:{port}")
        
        try:
            res = self.client.execute("USE nebulabenchmarking")
            if res.is_succeeded:
                print(f"[{self.name}] Switched to space 'nebulabenchmarking'")
        except Exception:
            pass

    def create_schema(self):
        print(f"[{self.name}] Creating space nebulabenchmarking...")
        res = self.client.execute("CREATE SPACE IF NOT EXISTS nebulabenchmarking(vid_type=FIXED_STRING(32))")
        if not res.is_succeeded:
            raise RuntimeError(f"Failed to create space: {res.status_message}")
            
        print(f"[{self.name}] Waiting 10 seconds for space creation propagation...")
        time.sleep(10)
        
        res = self.client.execute("USE nebulabenchmarking")
        if not res.is_succeeded:
            raise RuntimeError(f"Failed to switch space: {res.status_message}")
            
        print(f"[{self.name}] Creating tag Author and edge COLLABORATES...")
        res = self.client.execute("CREATE TAG IF NOT EXISTS Author(id string)")
        if not res.is_succeeded:
            raise RuntimeError(f"Failed to create tag Author: {res.status_message}")
            
        res = self.client.execute("CREATE EDGE IF NOT EXISTS COLLABORATES()")
        if not res.is_succeeded:
            raise RuntimeError(f"Failed to create edge COLLABORATES: {res.status_message}")
            
        # Create tag and edge indexes for MATCH and traversals
        print(f"[{self.name}] Creating indexes...")
        self.client.execute("CREATE TAG INDEX IF NOT EXISTS author_index ON Author()")
        self.client.execute("CREATE TAG INDEX IF NOT EXISTS author_id_index ON Author(id(32))")
        self.client.execute("CREATE EDGE INDEX IF NOT EXISTS collaborates_index ON COLLABORATES()")
        
        print(f"[{self.name}] Waiting 20 seconds for schema and index propagation...")
        time.sleep(20)

    def load_nodes(self, nodes):
        print(f"[{self.name}] Starting node loading of {len(nodes)} nodes...")
        batch_size = 1000
        for i in range(0, len(nodes), batch_size):
            batch = nodes[i:i+batch_size]
            values = []
            for node in batch:
                vid = str(node['id'])
                values.append(f"'{vid}':('{vid}')")
            query = f"INSERT VERTEX Author(id) VALUES {', '.join(values)}"
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
            batch_size = 200
            for i in range(0, len(chunk), batch_size):
                batch = chunk[i:i+batch_size]
                values = []
                for edge in batch:
                    src = str(edge['source'])
                    dst = str(edge['target'])
                    values.append(f"'{src}' -> '{dst}':()")
                query = f"INSERT EDGE COLLABORATES() VALUES {', '.join(values)}"
                try:
                    res = self.client.execute(query)
                    if not res.is_succeeded:
                        raise RuntimeError(res.status_message)
                except Exception as e:
                    # Fallback to single insertions
                    for edge in batch:
                        src = str(edge['source'])
                        dst = str(edge['target'])
                        single_query = f"INSERT EDGE COLLABORATES() VALUES '{src}' -> '{dst}':()"
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
        
        # Rebuild indexes to ensure they are fully populated and active
        print(f"[{self.name}] Rebuilding indexes...")
        self.client.execute("REBUILD TAG INDEX author_index")
        self.client.execute("REBUILD TAG INDEX author_id_index")
        self.client.execute("REBUILD EDGE INDEX collaborates_index")
        # Sleep to allow rebuilding propagation
        time.sleep(5)
        print(f"[{self.name}] Finished loading edges.")

    def clear_data(self):
        print(f"[{self.name}] Dropping space nebulabenchmarking to clear all data...")
        try:
            res = self.client.execute("DROP SPACE nebulabenchmarking")
            if not res.is_succeeded:
                print(f"[{self.name}] Warning: Space drop failed: {res.status_message}")
        except Exception as e:
            print(f"[{self.name}] Note: Space drop skipped or failed: {e}")
            
        print(f"[{self.name}] Waiting 10 seconds for space drop propagation...")
        time.sleep(10)
            
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
