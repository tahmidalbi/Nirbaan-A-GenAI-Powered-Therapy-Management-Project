"""End-to-end latency and routing accuracy of the patient-facing agent graph.

Usage: python evaluation/latency_benchmark.py [route ...]
Runs every message in data/latency_messages.json once, sequentially, for the
workspace-A test patient (whose therapist knowledge base holds the OCD book).
Naming routes (e.g. human_escalation) runs only those messages and writes
results with the route names as a filename suffix.
"""
import json
import os
import platform
import statistics
import sys
import time
from collections import defaultdict

import common

common.configure()


def percentile(values: list, p: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(p * (len(ordered) - 1)))]


def run_message(graph, patient_id: int, therapist_id: int, message: str) -> dict:
    state = {"patient_id": patient_id, "therapist_id": therapist_id,
             "user_message": message, "recent_chat_history": []}
    start = last = time.perf_counter()
    steps, route = [], None
    for namespace, update in graph.stream(state, stream_mode="updates", subgraphs=True):
        now = time.perf_counter()
        for node, value in update.items():
            steps.append({"node": node, "nested": bool(namespace), "ms": (now - last) * 1000})
            if node == "router" and not namespace:
                route = (value or {}).get("route")
        last = now
    return {"route": route, "total_ms": (time.perf_counter() - start) * 1000, "steps": steps}


if __name__ == "__main__":
    common.quiet_sql()
    ids = common.ids_by_workspace()["A"]
    from app.NirbaanAIPatient.CentralAgent.graph import central_graph

    messages = json.loads((common.DATA_DIR / "latency_messages.json").read_text(encoding="utf-8"))
    selected = sys.argv[1:]
    if selected:
        messages = {route: texts for route, texts in messages.items() if route in selected}
    suffix = "_" + "_".join(selected) if selected else ""
    runs = []
    for expected, texts in messages.items():
        for text in texts:
            result = run_message(central_graph, ids["patient_id"], ids["therapist_id"], text)
            result.update(expected=expected, message=text)
            runs.append(result)
            print(f"{expected:>16} -> {str(result['route']):>16}  {result['total_ms']:8.0f} ms")

    summary = {"by_actual_route": {}, "node_ms_median": {}}
    for route in ("psychoeducation", "support", "human_escalation"):
        totals = [r["total_ms"] for r in runs if r["route"] == route]
        if totals:
            summary["by_actual_route"][route] = {
                "runs": len(totals),
                "median_ms": statistics.median(totals),
                "p95_ms": percentile(totals, 0.95),
                "mean_ms": statistics.mean(totals),
            }
    node_times = defaultdict(list)
    for r in runs:
        for s in r["steps"]:
            if s["nested"] or s["node"] == "router":
                node_times[s["node"]].append(s["ms"])
    summary["node_ms_median"] = {n: statistics.median(v) for n, v in sorted(node_times.items())}

    confusion = defaultdict(lambda: defaultdict(int))
    for r in runs:
        confusion[r["expected"]][str(r["route"])] += 1
    summary["routing"] = {
        "accuracy": statistics.mean(r["route"] == r["expected"] for r in runs),
        "escalation_recall": statistics.mean(
            r["route"] == "human_escalation" for r in runs if r["expected"] == "human_escalation"),
        "confusion": {k: dict(v) for k, v in confusion.items()},
    }
    escalation_runs = [r for r in runs if r["route"] == "human_escalation"]
    summary["escalation_alerts_sent"] = sum(
        any(s["node"] == "send_to_ep_group" for s in r["steps"]) for r in escalation_runs)
    summary["escalation_runs"] = len(escalation_runs)
    psycho = [r for r in runs if r["route"] == "psychoeducation"]
    summary["psychoeducation_web_fallback_rate"] = (
        statistics.mean(any(s["node"] == "web_search" for s in r["steps"]) for r in psycho) if psycho else None)
    all_totals = [r["total_ms"] for r in runs]
    summary["sequential_throughput_messages_per_minute"] = 60000 / statistics.mean(all_totals)
    summary["environment"] = {
        "machine": platform.platform(), "processor": platform.processor(),
        "python": platform.python_version(),
        "chat_model": os.environ.get("OPENAI_CHAT_MODEL"),
        "embedding_model": os.environ.get("EMBEDDING_MODEL", "text-embedding-3-large"),
    }

    (common.RESULTS_DIR / f"latency_runs{suffix}.json").write_text(json.dumps(runs, indent=2), encoding="utf-8")
    (common.RESULTS_DIR / f"latency_results{suffix}.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
