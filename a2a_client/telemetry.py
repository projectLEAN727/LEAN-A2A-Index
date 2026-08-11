import time
import json
from typing import Dict, Any, Optional


class TelemetryMetrics:
    def __init__(self, scenario_name: str, payload_id: str):
        self.scenario_name = scenario_name
        self.payload_id = payload_id
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.step_starts: Dict[str, float] = {}
        self.step_latencies: Dict[str, float] = {}
        self.gas_used_mnt: str = "0"
        self.payment_amount_mnt: float = 0.0
        self.treasury_fee_mnt: float = 0.0
        self.status: str = "IN_PROGRESS"
        self.error_message: Optional[str] = None

    def start_step(self, step_name: str):
        self.step_starts[step_name] = time.time()

    def end_step(self, step_name: str):
        if step_name in self.step_starts:
            latency = (time.time() - self.step_starts[step_name]) * 1000.0
            self.step_latencies[step_name] = round(latency, 2)

    def set_onchain_metrics(self, gas_used_mnt: float, payment_amount_mnt: float, treasury_fee_mnt: float):
        self.gas_used_mnt = f"{gas_used_mnt:.6f}"
        self.payment_amount_mnt = payment_amount_mnt
        self.treasury_fee_mnt = treasury_fee_mnt

    def finish(self, status: str = "SUCCESS", error_message: Optional[str] = None):
        self.end_time = time.time()
        self.status = status
        self.error_message = error_message

    def to_dict(self) -> Dict[str, Any]:
        total_latency = (
            (self.end_time - self.start_time) * 1000.0
            if self.end_time
            else (time.time() - self.start_time) * 1000.0
        )
        data = {
            "timestamp": int(self.start_time),
            "scenario": self.scenario_name,
            "payload_id": self.payload_id,
            "total_latency_ms": round(total_latency, 2),
            "latencies_ms": self.step_latencies,
            "gas_used_mnt": self.gas_used_mnt,
            "payment_amount_mnt": self.payment_amount_mnt,
            "treasury_fee_mnt": self.treasury_fee_mnt,
            "status": self.status,
        }
        if self.error_message:
            data["error_message"] = self.error_message
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


class TelemetryLogger:
    def __init__(self):
        self.current_metrics: Optional[TelemetryMetrics] = None

    def start_scenario(self, scenario_name: str, payload_id: str) -> TelemetryMetrics:
        self.current_metrics = TelemetryMetrics(scenario_name, payload_id)
        return self.current_metrics

    def get_metrics(self) -> Optional[TelemetryMetrics]:
        return self.current_metrics


# Single global logger instance for convenience
global_telemetry = TelemetryLogger()
