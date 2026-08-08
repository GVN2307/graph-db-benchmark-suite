import os
import time
from neo4j import GraphDatabase
from loaders.base_loader import BaseGraphLoader

class Neo4jLoader(BaseGraphLoader):
    def __init__(self):
        super().__init__()
        self.driver = None

    def connect(self):
        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME") or "neo4j"
        password = os.getenv("NEO4J_PASSWORD")
        if not uri or not user or not password:
            raise ValueError("Neo4j Aura credentials are not fully set in .env")
        
        # Bypass Windows SSL verification issues by using ssc (Self-Signed Certificate) URI schemes
        if uri.startswith("neo4j+s://"):
            uri = uri.replace("neo4j+s://", "neo4j+ssc://")
        elif uri.startswith("bolt+s://"):
            uri = uri.replace("bolt+s://", "bolt+ssc://")
            
        retries = 3
        for attempt in range(retries):
            try:
                print(f"[{self.name}] Connecting to {uri} with user {user} (Attempt {attempt+1}/{retries})...")
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
        batch_size = 1000
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
            time.sleep(0.05)  # Tiny sleep to avoid overwhelming Free Tier instances
        print(f"[{self.name}] Finished loading edges.")

    def clear_data(self):
        print(f"[{self.name}] Clearing database data...")
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        print(f"[{self.name}] Database cleared.")

    def close(self):
        if self.driver:
            self.driver.close()
            print(f"[{self.name}] Connection closed.")
