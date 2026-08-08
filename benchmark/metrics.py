import statistics

def calculate_percentiles(latencies_ms):
    """Return p50, p95 from a list of float latencies."""
    if not latencies_ms:
        return {"p50": 0.0, "p95": 0.0}
    
    sorted_lat = sorted(latencies_ms)
    p50 = statistics.median(sorted_lat)
    
    # Calculate index safely
    idx = min(int(len(sorted_lat) * 0.95), len(sorted_lat) - 1)
    p95 = sorted_lat[idx]
    
    return {"p50": round(p50, 3), "p95": round(p95, 3)}
