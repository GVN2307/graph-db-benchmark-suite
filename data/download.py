import os
import gzip
import urllib.request
import shutil

DATA_URL = "https://snap.stanford.edu/data/ca-AstroPh.txt.gz"
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
GZ_FILE = os.path.join(DATA_DIR, "ca-AstroPh.txt.gz")
TXT_FILE = os.path.join(DATA_DIR, "ca-AstroPh.txt")

def download_and_extract():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        print(f"Created directory: {DATA_DIR}")

    if not os.path.exists(TXT_FILE):
        if not os.path.exists(GZ_FILE):
            print(f"Downloading dataset from {DATA_URL}...")
            urllib.request.urlretrieve(DATA_URL, GZ_FILE)
            print("Download completed.")

        print(f"Extracting {GZ_FILE}...")
        with gzip.open(GZ_FILE, 'rb') as f_in:
            with open(TXT_FILE, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        print(f"Extraction completed. File saved to: {TXT_FILE}")

        # Cleanup compressed file
        try:
            os.remove(GZ_FILE)
            print("Cleaned up compressed file.")
        except Exception as e:
            print(f"Could not remove gz file: {e}")
    else:
        print("Dataset already downloaded and extracted.")

    # Check file contents
    with open(TXT_FILE, 'r') as f:
        line_count = sum(1 for _ in f)
    print(f"Dataset has {line_count} lines (including comments).")

def parse_dataset():
    """
    Parses the dataset and returns a tuple of (nodes, edges).
    Nodes is a list of dicts: [{'id': int, 'label': 'Author'}]
    Edges is a list of dicts: [{'source': int, 'target': int, 'type': 'COLLABORATES'}]
    """
    if not os.path.exists(TXT_FILE):
        download_and_extract()

    unique_nodes = set()
    unique_edges = set()

    print("Parsing dataset file...")
    with open(TXT_FILE, 'r') as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
            parts = line.strip().split()
            if len(parts) >= 2:
                u, v = int(parts[0]), int(parts[1])
                unique_nodes.add(u)
                unique_nodes.add(v)
                # Deduplicate undirected edge
                edge_pair = (min(u, v), max(u, v))
                unique_edges.add(edge_pair)

    nodes = [{"id": node_id, "label": "Author"} for node_id in sorted(unique_nodes)]
    edges = [{"source": e[0], "target": e[1], "type": "COLLABORATES"} for e in sorted(unique_edges)]
    
    print(f"Parsed {len(nodes)} unique nodes and {len(edges)} edges.")
    return nodes, edges

if __name__ == "__main__":
    download_and_extract()
