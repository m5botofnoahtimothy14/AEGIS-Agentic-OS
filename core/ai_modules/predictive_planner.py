                                  
import logging

logger = logging.getLogger("SATURDAY.AI.Planner")

class PredictivePlanner:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.plans = []
        self.event_bus.subscribe("data_sync", self.update_plan)

    def update_plan(self, data):
        logger.info("Updating predictive plan based on new data.")
        if isinstance(data, dict):
            self.plans.append({"kind": "update", "data": data, "status": "pending"})
            self.plans = self.plans[-100:]
            self._project(data)
        return {"plan_count": len(self.plans)}

    def _project(self, data) -> None:
        try:
            import datetime
            from collections import Counter
            values = data.get("values")
            if isinstance(values, (list, tuple)) and values:
                deltas = []
                numeric = [float(v) for v in values if isinstance(v, (int, float))]
                for i in range(1, len(numeric)):
                    deltas.append(numeric[i] - numeric[i - 1])
                if deltas:
                    trend = sum(deltas) / len(deltas)
                    projection = numeric[-1] + trend
                    self.event_bus.publish("prediction", {
                        "trend": trend,
                        "projection": projection,
                        "window": len(numeric),
                        "updated_at": datetime.datetime.now().isoformat(),
                    })
        except Exception as e:
            logger.warning("Predictive projection failed", error=str(e))
