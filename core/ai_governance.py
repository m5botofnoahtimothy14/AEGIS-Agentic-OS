import json
import logging
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger("SATURDAY.AIGovernance")

class RiskLevel(Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ActionCategory(Enum):
    SYSTEM_CONTROL = "system_control"
    FILE_OPERATION = "file_operation"
    NETWORK_ACCESS = "network_access"
    PROCESS_MANAGEMENT = "process_management"
    USER_DATA_ACCESS = "user_data_access"
    EXTERNAL_COMMUNICATION = "external_communication"
    SELF_MODIFICATION = "self_modification"
    FINANCIAL = "financial"
    PRIVILEGE_ESCALATION = "privilege_escalation"

@dataclass
class GovernanceRule:
    id: str
    name: str
    description: str
    category: ActionCategory
    risk_level: RiskLevel
    requires_confirmation: bool
    requires_admin: bool
    blocked_keywords: List[str] = field(default_factory=list)
    allowed_contexts: List[str] = field(default_factory=list)
    max_frequency_per_minute: int = 0
    enabled: bool = True

@dataclass
class ActionRequest:
    action: str
    category: ActionCategory
    parameters: Dict[str, Any]
    context: str
    timestamp: float = field(default_factory=time.time)
    user_confirmed: bool = False
    admin_approved: bool = False

@dataclass
class GovernanceDecision:
    allowed: bool
    reason: str
    risk_level: RiskLevel
    requires_confirmation: bool
    requires_admin: bool
    alternative: Optional[str] = None
    audit_id: str = ""

class AIGovernanceEngine:
    def __init__(self, event_bus=None, config_path: str = None):
        self.event_bus = event_bus
        self.config_path = config_path or "data/governance_rules.json"
        self.rules: Dict[str, GovernanceRule] = {}
        self.action_history: List[Dict] = []
        self.pending_confirmations: Dict[str, ActionRequest] = {}
        self._action_counts: Dict[str, List[float]] = {}
        
        self._load_default_rules()
        self._load_custom_rules()
        
        if self.event_bus:
            self.event_bus.subscribe("governance_request", self._handle_request)
            self.event_bus.subscribe("governance_confirm", self._handle_confirmation)

    def _load_default_rules(self):
        """Load hardcoded default governance rules -- comprehensive ethical coverage."""
        defaults = [
            # ── SYSTEM CONTROL ──
            GovernanceRule(
                id="sys_shutdown",
                name="System Shutdown/Restart",
                description="Shutting down or restarting the system",
                category=ActionCategory.SYSTEM_CONTROL,
                risk_level=RiskLevel.HIGH,
                requires_confirmation=True,
                requires_admin=True,
                blocked_keywords=["shutdown", "restart", "reboot", "poweroff"],
            ),
            GovernanceRule(
                id="sys_sleep",
                name="System Sleep/Hibernate",
                description="Putting system to sleep or hibernate",
                category=ActionCategory.SYSTEM_CONTROL,
                risk_level=RiskLevel.MEDIUM,
                requires_confirmation=True,
                requires_admin=False,
            ),
            GovernanceRule(
                id="sys_lock",
                name="Lock Workstation",
                description="Locking the workstation screen",
                category=ActionCategory.SYSTEM_CONTROL,
                risk_level=RiskLevel.LOW,
                requires_confirmation=False,
                requires_admin=False,
            ),
            # ── FILE OPERATIONS ──
            GovernanceRule(
                id="file_delete_system",
                name="Delete System Files",
                description="Deleting files in system directories",
                category=ActionCategory.FILE_OPERATION,
                risk_level=RiskLevel.CRITICAL,
                requires_confirmation=True,
                requires_admin=True,
                blocked_keywords=["system32", "windows", "program files", "syswow64"],
            ),
            GovernanceRule(
                id="file_delete_user",
                name="Delete User Files",
                description="Deleting user documents, photos, etc.",
                category=ActionCategory.FILE_OPERATION,
                risk_level=RiskLevel.HIGH,
                requires_confirmation=True,
                requires_admin=False,
            ),
            GovernanceRule(
                id="file_write_sensitive",
                name="Write to Sensitive Locations",
                description="Writing to system/config directories",
                category=ActionCategory.FILE_OPERATION,
                risk_level=RiskLevel.HIGH,
                requires_confirmation=True,
                requires_admin=True,
            ),
            GovernanceRule(
                id="file_read_protected",
                name="Read Protected Files",
                description="Accessing SSH keys, credentials, wallets",
                category=ActionCategory.FILE_OPERATION,
                risk_level=RiskLevel.CRITICAL,
                requires_confirmation=True,
                requires_admin=True,
                blocked_keywords=["password", "credential", "secret", ".ssh", ".gnupg", "wallet", "id_rsa", "credentials.json"],
            ),
            # ── NETWORK ACCESS ──
            GovernanceRule(
                id="net_external",
                name="External Network Connections",
                description="Making outbound network connections",
                category=ActionCategory.NETWORK_ACCESS,
                risk_level=RiskLevel.MEDIUM,
                requires_confirmation=False,
                requires_admin=False,
                max_frequency_per_minute=30,
            ),
            GovernanceRule(
                id="net_download_executable",
                name="Download & Execute",
                description="Downloading and running executables",
                category=ActionCategory.NETWORK_ACCESS,
                risk_level=RiskLevel.CRITICAL,
                requires_confirmation=True,
                requires_admin=True,
                blocked_keywords=["download", "install", "setup", ".exe", ".msi"],
            ),
            GovernanceRule(
                id="net_port_scan",
                name="Port Scanning",
                description="Scanning remote ports",
                category=ActionCategory.NETWORK_ACCESS,
                risk_level=RiskLevel.MEDIUM,
                requires_confirmation=False,
                requires_admin=False,
                max_frequency_per_minute=5,
            ),
            GovernanceRule(
                id="net_email",
                name="Send Email",
                description="Sending emails via SMTP",
                category=ActionCategory.EXTERNAL_COMMUNICATION,
                risk_level=RiskLevel.MEDIUM,
                requires_confirmation=True,
                requires_admin=False,
            ),
            # ── PROCESS MANAGEMENT ──
            GovernanceRule(
                id="proc_kill_critical",
                name="Kill Critical Processes",
                description="Terminating system-critical processes",
                category=ActionCategory.PROCESS_MANAGEMENT,
                risk_level=RiskLevel.CRITICAL,
                requires_confirmation=True,
                requires_admin=True,
                blocked_keywords=["system", "svchost", "lsass", "csrss", "winlogon", "explorer", "dwm"],
            ),
            GovernanceRule(
                id="proc_kill_user",
                name="Kill User Processes",
                description="Terminating user applications",
                category=ActionCategory.PROCESS_MANAGEMENT,
                risk_level=RiskLevel.MEDIUM,
                requires_confirmation=True,
                requires_admin=False,
            ),
            GovernanceRule(
                id="proc_mass_kill",
                name="Mass Process Termination",
                description="Killing multiple processes at once",
                category=ActionCategory.PROCESS_MANAGEMENT,
                risk_level=RiskLevel.HIGH,
                requires_confirmation=True,
                requires_admin=True,
            ),
            # ── USER DATA ACCESS ──
            GovernanceRule(
                id="data_read_private",
                name="Read Private User Data",
                description="Accessing passwords, keys, personal docs",
                category=ActionCategory.USER_DATA_ACCESS,
                risk_level=RiskLevel.HIGH,
                requires_confirmation=True,
                requires_admin=False,
                blocked_keywords=["password", "credential", "secret", "key", ".ssh", ".gnupg", "wallet"],
            ),
            GovernanceRule(
                id="data_clipboard_access",
                name="Clipboard Access",
                description="Reading clipboard contents",
                category=ActionCategory.USER_DATA_ACCESS,
                risk_level=RiskLevel.LOW,
                requires_confirmation=False,
                requires_admin=False,
            ),
            # ── EXTERNAL COMMUNICATION ──
            GovernanceRule(
                id="comm_external_ai",
                name="External AI Communication",
                description="Sending data to external AI services",
                category=ActionCategory.EXTERNAL_COMMUNICATION,
                risk_level=RiskLevel.MEDIUM,
                requires_confirmation=False,
                requires_admin=False,
                max_frequency_per_minute=10,
            ),
            GovernanceRule(
                id="comm_notification",
                name="Send Notifications",
                description="Sending toast notifications to user",
                category=ActionCategory.EXTERNAL_COMMUNICATION,
                risk_level=RiskLevel.LOW,
                requires_confirmation=False,
                requires_admin=False,
            ),
            # ── SELF MODIFICATION ──
            GovernanceRule(
                id="self_modify_code",
                name="Self Code Modification",
                description="Modifying own code or configuration",
                category=ActionCategory.SELF_MODIFICATION,
                risk_level=RiskLevel.HIGH,
                requires_confirmation=True,
                requires_admin=True,
            ),
            GovernanceRule(
                id="self_rewrite_config",
                name="Rewrite Configuration",
                description="Modifying SATURDAY config files",
                category=ActionCategory.SELF_MODIFICATION,
                risk_level=RiskLevel.HIGH,
                requires_confirmation=True,
                requires_admin=True,
            ),
            # ── FINANCIAL ──
            GovernanceRule(
                id="financial_action",
                name="Financial Transactions",
                description="Any financial or payment action",
                category=ActionCategory.FINANCIAL,
                risk_level=RiskLevel.CRITICAL,
                requires_confirmation=True,
                requires_admin=True,
                blocked_keywords=["payment", "purchase", "buy", "transfer", "crypto", "wallet", "send money"],
            ),
            # ── PRIVILEGE ESCALATION ──
            GovernanceRule(
                id="priv_escalation",
                name="Privilege Escalation",
                description="Attempting to gain admin/elevated privileges",
                category=ActionCategory.PRIVILEGE_ESCALATION,
                risk_level=RiskLevel.CRITICAL,
                requires_confirmation=True,
                requires_admin=True,
                blocked_keywords=["runas", "sudo", "admin", "elevate", "uac bypass"],
            ),
            # ── ETHICAL GOVERNANCE RULES (SATURDAY-specific) ──
            GovernanceRule(
                id="eth_no_harm",
                name="No Harm to Humans",
                description="Never execute commands that could physically harm humans or damage property",
                category=ActionCategory.SYSTEM_CONTROL,
                risk_level=RiskLevel.CRITICAL,
                requires_confirmation=True,
                requires_admin=True,
                blocked_keywords=["harm", "destroy", "weapon", "attack", "exploit", "inject", "bomb"],
            ),
            GovernanceRule(
                id="eth_privacy",
                name="Privacy by Default",
                description="Never access cameras, microphones, or location without explicit consent",
                category=ActionCategory.USER_DATA_ACCESS,
                risk_level=RiskLevel.HIGH,
                requires_confirmation=True,
                requires_admin=False,
                blocked_keywords=["camera", "microphone", "location", "track", "surveillance", "spy"],
            ),
            GovernanceRule(
                id="eth_transparency",
                name="Transparency",
                description="Always explain what a command will do before execution",
                category=ActionCategory.SYSTEM_CONTROL,
                risk_level=RiskLevel.MEDIUM,
                requires_confirmation=False,
                requires_admin=False,
            ),
            GovernanceRule(
                id="eth_no_malware",
                name="No Malware/Exploits",
                description="Never create, distribute, or execute malware",
                category=ActionCategory.NETWORK_ACCESS,
                risk_level=RiskLevel.CRITICAL,
                requires_confirmation=True,
                requires_admin=True,
                blocked_keywords=["malware", "virus", "ransomware", "trojan", "backdoor", "rootkit", "keylogger"],
            ),
            GovernanceRule(
                id="eth_no_social_eng",
                name="No Social Engineering",
                description="Never impersonate humans or manipulate people",
                category=ActionCategory.EXTERNAL_COMMUNICATION,
                risk_level=RiskLevel.CRITICAL,
                requires_confirmation=True,
                requires_admin=True,
                blocked_keywords=["impersonate", "phish", "deceive", "spoof", "fake identity"],
            ),
            GovernanceRule(
                id="eth_data_integrity",
                name="Data Integrity",
                description="Never corrupt, encrypt for ransom, or destroy user data",
                category=ActionCategory.FILE_OPERATION,
                risk_level=RiskLevel.CRITICAL,
                requires_confirmation=True,
                requires_admin=True,
                blocked_keywords=["encrypt files", "ransom", "corrupt", "wipe", "format"],
            ),
            GovernanceRule(
                id="eth_no_unauth_access",
                name="No Unauthorized Access",
                description="Never attempt to access other users' accounts or systems",
                category=ActionCategory.NETWORK_ACCESS,
                risk_level=RiskLevel.CRITICAL,
                requires_confirmation=True,
                requires_admin=True,
                blocked_keywords=["brute force", "crack", "hack", "unauthorized access"],
            ),
            GovernanceRule(
                id="eth_audit_trail",
                name="Audit Trail",
                description="All actions must be logged for accountability",
                category=ActionCategory.SYSTEM_CONTROL,
                risk_level=RiskLevel.LOW,
                requires_confirmation=False,
                requires_admin=False,
            ),
            GovernanceRule(
                id="eth_abort_uncertainty",
                name="Abort on Uncertainty",
                description="If unsure about safety, ask the user before proceeding",
                category=ActionCategory.SYSTEM_CONTROL,
                risk_level=RiskLevel.MEDIUM,
                requires_confirmation=True,
                requires_admin=False,
            ),
            GovernanceRule(
                id="eth_no_destructive",
                name="No Destructive Commands",
                description="Never run rm -rf, format, or similar destructive commands",
                category=ActionCategory.FILE_OPERATION,
                risk_level=RiskLevel.CRITICAL,
                requires_confirmation=True,
                requires_admin=True,
                blocked_keywords=["rm -rf", "format", "rd /s", "del /s", "cipher /w"],
            ),
            GovernanceRule(
                id="eth_credential_safety",
                name="Credential Safety",
                description="Never log, transmit, or store credentials in plaintext",
                category=ActionCategory.USER_DATA_ACCESS,
                risk_level=RiskLevel.CRITICAL,
                requires_confirmation=True,
                requires_admin=True,
                blocked_keywords=["log password", "echo password", "print secret", "send token"],
            ),
        ]
        for rule in defaults:
            self.rules[rule.id] = rule

    def _load_custom_rules(self):
        """Load custom rules from config file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                for rule_data in data.get("rules", []):
                    rule = GovernanceRule(
                        id=rule_data["id"],
                        name=rule_data["name"],
                        description=rule_data["description"],
                        category=ActionCategory(rule_data["category"]),
                        risk_level=RiskLevel(rule_data["risk_level"]),
                        requires_confirmation=rule_data["requires_confirmation"],
                        requires_admin=rule_data["requires_admin"],
                        blocked_keywords=rule_data.get("blocked_keywords", []),
                        allowed_contexts=rule_data.get("allowed_contexts", []),
                        max_frequency_per_minute=rule_data.get("max_frequency_per_minute", 0),
                        enabled=rule_data.get("enabled", True),
                    )
                    self.rules[rule.id] = rule
        except Exception as e:
            logger.warning(f"Failed to load custom governance rules: {e}")

    def _save_custom_rules(self):
        """Save custom rules to config file"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            data = {"rules": []}
            for rule in self.rules.values():
                data["rules"].append({
                    "id": rule.id,
                    "name": rule.name,
                    "description": rule.description,
                    "category": rule.category.value,
                    "risk_level": rule.risk_level.value,
                    "requires_confirmation": rule.requires_confirmation,
                    "requires_admin": rule.requires_admin,
                    "blocked_keywords": rule.blocked_keywords,
                    "allowed_contexts": rule.allowed_contexts,
                    "max_frequency_per_minute": rule.max_frequency_per_minute,
                    "enabled": rule.enabled,
                })
            with open(self.config_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save governance rules: {e}")

    def evaluate(self, request: ActionRequest) -> GovernanceDecision:
        """Evaluate an action request against governance rules"""
        audit_id = f"gov_{int(time.time() * 1000)}_{id(request)}"
        
        # Find matching rule
        matched_rule = None
        for rule in self.rules.values():
            if not rule.enabled:
                continue
            if rule.category == request.category:
                # Check keyword matches
                action_lower = request.action.lower()
                params_str = json.dumps(request.parameters).lower()
                full_text = action_lower + " " + params_str
                
                if any(kw in full_text for kw in rule.blocked_keywords):
                    matched_rule = rule
                    break
                
                # Check frequency limit
                if rule.max_frequency_per_minute > 0:
                    now = time.time()
                    if rule.id not in self._action_counts:
                        self._action_counts[rule.id] = []
                    self._action_counts[rule.id] = [t for t in self._action_counts[rule.id] if now - t < 60]
                    if len(self._action_counts[rule.id]) >= rule.max_frequency_per_minute:
                        return GovernanceDecision(
                            allowed=False,
                            reason=f"Rate limit exceeded for {rule.name} (max {rule.max_frequency_per_minute}/min)",
                            risk_level=rule.risk_level,
                            requires_confirmation=False,
                            requires_admin=False,
                            audit_id=audit_id
                        )
        
        if not matched_rule:
            # No specific rule matched - allow with logging
            self._log_action(request, audit_id, True, "No matching governance rule")
            return GovernanceDecision(
                allowed=True,
                reason="No governing rule matched - action permitted",
                risk_level=RiskLevel.NONE,
                requires_confirmation=False,
                requires_admin=False,
                audit_id=audit_id
            )
        
        # Check frequency for matched rule
        if matched_rule.max_frequency_per_minute > 0:
            now = time.time()
            if matched_rule.id not in self._action_counts:
                self._action_counts[matched_rule.id] = []
            self._action_counts[matched_rule.id] = [t for t in self._action_counts[matched_rule.id] if now - t < 60]
            self._action_counts[matched_rule.id].append(now)
        
        # Determine if allowed
        if matched_rule.requires_admin and not request.admin_approved:
            return GovernanceDecision(
                allowed=False,
                reason=f"Requires admin approval: {matched_rule.name}",
                risk_level=matched_rule.risk_level,
                requires_confirmation=True,
                requires_admin=True,
                audit_id=audit_id
            )
        
        if matched_rule.requires_confirmation and not request.user_confirmed:
            # Store for confirmation
            self.pending_confirmations[audit_id] = request
            return GovernanceDecision(
                allowed=False,
                reason=f"Requires user confirmation: {matched_rule.name}",
                risk_level=matched_rule.risk_level,
                requires_confirmation=True,
                requires_admin=matched_rule.requires_admin,
                alternative="Say 'confirm' to proceed or 'cancel' to abort",
                audit_id=audit_id
            )
        
        # All checks passed
        self._log_action(request, audit_id, True, f"Approved by governance rule: {matched_rule.name}")
        return GovernanceDecision(
            allowed=True,
            reason=f"Approved by governance rule: {matched_rule.name}",
            risk_level=matched_rule.risk_level,
            requires_confirmation=False,
            requires_admin=False,
            audit_id=audit_id
        )

    def _log_action(self, request: ActionRequest, audit_id: str, allowed: bool, reason: str):
        """Log action for audit trail"""
        entry = {
            "audit_id": audit_id,
            "timestamp": datetime.now().isoformat(),
            "action": request.action,
            "category": request.category.value,
            "parameters": request.parameters,
            "context": request.context,
            "allowed": allowed,
            "reason": reason,
            "risk_level": "unknown"
        }
        self.action_history.append(entry)
        if len(self.action_history) > 10000:
            self.action_history = self.action_history[-5000:]
        
        if self.event_bus:
            self.event_bus.publish("governance_audit", entry)

    def _handle_request(self, data: Dict):
        """Handle governance request from event bus"""
        request = ActionRequest(
            action=data.get("action", ""),
            category=ActionCategory(data.get("category", "system_control")),
            parameters=data.get("parameters", {}),
            context=data.get("context", "voice_command"),
            user_confirmed=data.get("user_confirmed", False),
            admin_approved=data.get("admin_approved", False),
        )
        decision = self.evaluate(request)
        
        if self.event_bus:
            self.event_bus.publish("governance_decision", {
                "request_id": data.get("request_id"),
                "allowed": decision.allowed,
                "reason": decision.reason,
                "risk_level": decision.risk_level.value,
                "requires_confirmation": decision.requires_confirmation,
                "requires_admin": decision.requires_admin,
                "alternative": decision.alternative,
                "audit_id": decision.audit_id,
            })

    def _handle_confirmation(self, data: Dict):
        """Handle user confirmation for pending action"""
        audit_id = data.get("audit_id")
        confirmed = data.get("confirmed", False)
        
        if audit_id in self.pending_confirmations:
            request = self.pending_confirmations.pop(audit_id)
            request.user_confirmed = confirmed
            decision = self.evaluate(request)
            
            if self.event_bus:
                self.event_bus.publish("governance_decision", {
                    "request_id": data.get("request_id"),
                    "allowed": decision.allowed,
                    "reason": decision.reason,
                    "audit_id": audit_id,
                })

    def get_audit_log(self, limit: int = 100) -> List[Dict]:
        """Get recent audit log entries"""
        return self.action_history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get governance statistics"""
        total = len(self.action_history)
        allowed = sum(1 for e in self.action_history if e["allowed"])
        blocked = total - allowed
        by_category = {}
        by_risk = {}
        for entry in self.action_history:
            cat = entry.get("category", "unknown")
            by_category[cat] = by_category.get(cat, 0) + 1
        return {
            "total_actions": total,
            "allowed": allowed,
            "blocked": blocked,
            "block_rate": round(blocked / max(1, total) * 100, 1),
            "by_category": by_category,
            "pending_confirmations": len(self.pending_confirmations),
            "active_rules": len([r for r in self.rules.values() if r.enabled]),
        }


import os
# Global instance
_governance_engine = None

def get_governance_engine(event_bus=None) -> AIGovernanceEngine:
    global _governance_engine
    if _governance_engine is None:
        _governance_engine = AIGovernanceEngine(event_bus)
    return _governance_engine