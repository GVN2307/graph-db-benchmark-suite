# Graph Database Cloud Benchmark Suite

This suite evaluates and benchmarks managed graph database cloud platforms on identical datasets and query workloads:
1. CognoDB Cloud
2. Neo4j AuraDB Free
3. FalkorDB Cloud
4. TypeDB Cloud
5. NebulaGraph Cloud

---

## Objective
The goal is to provide a reproducible, fair comparison of read throughput/latency, write latency, indexing speed, concurrent scaling, and aggregations across various graph database systems under free-tier constraints.

---

## Platforms Tested
- **CognoDB**: Cypher query language, Bolt API protocol. Instance: Free tier cloud instance.
- **Neo4j Aura**: Cypher query language, Bolt API protocol. Instance: AuraDB Free instance (limit ~200K elements).
- **FalkorDB**: Cypher query language, Redis API protocol. Instance: Free Tier (limit 100MB RAM).
- **TypeDB**: TypeQL query language, TypeQL RPC API protocol. Instance: TypeDB Cloud Free Cluster.
- **NebulaGraph**: nGQL query language, Thrift RPC API protocol. Instance: Nebula Cloud Free Tier.

---

## Dataset
- **Source**: SNAP CA-AstroPh collaboration network (Astro Physics collaborations)
- **Metadata**: 18,772 nodes, 198,110 edges (undirected, deduplicated)
- **Format**: Space-separated node ID pairs.
- **Loading**: Cleaned, parsed, and batched sequentially on each database.

---

## Methodology
1. **Deduplication**: Undirected edge pairs are deduplicated to guarantee exactly 198,110 edges.
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
   ```bash
   python main.py
   ```

---

## Results Matrix

### 1. Data Ingestion Speed
| Platform | Total Load Time (s) | Node Load Time (s) | Edge Load Time (s) | Node Throughput (nodes/s) | Edge Throughput (edges/s) | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| **CognoDB** | 5.185 | 2.524 | 2.661 | 4806.795 | 7443.779 | Sampled to 10% (12,132 nodes, 19,811 edges) |
| **Neo4j Aura** | 48.225 | 1.325 | 46.899 | 14162.330 | 4224.167 | Full dataset (18,772 nodes, 198,110 edges) |
| **FalkorDB** | 103.209 | 3.842 | 99.367 | 4886.000 | 1993.720 | Full dataset (18,772 nodes, 198,110 edges) |
| **TypeDB** | N/A | N/A | N/A | N/A | N/A | Failed during run (503 Service Unavailable) |
| **NebulaGraph** | N/A | N/A | N/A | N/A | N/A | Connection failed (BAD service status on host) |

### 2. Multi-Hop Traversals (Latency in ms)
| Platform | 1-Hop p50 | 1-Hop p95 | 2-Hop p50 | 2-Hop p95 | 3-Hop p50 | 3-Hop p95 |
| --- | --- | --- | --- | --- | --- | --- |
| **CognoDB** | 307.46 | 411.39 | 286.98 | 406.78 | 512.00 | 1852.42 |
| **Neo4j Aura** | 98.94 | 139.39 | 84.03 | 172.03 | 97.66 | 164.99 |
| **FalkorDB** | 316.16 | 429.31 | 304.38 | 411.39 | 324.35 | 501.50 |
| **TypeDB** | N/A | N/A | N/A | N/A | N/A | N/A |
| **NebulaGraph** | N/A | N/A | N/A | N/A | N/A | N/A |

### 3. Lookups (Latency in ms)
| Platform | Point p50 | Point p95 | Indexed p50 | Indexed p95 |
| --- | --- | --- | --- | --- |
| **CognoDB** | 314.11 | 485.38 | 307.71 | 505.60 |
| **Neo4j Aura** | 92.42 | 151.04 | 86.40 | 146.43 |
| **FalkorDB** | 311.30 | 434.18 | 309.76 | 418.82 |
| **TypeDB** | N/A | N/A | N/A | N/A |
| **NebulaGraph** | N/A | N/A | N/A | N/A |

### 4. Aggregations (Latency in ms)
| Platform | Node Count p50 | Node Count p95 | Edge Count p50 | Edge Count p95 |
| --- | --- | --- | --- | --- |
| **CognoDB** | 309.76 | 512.00 | 313.86 | 533.50 |
| **Neo4j Aura** | 77.57 | 136.06 | 81.54 | 172.80 |
| **FalkorDB** | 319.23 | 451.84 | 310.78 | 410.37 |
| **TypeDB** | N/A | N/A | N/A | N/A |
| **NebulaGraph** | N/A | N/A | N/A | N/A |

### 5. Mixed Workload (Concurrent Load Test)
| Platform | QPS | p50 Latency (ms) | p95 Latency (ms) | Failures |
| --- | --- | --- | --- | --- |
| **CognoDB** | 24.4 | 308.66 | 470.78 | 0 |
| **Neo4j Aura** | 110.0 | 81.17 | 126.83 | 0 |
| **FalkorDB** | 3.1 | 3311.72 | 3888.43 | 0 |
| **TypeDB** | N/A | N/A | N/A | N/A |
| **NebulaGraph** | N/A | N/A | N/A | N/A |

---

## Analysis

### Data Ingestion Speed
Neo4j AuraDB Free performed with high node throughput (14,162 nodes/s) but slowed down during relationship insertion due to index verification overhead on a cloud instance, completing the full dataset load in 48.23s. FalkorDB required 103.21s to load the dataset, heavily impacted by the 100MB RAM limit on its free tier, which triggers disk swaps/memory paging during intensive edge loads. CognoDB completed loading in 5.19s, but was restricted to a 10% sampled subset (19,811 edges) because of its strict free-tier scale limits (0.5GB RAM) preventing full dataset execution.

### Query Latency (Traversals, Lookups, Aggregations)
Neo4j AuraDB demonstrated superior latency characteristics across all read operations. For 1-hop, 2-hop, and 3-hop traversals, Neo4j stayed below 100ms (p50), utilizing its native graph storage engine (pointer chasing) and efficient driver-level connection pooling. Both FalkorDB and CognoDB averaged around 300ms (p50) for traversals, lookups, and count aggregations. This difference is mainly due to connection-level overhead, higher network latency on free tier endpoints, and single-threaded query processing limits on those free instances. CognoDB's 3-hop traversal latency rose to 1.85s (p95) as query complexity scaled.

### Concurrent Performance under Stress
Under a 10-thread concurrent mixed workload (80% read / 20% write), Neo4j Aura reached 110.0 QPS with stable latencies (81.17ms p50, 126.83ms p95), showcasing its robust concurrent execution capabilities. CognoDB handled the concurrent load at 24.4 QPS with 308.66ms p50 latency. FalkorDB suffered severe degradation, dropping to 3.1 QPS with median latencies exceeding 3.3s. This indicates that FalkorDB's free instance is single-threaded or restricted under concurrent connection pools, leading to thread contention, and memory exhaustion under concurrent write-write/read-write workloads.

---

## Caveats
- **Free Tier Scale & Throttling**: Free cloud offerings impose CPU/RAM caps. CognoDB ran with a 10% sample due to RAM limitations. FalkorDB's performance fell due to its 100MB RAM constraint.
- **Connection Issues**: NebulaGraph suffered bad connection statuses on its Thrift RPC port. TypeDB returned HTTP 503 Service Unavailable on its cloud endpoint.
- **Network Overhead**: Benchmark measurements include network round-trips from the client to the cloud instance, which adds a baseline latency of approximately 70-150ms depending on the region.