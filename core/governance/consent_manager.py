class ConsentManager:
    def __init__(self):
        self.consent_log = {}
        self.revocation_log = {}
        self.expiry_log = {}
        self.default_expiry_days = 365

    def give_consent(self, user, scope, expiry_days=None):
        expiry = expiry_days or self.default_expiry_days
        self.consent_log.setdefault(user, set()).add(scope)
        self.expiry_log[user] = expiry
        self._audit("consent_given", user=user, scope=scope, expiry_days=expiry)

    def revoke_consent(self, user, scope):
        if user in self.consent_log and scope in self.consent_log[user]:
            self.consent_log[user].discard(scope)
            self.revocation_log.setdefault(user, set()).add(scope)
            self._audit("consent_revoked", user=user, scope=scope)
            return True
        return False

    def has_consent(self, user, scope):
        if user not in self.consent_log:
            return False
        if scope not in self.consent_log[user]:
            return False
        # Check expiry
        expiry = self.expiry_log.get(user)
        if expiry and time.time() > expiry * 86400:
            self.revoke_consent(user, scope)
            return False
        return True

    def list_consents(self, user):
        return dict(self.consent_log.get(user, []))

    def _audit(self, action, **kwargs):
        import structlog
        logger = structlog.get_logger("SATURDAY.Consent")
        logger.info("consent_action", action=action, **kwargs)