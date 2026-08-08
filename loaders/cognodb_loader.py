import os
import time
from neo4j import GraphDatabase
from loaders.base_loader import BaseGraphLoader

class CognoDBLoader(BaseGraphLoader):
    def __init__(self):
        super().__init__()
        self.driver = None

    def connect(self):
        uri = os.getenv("COGNODB_URI")
        user = os.getenv("COGNODB_USER")
        password = os.getenv("COGNODB_PASSWORD")
        if not uri or not user or not password:
            raise ValueError("CognoDB credentials are not fully set in .env")
        
        # Bypass Windows SSL verification issues by using ssc (Self-Signed Certificate) URI schemes
        if uri.startswith("neo4j+s://"):
            uri = uri.replace("neo4j+s://", "neo4j+ssc://")
        elif uri.startswith("bolt+s://"):
            uri = uri.replace("bolt+s://", "bolt+ssc://")
            
        retries = 3
        for attempt in range(retries):
            try:
                print(f"[{self.name}] Connecting to {uri} (Attempt {attempt+1}/{retries})...")
                self.driver = GraphDatabase.driver(uri, auth=(user, password))
                self.driver.verify_connectivity()
                print(f"[{self.name}] Connected successfully.")
                break
            except Exception as e:
                if attempt == retries - 1:
                    raise
                print(f"[{self.name}] Connection failed: {e}. Retrying in 5 seconds...")
                time.sleep(5)

    def create_schema(self):
        print(f"[{self.name}] Creating schema index...")
        with self.driver.session() as session:
            try:
                session.run("CREATE INDEX author_id_index FOR (a:Author) ON (a.id)")
                print(f"[{self.name}] Index created using standard syntax.")
            except Exception as e:
                print(f"[{self.name}] Standard index creation failed: {e}. Trying legacy syntax...")
                try:
                    session.run("CREATE INDEX ON :Author(id)")
                    print(f"[{self.name}] Index created using legacy syntax.")
                except Exception as e2:
                    print(f"[{self.name}] Legacy index creation failed: {e2}. Continuing...")

    def load_nodes(self, nodes):
        print(f"[{self.name}] Starting node loading of {len(nodes)} nodes...")
        batch_size = 5000
        for i in range(0, len(nodes), batch_size):
            batch = nodes[i:i+batch_size]
            with self.driver.session() as session:
                session.run(
                    "UNWIND $batch AS row CREATE (n:Author {id: row.id})",
                    batch=batch
                )
        print(f"[{self.name}] Finished loading nodes.")

    def load_edges(self, edges):
        print(f"[{self.name}] Starting edge loading of {len(edges)} edges...")
        batch_size = 5000
        for i in range(0, len(edges), batch_size):
            batch = edges[i:i+batch_size]
            with self.driver.session() as session:
                session.run(
                    """
                    UNWIND $batch AS row
                    MATCH (src:Author {id: row.source})
                    MATCH (tgt:Author {id: row.target})
                    CREATE (src)-[:COLLABORATES]->(tgt)
                    """,
                    batch=batch
                )
        print(f"[{self.name}] Finished loading edges.")

    def clear_data(self):
        print(f"[{self.name}] Clearing database data in batches...")
        deleted = 0
        with self.driver.session() as session:
            while True:
                res = session.run("MATCH (n) WITH n LIMIT 5000 DETACH DELETE n RETURN count(n)").single()
                count = res[0] if res else 0
                deleted += count
                if count == 0:
                    break
        print(f"[{self.name}] Database cleared. Deleted {deleted} nodes and relationships.")

    def close(self):
        if self.driver:
            self.driver.close()
            print(f"[{self.name}] Connection closed.")
