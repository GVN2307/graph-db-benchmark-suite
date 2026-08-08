import os
from dotenv import load_dotenv
from typedb.driver import TypeDB, Credentials, DriverOptions, DriverTlsConfig, TransactionType
from loaders.base_loader import BaseGraphLoader

class TypeDBLoader(BaseGraphLoader):
    def __init__(self):
        super().__init__()
        self.driver = None
        self.database_name = None

    def connect(self):
        # Load environment variables from .env if present
        load_dotenv()
        host = os.getenv("TYPEDB_HOST")
        port = os.getenv("TYPEDB_PORT", "443")
        user = os.getenv("TYPEDB_USER", "admin")
        password = os.getenv("TYPEDB_PASSWORD")
        self.database_name = os.getenv("TYPEDB_DATABASE", "typedb-benchmark")
        
        if not host or not password:
            raise ValueError("TypeDB credentials are not fully set in .env")
            
        address = f"{host}:{port}"
        credentials = Credentials(user, password)
        
        retries = 3
        for attempt in range(retries):
            try:
                print(f"[{self.name}] Connecting to TypeDB Cloud at {address} (Attempt {attempt+1}/{retries})...")
                # Try TLS first
                try:
                    options = DriverOptions(DriverTlsConfig.enabled_with_native_root_ca())
                    self.driver = TypeDB.driver(address, credentials, options)
                    print(f"[{self.name}] Connected successfully with TLS.")
                except Exception as tls_err:
                    print(f"[{self.name}] TLS connection failed: {tls_err}. Trying connection without TLS...")
                    options_no_tls = DriverOptions(DriverTlsConfig.disabled())
                    self.driver = TypeDB.driver(address, credentials, options_no_tls)
                    print(f"[{self.name}] Connected successfully without TLS.")
                
                # Check connection by ensuring database exists
                if not self.driver.databases.contains(self.database_name):
                    print(f"[{self.name}] Creating database: {self.database_name}")
                    self.driver.databases.create(self.database_name)
                break
            except Exception as e:
                if attempt == retries - 1:
                    raise
                print(f"[{self.name}] Connection failed: {e}. Retrying in 5 seconds...")
                time.sleep(5)

    def create_schema(self):
        print(f"[{self.name}] Defining schema...")
        schema_query = """
        define
          attribute uid value string;
          relation collaborates,
            relates collaborator @card(1..);
          entity person,
            owns uid,
            plays collaborates:collaborator;
        """
        with self.driver.transaction(self.database_name, TransactionType.SCHEMA) as tx:
            tx.query(schema_query).resolve()
            tx.commit()
        print(f"[{self.name}] Schema defined successfully.")

    def load_nodes(self, nodes):
        print(f"[{self.name}] Starting node loading of {len(nodes)} nodes with pipelining...")
        batch_size = 1000
        for i in range(0, len(nodes), batch_size):
            batch = nodes[i:i+batch_size]
            with self.driver.transaction(self.database_name, TransactionType.WRITE) as tx:
                promises = []
                for node in batch:
                    node_id_str = str(node["id"])
                    query = f'insert $p isa person, has uid "{node_id_str}";'
                    promises.append(tx.query(query))
                for p in promises:
                    p.resolve()
                tx.commit()
        print(f"[{self.name}] Finished loading nodes.")

    def load_edges(self, edges):
        print(f"[{self.name}] Starting edge loading of {len(edges)} edges in parallel...")
        num_threads = 20
        chunk_size = (len(edges) + num_threads - 1) // num_threads
        chunks = [edges[i:i+chunk_size] for i in range(0, len(edges), chunk_size)]
        
        from concurrent.futures import ThreadPoolExecutor
        
        def worker(thread_idx, chunk):
            batch_size = 500
            for i in range(0, len(chunk), batch_size):
                batch = chunk[i:i+batch_size]
                try:
                    with self.driver.transaction(self.database_name, TransactionType.WRITE) as tx:
                        promises = []
                        for edge in batch:
                            src_id = str(edge["source"])
                            tgt_id = str(edge["target"])
                            query = f'match $p1 isa person, has uid "{src_id}"; $p2 isa person, has uid "{tgt_id}"; insert (collaborator: $p1, collaborator: $p2) isa collaborates;'
                            promises.append(tx.query(query))
                        for p in promises:
                            p.resolve()
                        tx.commit()
                except Exception as e:
                    print(f"[{self.name} Thread-{thread_idx}] Batch error: {e}")
            print(f"[{self.name} Thread-{thread_idx}] Finished chunk.")

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker, idx, chunk) for idx, chunk in enumerate(chunks)]
            for future in futures:
                future.result()
        print(f"[{self.name}] Finished loading edges.")

    def clear_data(self):
        print(f"[{self.name}] Re-creating database to clear schema and data...")
        if self.driver.databases.contains(self.database_name):
            self.driver.databases.get(self.database_name).delete()
        self.driver.databases.create(self.database_name)
        print(f"[{self.name}] Re-created database: {self.database_name}")

    def close(self):
        if self.driver:
            self.driver.close()
            print(f"[{self.name}] Connection closed.")
