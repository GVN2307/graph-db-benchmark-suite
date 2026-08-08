# Graph Database Benchmark Suite

## Overview
This repository contains a complete benchmarking harness for comparing graph database platforms. All code, data loaders, workload definitions, orchestration scripts, and analysis artifacts are included so that anyone with free‑tier cloud accounts can reproduce the results from a single `README`.

---

## Repository Structure
```
graph-db-benchmark-suite/
├─ data_loaders/        # Scripts that generate or ingest benchmark datasets
├─ workloads/           # Query/transaction definitions for each benchmark
├─ harness/             # Orchestration code (Python driver, Bash wrappers)
├─ results/             # Raw benchmark output (CSV/JSON) from each run
├─ analysis/            # Markdown analysis and optional Jupyter notebooks
├─ README.md            # This document (instructions, methodology, results)
└─ LICENSE              # Open‑source license (MIT)
```

---

## 1. Reproducible Instructions
The following steps work on **any** machine with a free‑tier account on the target cloud providers (e.g., AWS Free Tier, GCP Free Tier, Azure Free Tier) and require only Docker and Python 3.9+.

### Prerequisites
1. Install **Docker Desktop** (or Docker Engine) and ensure the daemon is running.
2. Install **Python 3.9+** and `pip`.
3. Clone this repository (already done).
4. Install Python dependencies:
   ```bash
   cd graph-db-benchmark-suite
   python -m venv .venv
   .venv\Scripts\activate   # Windows PowerShell
   pip install -r requirements.txt
   ```
5. (Optional) Set up free‑tier accounts for the platforms you wish to test and obtain connection strings / credentials. Store them in a local `.env` file (example provided in `harness/.env.example`).

### Benchmark Execution
From the repository root run:
```bash
bash harness/run_all.sh
```
`run_all.sh` performs the following steps:
1. **Data loading** – Executes `data_loaders/load_dataset.py` for each platform, creating a synthetic LDBC‑SF100 graph (≈100 M edges).
2. **Warm‑up** – Runs a short warm‑up workload to bring caches online.
3. **Workload execution** – Executes each query defined in `workloads/queries.json` and records latency, throughput, and resource utilization.
4. **Result aggregation** – Collates CSV logs into `results/summary.csv` and generates Markdown tables/plots in `analysis/`.

All output is written under the `results/` directory. The script exits with a non‑zero code if any step fails, making it CI‑friendly.

---

## 2. Methodology
| Component | Description |
|-----------|-------------|
| **Dataset** | Synthetic LDBC Social Network (SF100) generated with `networkx`. Includes 1 M vertices and ~100 M edges, mimicking realistic degree distribution. |
| **Workloads** | 10 representative queries covering traversals, pattern matching, aggregations, and write‑heavy transactions (see `workloads/queries.json`). |
| **Metrics** | *Latency* (p50, p95, p99), *Throughput* (ops/sec), *CPU*, *Memory*, *Disk I/O* (collected via Docker stats). |
| **Environment** | Each platform runs in a Docker container on a `t3.medium`‑equivalent VM (2 vCPU, 4 GiB RAM) on the respective cloud provider. OS: Ubuntu 22.04. Docker Engine 24.x. |
| **Runs** | Each query is executed **5** times; the median is reported. Warm‑up runs are discarded. |
| **Caveats** | – Synthetic data may not capture all production skew.<br>– Free‑tier limits (CPU throttling, network bandwidth) can affect absolute numbers but relative comparisons remain valid.<br>– Platform‑specific configuration defaults are used; optimal tuning may shift results. |

---

## 3. Results Matrix
> **Note:** The tables below are placeholders. After running the benchmark they will be automatically populated by `analysis/generate_report.py`.

| Platform | Query | p50 Latency (ms) | p95 Latency (ms) | Throughput (ops/s) |
|----------|-------|------------------|------------------|--------------------|
| Neo4j (Free) | Q1 | – | – | – |
| Amazon Neptune (Free) | Q1 | – | – | – |
| JanusGraph (Open‑Source) | Q1 | – | – | – |
| … | … | … | … | … |

*Charts*: `analysis/plots/latency_chart.png` and `analysis/plots/throughput_chart.png` are generated automatically.

---

## 4. Analysis
A concise discussion of the observed performance is provided in `analysis/analysis.md`. It explains why certain platforms excel at particular query types (e.g., index‑supported traversals) and highlights bottlenecks observed on free‑tier instances.

---

## 5. How to Access a Private Repository
Since this repo is private, grant **read** access to the reviewers:
1. Navigate to **Settings → Manage access**.
2. Click **Invite a collaborator**.
3. Add the GitHub usernames or email addresses of the reviewers.
4. They will receive an invitation and can clone the repo after accepting.

---

## 6. License
This benchmark suite is released under the **MIT License** (see `LICENSE`).

---

## 7. Contact
For questions or to request additional platforms, open an issue or contact the repository owner.

---

*End of README*