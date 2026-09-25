import time
import asyncio
from contextlib import asynccontextmanager
from typing import Any, Callable, Optional
from functools import wraps


class LatencyTracker:
    """Lightweight latency tracker for AI request pipeline."""

    def __init__(self, request_id: str):
        self.request_id = request_id
        self.events: list[dict[str, Any]] = []
        self._stack: list[tuple[str, float]] = []
        self.t0 = time.perf_counter()

    def mark(self, name: str, metadata: Optional[dict] = None) -> None:
        """Mark an instantaneous event."""
        elapsed = (time.perf_counter() - self.t0) * 1000
        self.events.append({
            "type": "mark",
            "name": name,
            "time_ms": round(elapsed, 2),
            "metadata": metadata or {},
        })

    def start(self, name: str) -> None:
        """Start timing an operation."""
        elapsed = (time.perf_counter() - self.t0) * 1000
        self._stack.append((name, elapsed))
        self.events.append({
            "type": "start",
            "name": name,
            "time_ms": round(elapsed, 2),
        })

    def end(self, name: str, metadata: Optional[dict] = None) -> float:
        """End timing an operation and return duration in ms."""
        elapsed = (time.perf_counter() - self.t0) * 1000
        # Find matching start
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i][0] == name:
                start_time = self._stack.pop(i)[1]
                duration = round(elapsed - start_time, 2)
                self.events.append({
                    "type": "end",
                    "name": name,
                    "time_ms": round(elapsed, 2),
                    "duration_ms": duration,
                    "metadata": metadata or {},
                })
                return duration
        # No matching start found
        self.events.append({
            "type": "end",
            "name": name,
            "time_ms": round(elapsed, 2),
            "duration_ms": None,
            "metadata": metadata or {},
        })
        return 0.0

    @asynccontextmanager
    async def measure(self, name: str, metadata: Optional[dict] = None):
        """Context manager for measuring an async operation."""
        self.start(name)
        try:
            yield
        finally:
            self.end(name, metadata)

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of all measured operations."""
        total_ms = round((time.perf_counter() - self.t0) * 1000, 2)
        operations = {}
        for event in self.events:
            if event["type"] == "end" and event.get("duration_ms") is not None:
                name = event["name"]
                if name not in operations:
                    operations[name] = {
                        "count": 0,
                        "total_ms": 0,
                        "min_ms": float("inf"),
                        "max_ms": 0,
                    }
                op = operations[name]
                op["count"] += 1
                op["total_ms"] += event["duration_ms"]
                op["min_ms"] = min(op["min_ms"], event["duration_ms"])
                op["max_ms"] = max(op["max_ms"], event["duration_ms"])

        # Calculate averages
        for op in operations.values():
            op["avg_ms"] = round(op["total_ms"] / op["count"], 2)
            op["total_ms"] = round(op["total_ms"], 2)
            op["min_ms"] = round(op["min_ms"], 2)
            op["max_ms"] = round(op["max_ms"], 2)

        return {
            "request_id": self.request_id,
            "total_ms": total_ms,
            "operations": operations,
            "events": self.events,
        }

    def log_summary(self, logger_name: str = "ai-latency") -> None:
        """Log the summary using print (for simplicity)."""
        import logging
        logger = logging.getLogger(logger_name)
        summary = self.get_summary()
        # Always print to stdout for visibility - force flush
        print(f"[AI-LATENCY] request_total={summary['total_ms']}ms", flush=True)
        for name, op in summary["operations"].items():
            print(f"[AI-LATENCY] {name}={op['total_ms']}ms (count={op['count']}, avg={op['avg_ms']}ms)", flush=True)
        # Also log via logger if configured
        logger.info(f"[AI-LATENCY] request_total={summary['total_ms']}ms")
        for name, op in summary["operations"].items():
            logger.info(f"[AI-LATENCY] {name}={op['total_ms']}ms (count={op['count']}, avg={op['avg_ms']}ms)")
        
        # Also write to file for reliable capture
        try:
            with open("/tmp/ai_latency.log", "a") as f:
                f.write(f"[AI-LATENCY] request_total={summary['total_ms']}ms\n")
                for name, op in summary["operations"].items():
                    f.write(f"[AI-LATENCY] {name}={op['total_ms']}ms (count={op['count']}, avg={op['avg_ms']}ms)\n")
                f.write("---\n")
        except Exception:
            pass


# Global tracker registry for request-scoped tracking
_trackers: dict[str, LatencyTracker] = {}


def get_tracker(request_id: str) -> LatencyTracker:
    """Get or create a tracker for a request."""
    if request_id not in _trackers:
        _trackers[request_id] = LatencyTracker(request_id)
    return _trackers[request_id]


def clear_tracker(request_id: str) -> None:
    """Clear a tracker after logging."""
    _trackers.pop(request_id, None)


def measure_async(name: str, request_id: str, metadata: Optional[dict] = None):
    """Decorator for measuring async functions."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            tracker = get_tracker(request_id)
            tracker.start(name)
            try:
                result = await func(*args, **kwargs)
                tracker.end(name, metadata)
                return result
            except Exception as e:
                tracker.end(name, {**(metadata or {}), "error": str(e)})
                raise
        return wrapper
    return decorator


def measure_sync(name: str, request_id: str, metadata: Optional[dict] = None):
    """Decorator for measuring sync functions."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracker = get_tracker(request_id)
            tracker.start(name)
            try:
                result = func(*args, **kwargs)
                tracker.end(name, metadata)
                return result
            except Exception as e:
                tracker.end(name, {**(metadata or {}), "error": str(e)})
                raise
        return wrapper
    return decorator