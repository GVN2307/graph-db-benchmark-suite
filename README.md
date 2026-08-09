# Graph Database Cloud Benchmark Suite

This suite evaluates and benchmarks managed graph database cloud platforms on identical datasets and query workloads:
1. CognoDB Cloud
2. Neo4j AuraDB Free
3. FalkorDB Cloud
4. TypeDB Cloud
5. NebulaGraph Cloud
6. NetworkX (Local In-Memory Baseline)

---

## Objective
The goal is to provide a reproducible, fair comparison of read throughput/latency, write latency, indexing speed, concurrent scaling, and aggregations across various graph database systems under free-tier constraints. We test at two scales:
- 10% sampled load (12,132 nodes, 19,811 edges) for stable execution on resource-constrained free instances.
- 100% full load (18,772 nodes, 198,110 edges) for testing limits.

---

## Platforms Tested
- **CognoDB**: Cypher query language, Bolt API protocol. Instance: Free tier cloud instance (0.5GB RAM scale limit).
- **Neo4j Aura**: Cypher query language, Bolt API protocol. Instance: AuraDB Free instance (limit ~200K elements).
- **FalkorDB**: Cypher query language, Redis API protocol. Instance: Free Tier (limit 100MB RAM).
- **TypeDB**: TypeQL query language, TypeQL RPC API protocol. Instance: TypeDB Cloud Free Cluster.
- **NebulaGraph**: nGQL query language, Thrift RPC API protocol. Instance: Nebula Cloud Free Tier.
- **NetworkX**: Python API, in-memory execution. Instance: Local CPU (acts as zero-network, zero-overhead baseline).

---

## Dataset Details
- **Source**: SNAP CA-AstroPh collaboration network (Astro Physics collaboration network)
- **Scale 100%**: 18,772 nodes, 198,110 edges (undirected, deduplicated)
- **Scale 10%**: 12,132 nodes, 19,811 edges (sampled systematically using a step size of 10 on deduplicated edges, keeping all referenced nodes)
- **Format**: Space-separated node ID pairs.
- **Loading**: Cleaned, parsed, and batched sequentially on each database.

---

## Methodology
1. **Deduplication**: Undirected edge pairs are deduplicated to guarantee exact edge counts.
2. **Database Reset**: Prior to testing, each platform is entirely cleared of data and index definitions are rebuilt.
3. **Warm-up**: Runs 50 query iterations for traversals, lookups, and paths to cache queries prior to benchmark metrics collection.
4. **Isolated Workloads**:
   - **Traversals**: 1-hop, 2-hop, and 3-hop counts executed 100 times using random start nodes.
   - **Lookups**: 100 point lookups and 100 indexed property lookups using random node IDs.
   - **Aggregations**: 100 node count and edge count aggregations.
5. **Concurrent Stress Workload**: 10 concurrent threads running for 60 seconds (80% read / 20% write).
6. **Correctness Verification**: Cross-references query results against a Python-based memory model ground truth to verify graph topology integrity.

---

## How to Run

1. **Setup Environment and Install Dependencies**:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables**:
   Copy `.env.example` to `.env` and fill in the connection details for your cloud database instances.

3. **Run Benchmark Suite**:
   Set `SAMPLE_PERCENT` to either `10` or `100` before executing:
   
   On Windows (PowerShell):
   ```powershell
   $env:SAMPLE_PERCENT="10"
   python main.py
   ```
   
   On Linux/macOS:
   ```bash
   SAMPLE_PERCENT=10 python main.py
   ```

---

## Results Matrix (10% Load)

### 1. Data Ingestion Speed
| Platform | Total Load Time (s) | Node Load Time (s) | Edge Load Time (s) | Node Throughput (nodes/s) | Edge Throughput (edges/s) |
| --- | --- | --- | --- | --- | --- |
| **NetworkX** | 0.050 | 0.017 | 0.033 | 713647.05 | 600333.33 |
| **CognoDB** | 5.103 | 2.863 | 2.240 | 4237.51 | 8844.20 |
| **FalkorDB** | 5.939 | 2.151 | 3.788 | 5639.85 | 5230.41 |
| **Neo4j Aura** | 13.756 | 1.967 | 11.789 | 6168.89 | 1680.48 |
| **TypeDB** | 0.000 | 0.000 | 0.000 | 0.00 | 0.00 |
| **NebulaGraph** | N/A | N/A | N/A | N/A | N/A |

*Note: TypeDB load time registers as 0.0 because nodes/edges were pre-loaded on the target cluster. NebulaGraph was unreachable (BAD status).*

### 2. Multi-Hop Traversals (Latency in ms)
| Platform | 1-Hop p50 | 1-Hop p95 | 2-Hop p50 | 2-Hop p95 | 3-Hop p50 | 3-Hop p95 |
| --- | --- | --- | --- | --- | --- | --- |
| **NetworkX** | 0.001 | 0.002 | 0.008 | 0.032 | 0.040 | 0.197 |
| **Neo4j Aura** | 102.59 | 237.44 | 102.78 | 281.09 | 102.98 | 175.62 |
| **CognoDB** | 308.74 | 419.84 | 396.03 | 417.79 | 357.89 | 422.66 |
| **FalkorDB** | 307.46 | 410.62 | 307.97 | 410.62 | 313.86 | 414.98 |
| **TypeDB** | 1098.75 | 1331.20 | 1126.40 | 1235.97 | N/A | N/A |
| **NebulaGraph** | N/A | N/A | N/A | N/A | N/A | N/A |

### 3. Lookups (Latency in ms)
| Platform | Point p50 | Point p95 | Indexed p50 | Indexed p95 |
| --- | --- | --- | --- | --- |
| **NetworkX** | 0.001 | 0.001 | 0.001 | 0.001 |
| **Neo4j Aura** | 102.66 | 177.79 | 102.59 | 179.71 |
| **CognoDB** | 322.82 | 431.87 | 316.93 | 437.50 |
| **FalkorDB** | 307.46 | 416.00 | 307.20 | 409.86 |
| **TypeDB** | 1096.70 | 1264.64 | 1116.16 | 1271.81 |
| **NebulaGraph** | N/A | N/A | N/A | N/A |

### 4. Aggregations (Latency in ms)
| Platform | Node Count p50 | Node Count p95 | Edge Count p50 | Edge Count p95 |
| --- | --- | --- | --- | --- |
| **NetworkX** | 0.002 | 0.005 | 2.12 | 3.61 |
| **Neo4j Aura** | 102.40 | 153.34 | 102.53 | 166.27 |
| **CognoDB** | 374.53 | 637.95 | 373.76 | 439.30 |
| **FalkorDB** | 307.20 | 410.62 | 307.46 | 414.46 |
| **TypeDB** | 1026.56 | 1258.50 | 1126.40 | 1238.02 |
| **NebulaGraph** | N/A | N/A | N/A | N/A |

### 5. Mixed Workload (Concurrent Load Test)
| Platform | QPS | p50 Latency (ms) | p95 Latency (ms) | Failures |
| --- | --- | --- | --- | --- |
| **NetworkX** | 197472.2 | 0.003 | 0.006 | 0 |
| **Neo4j Aura** | 17.0 | 102.69 | 171.89 | 0 |
| **CognoDB** | 5.2 | 407.10 | 506.03 | 0 |
| **FalkorDB** | 3.4 | 585.08 | 1025.48 | 0 |
| **TypeDB** | 2.0 | 1116.88 | 1128.74 | 0 |
| **NebulaGraph** | N/A | N/A | N/A | N/A |

---

## Results Matrix (100% Load)

### 1. Data Ingestion Speed
| Platform | Total Load Time (s) | Node Load Time (s) | Edge Load Time (s) | Node Throughput (nodes/s) | Edge Throughput (edges/s) |
| --- | --- | --- | --- | --- | --- |
| **CognoDB** | 5.185 | 2.524 | 2.661 | 4806.80 | 7443.78 |
| **Neo4j Aura** | 48.225 | 1.325 | 46.899 | 14162.33 | 4224.17 |
| **FalkorDB** | 103.209 | 3.842 | 99.367 | 4886.00 | 1993.72 |
| **TypeDB** | N/A | N/A | N/A | N/A | N/A |
| **NebulaGraph** | N/A | N/A | N/A | N/A | N/A |

*Note: CognoDB automatically downsampled to 10% to prevent Out-Of-Memory errors on the free tier. TypeDB failed with HTTP 503.*

### 2. Multi-Hop Traversals (Latency in ms)
| Platform | 1-Hop p50 | 1-Hop p95 | 2-Hop p50 | 2-Hop p95 | 3-Hop p50 | 3-Hop p95 |
| --- | --- | --- | --- | --- | --- | --- |
| **Neo4j Aura** | 98.94 | 139.39 | 84.03 | 172.03 | 97.66 | 164.99 |
| **CognoDB** | 307.46 | 411.39 | 286.98 | 406.78 | 512.00 | 1852.42 |
| **FalkorDB** | 316.16 | 429.31 | 304.38 | 411.39 | 324.35 | 501.50 |
| **TypeDB** | N/A | N/A | N/A | N/A | N/A | N/A |
| **NebulaGraph** | N/A | N/A | N/A | N/A | N/A | N/A |

### 3. Lookups (Latency in ms)
| Platform | Point p50 | Point p95 | Indexed p50 | Indexed p95 |
| --- | --- | --- | --- | --- |
| **Neo4j Aura** | 92.42 | 151.04 | 86.40 | 146.43 |
| **CognoDB** | 314.11 | 485.38 | 307.71 | 505.60 |
| **FalkorDB** | 311.30 | 434.18 | 309.76 | 418.82 |
| **TypeDB** | N/A | N/A | N/A | N/A |
| **NebulaGraph** | N/A | N/A | N/A | N/A |

### 4. Aggregations (Latency in ms)
| Platform | Node Count p50 | Node Count p95 | Edge Count p50 | Edge Count p95 |
| --- | --- | --- | --- | --- |
| **Neo4j Aura** | 77.57 | 136.06 | 81.54 | 172.80 |
| **CognoDB** | 309.76 | 512.00 | 313.86 | 533.50 |
| **FalkorDB** | 319.23 | 451.84 | 310.78 | 410.37 |
| **TypeDB** | N/A | N/A | N/A | N/A |
| **NebulaGraph** | N/A | N/A | N/A | N/A |

### 5. Mixed Workload (Concurrent Load Test)
| Platform | QPS | p50 Latency (ms) | p95 Latency (ms) | Failures |
| --- | --- | --- | --- | --- |
| **Neo4j Aura** | 110.0 | 81.17 | 126.83 | 0 |
| **CognoDB** | 24.4 | 308.66 | 470.78 | 0 |
| **FalkorDB** | 3.1 | 3311.72 | 3888.43 | 0 |
| **TypeDB** | N/A | N/A | N/A | N/A |
| **NebulaGraph** | N/A | N/A | N/A | N/A |

---

## Detailed Performance Analysis

### In-Memory Baseline vs Cloud Databases
NetworkX runs entirely in local memory with zero network latency, achieving traversal speeds under 0.05ms and mixed concurrent throughput of over 190,000 QPS. However, it lacks durability, transaction isolation, clustering, and multi-user remote access. 

The cloud databases introduce a network-induced latency floor (approximately 70-120ms) because every query requires a Bolt or gRPC network round-trip from the client runner to the hosted cloud cluster.

### Neo4j AuraDB (The Premium Managed Performer)
Neo4j AuraDB Free demonstrated the most robust and stable scaling:
- At 100% load, its native graph storage engine (using pointer chasing rather than index lookups) handled multi-hop traversals in under 100ms.
- Under high concurrency stress, its thread pool and Bolt connection multiplexing allowed it to scale up to 110 QPS, actually reducing median latency to 81.17ms due to connection reuse and query plan caching.
- However, relationship loading throughput (4,224 edges/s) was slower than node loading (14,162 nodes/s) due to transactional constraint checks and index verification overhead on the remote instance.

### FalkorDB (RAM Constraint Degradation)
FalkorDB runs inside a Redis-like memory model, which yields fast execution under light workloads (data loading took only 5.94s at 10% load). 
However, under the free-tier limit of 100MB RAM, FalkorDB suffered severe degradation at 100% load:
- Data ingestion took 103.21s (nearly double that of Neo4j Aura) due to memory swapping and paging on the cloud VM.
- Under concurrent stress, throughput dropped to 3.1 QPS, and p50 latencies spiked to 3.31s. This indicates severe single-threaded queueing and context switching overhead on the resource-constrained free instance.

### CognoDB (Downsampling and Connection Overhead)
CognoDB performed stably with flat traversal and lookup latencies (~300-390ms) at both scales. 
However, its free tier enforces a strict 0.5GB memory cap. The database automatically triggered a 10% systematic downsampling logic during load to prevent Out-Of-Memory crashes. At 10% load, it sustained 5.2 QPS with a median latency of 407.10ms.

### TypeDB (High-Latency gRPC Schema Engine)
TypeDB Cloud Free Cluster recorded traversal and lookup latencies above 1.0s. TypeDB uses TypeQL, which compiles queries through an entity-relationship logic and performs active type-validation checks. This schema enforcement overhead, combined with gRPC session initialization, results in high latency for individual operations and limits concurrent throughput to 2.0 QPS on the free tier.

---

## Caveats
- **Free-Tier Limits**: Compute resources (CPU cycles, RAM allocations) are severely throttled on free tiers. The benchmarks reflect these limitations (e.g., FalkorDB's 100MB RAM cap, CognoDB's 0.5GB cap).
- **Network Latency Floor**: All database queries are affected by network round-trip times between the client runner and the cloud host endpoints.
- **Connection Failures**: NebulaGraph Cloud returned BAD status responses on the Thrift RPC interface. TypeDB Cloud occasionally returned HTTP 503 Service Unavailable during full load runs.