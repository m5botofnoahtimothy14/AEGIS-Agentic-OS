                             
import logging

logger = logging.getLogger("SATURDAY.AI.IssueHandler")

class IssueHandler:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.issues = []
        self.event_bus.subscribe("security_alert", self.triage_issue)

    def triage_issue(self, data):
        logger.warning(f"Triaging system issue: {data}")
        severity, summary = self._assess(data)
        issue = {
            "severity": severity,
            "summary": summary,
            "source": data if isinstance(data, dict) else {"raw": data},
            "status": "open",
        }
        self.issues.append(issue)
        self.issues = self.issues[-100:]
        if severity == "critical":
            self.event_bus.publish("critical_issue", issue)
        return issue

    def _assess(self, data) -> tuple:
        if not isinstance(data, dict):
            return "medium", "Issue reported without structured details"
        alert_type = str(data.get("type", "")).lower()
        critical_types = {"breach", "intrusion", "unauthorized", "malware", "ransomware"}
        if alert_type in critical_types:
            return "critical", f"Critical security event: {alert_type}"
        if "potential" in alert_type or alert_type in {"suspicious", "warning"}:
            return "medium", f"Potential issue: {alert_type}"
        return "low", f"Advisory event: {alert_type or 'unspecified'}"
