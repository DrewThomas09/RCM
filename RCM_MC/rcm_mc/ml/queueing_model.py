"""Queueing theory models for RCM operations analysis.

Models denial workqueues, coding backlogs, prior auth pipelines, and
A/R follow-up as queueing systems to estimate staffing needs, SLA
breach probability, and throughput capacity.

Uses M/M/c and Little's Law. References: Kleinrock, Queueing Systems;
Hillier & Lieberman, Introduction to Operations Research.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import factorial, exp, sqrt
from typing import Any, Dict, List, Optional


@dataclass
class QueueMetrics:
    """Steady-state queue metrics for an RCM workqueue."""
    queue_name: str
    arrival_rate: float  # items per day
    service_rate: float  # items per server per day
    n_servers: int
    utilization: float  # rho = lambda / (c * mu)
    avg_queue_length: float  # Lq
    avg_system_length: float  # L
    avg_wait_time: float  # Wq (days)
    avg_system_time: float  # W (days)
    prob_wait: float  # P(waiting > 0)
    sla_breach_prob: float  # P(wait > SLA target)
    recommended_servers: int
    bottleneck: bool


def _erlang_c(c: int, rho_total: float) -> float:
    """Erlang C formula: probability of queueing in M/M/c system."""
    if c <= 0 or rho_total <= 0:
        return 0
    a = rho_total  # total offered load
    if a / c >= 1:
        return 1.0  # system is overloaded

    sum_terms = sum(a ** k / factorial(k) for k in range(c))
    last_term = (a ** c / factorial(c)) * (c / (c - a))
    return last_term / (sum_terms + last_term)


def analyze_mmc_queue(
    name: str,
    arrival_rate: float,
    service_rate: float,
    n_servers: int,
    sla_days: float = 5.0,
) -> QueueMetrics:
    """M/M/c queue analysis for an RCM workqueue.

    Parameters
    ----------
    name : Queue name (e.g., "Denial Appeals", "Coding Backlog")
    arrival_rate : Items arriving per day (e.g., new denials/day)
    service_rate : Items processed per server per day
    n_servers : Number of workers (coders, appeal analysts, etc.)
    sla_days : Target turnaround time (SLA)
    """
    if service_rate <= 0 or n_servers <= 0:
        return QueueMetrics(
            queue_name=name, arrival_rate=arrival_rate, service_rate=service_rate,
            n_servers=n_servers, utilization=1.0, avg_queue_length=float("inf"),
            avg_system_length=float("inf"), avg_wait_time=float("inf"),
            avg_system_time=float("inf"), prob_wait=1.0, sla_breach_prob=1.0,
            recommended_servers=max(1, int(arrival_rate / service_rate) + 1),
            bottleneck=True,
        )

    rho = arrival_rate / (n_servers * service_rate)

    if rho >= 1:
        # System overloaded
        rec = int(arrival_rate / service_rate) + 1
        return QueueMetrics(
            queue_name=name, arrival_rate=arrival_rate, service_rate=service_rate,
            n_servers=n_servers, utilization=min(rho, 1.0),
            avg_queue_length=arrival_rate * 10,
            avg_system_length=arrival_rate * 10 + arrival_rate / service_rate,
            avg_wait_time=10, avg_system_time=10 + 1 / service_rate,
            prob_wait=1.0, sla_breach_prob=1.0,
            recommended_servers=rec, bottleneck=True,
        )

    rho_total = arrival_rate / service_rate
    p_wait = _erlang_c(n_servers, rho_total)

    # Average queue length (Lq)
    lq = p_wait * rho / (1 - rho)

    # Average wait in queue (Wq) — Little's Law
    wq = lq / arrival_rate if arrival_rate > 0 else 0

    # Average time in system (W)
    w = wq + 1 / service_rate

    # Average number in system (L) — Little's Law
    l = arrival_rate * w

    # SLA breach probability: P(wait > sla_days)
    if wq > 0:
        # Exponential approximation for wait distribution
        sla_breach = p_wait * exp(-n_servers * service_rate * (1 - rho) * sla_days) if rho < 1 else 1.0
    else:
        sla_breach = 0

    # Recommended servers for < 10% SLA breach
    rec = n_servers
    for test_c in range(n_servers, n_servers + 20):
        test_rho = arrival_rate / (test_c * service_rate)
        if test_rho >= 1:
            continue
        test_rho_total = arrival_rate / service_rate
        test_pw = _erlang_c(test_c, test_rho_total)
        test_breach = test_pw * exp(-test_c * service_rate * (1 - test_rho) * sla_days) if test_rho < 1 else 1
        if test_breach < 0.10:
            rec = test_c
            break
    else:
        rec = n_servers + 10

    return QueueMetrics(
        queue_name=name,
        arrival_rate=round(arrival_rate, 1),
        service_rate=round(service_rate, 1),
        n_servers=n_servers,
        utilization=round(min(rho, 1.0), 3),
        avg_queue_length=round(lq, 1),
        avg_system_length=round(l, 1),
        avg_wait_time=round(wq, 2),
        avg_system_time=round(w, 2),
        prob_wait=round(p_wait, 3),
        sla_breach_prob=round(min(1, max(0, sla_breach)), 3),
        recommended_servers=rec,
        bottleneck=rho > 0.85,
    )


def analyze_rcm_operations(
    daily_denials: float = 50,
    denial_analysts: int = 5,
    daily_coding_volume: float = 200,
    coders: int = 8,
    daily_auth_requests: float = 30,
    auth_staff: int = 3,
    daily_ar_followups: float = 100,
    ar_staff: int = 6,
) -> List[QueueMetrics]:
    """Analyze all RCM workqueues as a system."""
    queues = [
        analyze_mmc_queue(
            "Denial Appeals", daily_denials,
            service_rate=12, n_servers=denial_analysts, sla_days=30,
        ),
        analyze_mmc_queue(
            "Medical Coding", daily_coding_volume,
            service_rate=30, n_servers=coders, sla_days=3,
        ),
        analyze_mmc_queue(
            "Prior Authorization", daily_auth_requests,
            service_rate=15, n_servers=auth_staff, sla_days=2,
        ),
        analyze_mmc_queue(
            "A/R Follow-Up", daily_ar_followups,
            service_rate=20, n_servers=ar_staff, sla_days=7,
        ),
    ]
    return queues


def littles_law_analysis(
    avg_inventory: float,
    throughput: float,
) -> Dict[str, float]:
    """Apply Little's Law: L = λW → W = L/λ.

    Given average backlog size and daily throughput, compute
    average cycle time and related metrics.
    """
    if throughput <= 0:
        return {"avg_cycle_time": float("inf"), "backlog_days": float("inf"),
                "throughput_per_day": 0, "inventory": avg_inventory}

    cycle_time = avg_inventory / throughput
    return {
        "avg_cycle_time": round(cycle_time, 1),
        "backlog_days": round(avg_inventory / throughput, 1),
        "throughput_per_day": round(throughput, 1),
        "inventory": round(avg_inventory, 0),
    }
