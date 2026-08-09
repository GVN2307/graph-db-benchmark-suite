import os
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.offline as op

def get_nested(dct, *keys, default=0.0):
    for key in keys:
        if isinstance(dct, dict) and key in dct:
            dct = dct[key]
        else:
            return default
    return dct

def safe_float(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0

def safe_fmt(val, fmt=".2f"):
    if isinstance(val, (int, float)):
        return f"{val:{fmt}}"
    try:
        fval = float(val)
        return f"{fval:{fmt}}"
    except (ValueError, TypeError):
        return str(val)

def generate_dashboard(results_dir="results", output_path="results/dashboard.html"):
    # Load all json result files in directory
    files = [f for f in os.listdir(results_dir) if f.endswith("_results.json")]
    platforms_data = {}
    
    for f in files:
        path = os.path.join(results_dir, f)
        try:
            with open(path, "r") as fh:
                data = json.load(fh)
                p_name = data.get("platform")
                if p_name:
                    platforms_data[p_name] = data
        except Exception as e:
            print(f"Error loading {f}: {e}")

    if not platforms_data:
        print("No platform data found to generate dashboard.")
        return

    # Extract metrics for plotting
    platforms = sorted(list(platforms_data.keys()))
    
    # 1. Loading times
    node_load = [safe_float(get_nested(platforms_data[p], "metrics", "data_loading", "node_load_time_sec")) for p in platforms]
    edge_load = [safe_float(get_nested(platforms_data[p], "metrics", "data_loading", "edge_load_time_sec")) for p in platforms]
    
    # 2. Traversals p50 & p95
    hop1_p50 = [safe_float(get_nested(platforms_data[p], "metrics", "1_hop_traversal", "p50_latency_ms")) for p in platforms]
    hop1_p95 = [safe_float(get_nested(platforms_data[p], "metrics", "1_hop_traversal", "p95_latency_ms")) for p in platforms]
    
    hop2_p50 = [safe_float(get_nested(platforms_data[p], "metrics", "2_hop_traversal", "p50_latency_ms")) for p in platforms]
    hop2_p95 = [safe_float(get_nested(platforms_data[p], "metrics", "2_hop_traversal", "p95_latency_ms")) for p in platforms]
    
    hop3_p50 = [safe_float(get_nested(platforms_data[p], "metrics", "3_hop_traversal", "p50_latency_ms")) for p in platforms]
    hop3_p95 = [safe_float(get_nested(platforms_data[p], "metrics", "3_hop_traversal", "p95_latency_ms")) for p in platforms]
    
    # 3. Lookups and aggregations
    pt_p50 = [safe_float(get_nested(platforms_data[p], "metrics", "point_lookup", "p50_latency_ms")) for p in platforms]
    idx_p50 = [safe_float(get_nested(platforms_data[p], "metrics", "indexed_lookup", "p50_latency_ms")) for p in platforms]
    cnt_nodes_p50 = [safe_float(get_nested(platforms_data[p], "metrics", "count_nodes", "p50_latency_ms")) for p in platforms]
    cnt_edges_p50 = [safe_float(get_nested(platforms_data[p], "metrics", "count_edges", "p50_latency_ms")) for p in platforms]

    # 4. Concurrency QPS and latency
    con_qps = [safe_float(get_nested(platforms_data[p], "metrics", "mixed_workload", "queries_per_second")) for p in platforms]
    con_p50 = [safe_float(get_nested(platforms_data[p], "metrics", "mixed_workload", "p50_latency_ms")) for p in platforms]
    con_p95 = [safe_float(get_nested(platforms_data[p], "metrics", "mixed_workload", "p95_latency_ms")) for p in platforms]

    # Optional Observability and Cost data
    cpu_list = []
    mem_list = []
    cost_1m_list = []
    
    for p in platforms:
        obs = get_nested(platforms_data[p], "metrics", "observability", default={})
        cost = get_nested(platforms_data[p], "metrics", "cost", default={})
        cpu_list.append(safe_float(obs.get("avg_cpu", 0.0)))
        mem_list.append(safe_float(obs.get("peak_mem_rss_mb", 0.0)))
        cost_1m_list.append(safe_float(cost.get("cost_per_million_queries_usd", 0.0)))

    # Initialize Plotly Figures
    fig1 = go.Figure()
    fig1.add_trace(go.Bar(name='Node Load Time (s)', x=platforms, y=node_load, marker_color='#3b82f6'))
    fig1.add_trace(go.Bar(name='Edge Load Time (s)', x=platforms, y=edge_load, marker_color='#1d4ed8'))
    fig1.update_layout(title="Data Ingestion Speeds (Lower is Better)", barmode='group', template="plotly_white")

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(name='1-Hop Traversal p50 (ms)', x=platforms, y=hop1_p50, marker_color='#a7f3d0'))
    fig2.add_trace(go.Bar(name='2-Hop Traversal p50 (ms)', x=platforms, y=hop2_p50, marker_color='#34d399'))
    fig2.add_trace(go.Bar(name='3-Hop Traversal p50 (ms)', x=platforms, y=hop3_p50, marker_color='#059669'))
    fig2.update_layout(title="Multi-hop Traversal Latencies - p50 (Lower is Better)", barmode='group', template="plotly_white")

    fig3 = go.Figure()
    fig3.add_trace(go.Bar(name='1-Hop Traversal p95 (ms)', x=platforms, y=hop1_p95, marker_color='#fca5a5'))
    fig3.add_trace(go.Bar(name='2-Hop Traversal p95 (ms)', x=platforms, y=hop2_p95, marker_color='#f87171'))
    fig3.add_trace(go.Bar(name='3-Hop Traversal p95 (ms)', x=platforms, y=hop3_p95, marker_color='#dc2626'))
    fig3.update_layout(title="Multi-hop Traversal Tail Latencies - p95 (Lower is Better)", barmode='group', template="plotly_white")

    fig4 = go.Figure()
    fig4.add_trace(go.Bar(name='Point Lookup p50 (ms)', x=platforms, y=pt_p50, marker_color='#fef08a'))
    fig4.add_trace(go.Bar(name='Indexed Lookup p50 (ms)', x=platforms, y=idx_p50, marker_color='#fde047'))
    fig4.add_trace(go.Bar(name='Count Nodes p50 (ms)', x=platforms, y=cnt_nodes_p50, marker_color='#fbbf24'))
    fig4.add_trace(go.Bar(name='Count Edges p50 (ms)', x=platforms, y=cnt_edges_p50, marker_color='#d97706'))
    fig4.update_layout(title="Lookups and Aggregation Latencies - p50 (Lower is Better)", barmode='group', template="plotly_white")

    fig5 = go.Figure()
    fig5.add_trace(go.Bar(name='Queries per Second (QPS)', x=platforms, y=con_qps, marker_color='#8b5cf6'))
    fig5.update_layout(title="Concurrent Query Throughput (Higher is Better)", template="plotly_white")

    fig6 = go.Figure()
    fig6.add_trace(go.Bar(name='Concurrent p50 (ms)', x=platforms, y=con_p50, marker_color='#ddd6fe'))
    fig6.add_trace(go.Bar(name='Concurrent p95 (ms)', x=platforms, y=con_p95, marker_color='#8b5cf6'))
    fig6.update_layout(title="Concurrent Stress Latency Profile (Lower is Better)", barmode='group', template="plotly_white")

    # Generate custom observation resource charts if available
    fig7 = go.Figure()
    fig7.add_trace(go.Bar(name='Peak Mem RSS (MB)', x=platforms, y=mem_list, marker_color='#e2e8f0'))
    fig7.add_trace(go.Bar(name='Avg CPU (%)', x=platforms, y=cpu_list, marker_color='#94a3b8'))
    fig7.update_layout(title="Client-Side Resource Footprint (Lower is Better)", barmode='group', template="plotly_white")

    fig8 = go.Figure()
    fig8.add_trace(go.Bar(name='Cost / Million Queries (USD)', x=platforms, y=cost_1m_list, marker_color='#10b981'))
    fig8.update_layout(title="TCO Cost Efficiency Comparison (Lower is Better)", template="plotly_white")

    # Generate standalone html plots
    p1_html = op.plot(fig1, include_plotlyjs=False, output_type='div')
    p2_html = op.plot(fig2, include_plotlyjs=False, output_type='div')
    p3_html = op.plot(fig3, include_plotlyjs=False, output_type='div')
    p4_html = op.plot(fig4, include_plotlyjs=False, output_type='div')
    p5_html = op.plot(fig5, include_plotlyjs=False, output_type='div')
    p6_html = op.plot(fig6, include_plotlyjs=False, output_type='div')
    p7_html = op.plot(fig7, include_plotlyjs=False, output_type='div')
    p8_html = op.plot(fig8, include_plotlyjs=False, output_type='div')

    # Build matrix table rows
    table_rows = ""
    for p in platforms:
        m = platforms_data[p]["metrics"]
        cost = m.get("cost", {})
        
        node_load_time = get_nested(platforms_data[p], "metrics", "data_loading", "node_load_time_sec")
        edge_load_time = get_nested(platforms_data[p], "metrics", "data_loading", "edge_load_time_sec")
        
        hop1_p50_val = get_nested(platforms_data[p], "metrics", "1_hop_traversal", "p50_latency_ms")
        hop1_p95_val = get_nested(platforms_data[p], "metrics", "1_hop_traversal", "p95_latency_ms")
        
        hop2_p50_val = get_nested(platforms_data[p], "metrics", "2_hop_traversal", "p50_latency_ms")
        hop2_p95_val = get_nested(platforms_data[p], "metrics", "2_hop_traversal", "p95_latency_ms")
        
        hop3_p50_val = get_nested(platforms_data[p], "metrics", "3_hop_traversal", "p50_latency_ms")
        hop3_p95_val = get_nested(platforms_data[p], "metrics", "3_hop_traversal", "p95_latency_ms")
        
        con_qps_val = get_nested(platforms_data[p], "metrics", "mixed_workload", "queries_per_second")
        cost_m_val = cost.get("cost_per_million_queries_usd", 0.0)
        
        table_rows += f"""
        <tr class="border-b hover:bg-gray-50 text-sm">
            <td class="px-6 py-4 font-medium text-gray-900">{p}</td>
            <td class="px-6 py-4">{safe_fmt(node_load_time)}s</td>
            <td class="px-6 py-4">{safe_fmt(edge_load_time)}s</td>
            <td class="px-6 py-4 font-semibold">{safe_fmt(hop1_p50_val)} / {safe_fmt(hop1_p95_val)}</td>
            <td class="px-6 py-4 font-semibold">{safe_fmt(hop2_p50_val)} / {safe_fmt(hop2_p95_val)}</td>
            <td class="px-6 py-4 font-semibold">{safe_fmt(hop3_p50_val)} / {safe_fmt(hop3_p95_val)}</td>
            <td class="px-6 py-4 font-semibold">{safe_fmt(con_qps_val)} QPS</td>
            <td class="px-6 py-4">${safe_fmt(cost_m_val)}</td>
        </tr>
        """

    # Combine into a premium modern dashboard template
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Graph Database Cloud Benchmark Dashboard</title>
        <script src="https://cdn.plot.ly/plotly-2.24.1.min.js"></script>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
        <style>
            body {{ font-family: 'Outfit', sans-serif; }}
        </style>
    </head>
    <body class="bg-slate-50 text-slate-800">
        <header class="bg-gradient-to-r from-violet-600 via-indigo-600 to-blue-600 text-white shadow-lg py-8 px-6">
            <div class="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center">
                <div>
                    <h1 class="text-3xl font-bold tracking-tight">Graph Database Cloud Benchmarking Suite</h1>
                    <p class="text-violet-100 mt-2 text-sm md:text-base">Production-grade performance matrices, observability profiles, and statistical audits.</p>
                </div>
                <div class="mt-4 md:mt-0 bg-white/10 backdrop-blur-md rounded-xl p-3 border border-white/20 text-xs">
                    <span class="font-bold">Dataset:</span> SNAP Astro Physics Collaboration Graph<br>
                    <span class="font-bold">Vertices:</span> 18,772 | <span class="font-bold">Edges:</span> 198,110
                </div>
            </div>
        </header>

        <main class="max-w-7xl mx-auto px-4 py-8 space-y-8">
            <!-- Results Comparison Matrix -->
            <section class="bg-white rounded-2xl shadow-sm border p-6">
                <h2 class="text-xl font-bold text-slate-900 mb-4">Core Performance Matrix Summary</h2>
                <div class="overflow-x-auto">
                    <table class="min-w-full text-left border-collapse">
                        <thead>
                            <tr class="bg-slate-100 text-slate-700 text-xs font-semibold uppercase tracking-wider border-b">
                                <th class="px-6 py-3">Platform</th>
                                <th class="px-6 py-3">Node Ingest (s)</th>
                                <th class="px-6 py-3">Edge Ingest (s)</th>
                                <th class="px-6 py-3">1-Hop (p50 / p95 ms)</th>
                                <th class="px-6 py-3">2-Hop (p50 / p95 ms)</th>
                                <th class="px-6 py-3">3-Hop (p50 / p95 ms)</th>
                                <th class="px-6 py-3">Stress Capacity</th>
                                <th class="px-6 py-3">Cost / 1M Q</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y">
                            {table_rows}
                        </tbody>
                    </table>
                </div>
            </section>

            <!-- Plotly charts sections -->
            <section class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div class="bg-white p-4 rounded-2xl shadow-sm border">{p1_html}</div>
                <div class="bg-white p-4 rounded-2xl shadow-sm border">{p8_html}</div>
            </section>

            <section class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div class="bg-white p-4 rounded-2xl shadow-sm border">{p2_html}</div>
                <div class="bg-white p-4 rounded-2xl shadow-sm border">{p3_html}</div>
            </section>

            <section class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div class="bg-white p-4 rounded-2xl shadow-sm border">{p4_html}</div>
                <div class="bg-white p-4 rounded-2xl shadow-sm border">{p7_html}</div>
            </section>

            <section class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div class="bg-white p-4 rounded-2xl shadow-sm border">{p5_html}</div>
                <div class="bg-white p-4 rounded-2xl shadow-sm border">{p6_html}</div>
            </section>
        </main>
        <footer class="bg-slate-900 text-slate-400 py-6 text-center text-xs mt-12">
            Generated automatically by the Graph Database Cloud Benchmark Suite
        </footer>
    </body>
    </html>
    """
    
    with open(output_path, "w") as fh:
        fh.write(html_content)
    print(f"Interactive dashboard successfully generated at: {output_path}")

if __name__ == "__main__":
    generate_dashboard()
