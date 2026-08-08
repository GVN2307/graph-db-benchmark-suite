import os
import time
import threading
from falkordb import FalkorDB
from loaders.base_loader import BaseGraphLoader

class FalkorDBLoader(BaseGraphLoader):
    def __init__(self):
        super().__init__()
        self.db = None
        self.graph = None
        self.lock = threading.Lock()

    def connect(self):
        host = os.getenv("FALKORDB_HOST")
        port = os.getenv("FALKORDB_PORT")
        password = os.getenv("FALKORDB_PASSWORD")
        if not host or not port:
            raise ValueError("FalkorDB host/port are not set in .env")
        
        port = int(port)
        
        retries = 3
        for attempt in range(retries):
            try:
                print(f"[{self.name}] Connecting to FalkorDB at {host}:{port} (Attempt {attempt+1}/{retries})...")
                self.db = FalkorDB(host=host, port=port, username="falkordb", password=password)
                self.graph = self.db.select_graph("astroph")
                # Force connection check by running a test query
                self.graph.query("RETURN 1")
                print(f"[{self.name}] Connected and graph selected.")
                break
            except Exception as e:
                if attempt == retries - 1:
                    raise
                print(f"[{self.name}] Connection failed: {e}. Retrying in 5 seconds...")
                time.sleep(5)

    def create_schema(self):
        print(f"[{self.name}] Creating schema index in FalkorDB...")
        try:
            # FalkorDB uses standard Cypher CREATE INDEX syntax
            self.graph.query("CREATE INDEX FOR (a:Author) ON (a.id)")
            print(f"[{self.name}] Index created successfully.")
        except Exception as e:
            print(f"[{self.name}] Index creation failed: {e}. Continuing...")

    def load_nodes(self, nodes):
        print(f"[{self.name}] Starting node loading of {len(nodes)} nodes...")
        batch_size = 5000
        for i in range(0, len(nodes), batch_size):
            batch = nodes[i:i+batch_size]
            # FalkorDB query takes parameters just like neo4j
            self.graph.query(
                "UNWIND $batch AS row CREATE (n:Author {id: row.id})",
                {"batch": batch}
            )
        print(f"[{self.name}] Finished loading nodes.")

    def load_edges(self, edges):
        print(f"[{self.name}] Starting edge loading of {len(edges)} edges...")
        batch_size = 5000
        for i in range(0, len(edges), batch_size):
            batch = edges[i:i+batch_size]
            self.graph.query(
                """
                UNWIND $batch AS row
                MATCH (src:Author {id: row.source})
                MATCH (tgt:Author {id: row.target})
                CREATE (src)-[:COLLABORATES]->(tgt)
                """,
                {"batch": batch}
            )
        print(f"[{self.name}] Finished loading edges.")

    def clear_data(self):
        print(f"[{self.name}] Clearing FalkorDB graph...")
        try:
            self.graph.delete()
            print(f"[{self.name}] Graph deleted.")
        except Exception as e:
            print(f"[{self.name}] Graph could not be deleted (might not exist): {e}")
        # Reselect graph to initialize a fresh empty instance
        self.graph = self.db.select_graph("astroph")

    def close(self):
        # falkordb library doesn't strictly require closing for simple connection pool,
        # but let's clear objects to be clean
        self.db = None
        self.graph = None
        print(f"[{self.name}] Connection closed.")
