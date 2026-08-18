class BiometricPolicy:
    def __init__(self):
        self.allowed_users = set()
        self.biometric_data = {}  # user_id -> encrypted template hash
        self.retention_days = 90
        self.access_log = []
        self.max_access_log = 1000

    def register_user(self, user_id, biometric_template_hash):
        self.allowed_users.add(user_id)
        self.biometric_data[user_id] = biometric_template_hash
        self._audit("biometric_registered", user_id=user_id)

    def unregister_user(self, user_id):
        self.allowed_users.discard(user_id)
        self.biometric_data.pop(user_id, None)
        self._audit("biometric_unregistered", user_id=user_id)

    def is_allowed(self, user_id):
        allowed = user_id in self.allowed_users
        self._audit("biometric_check", user_id=user_id, allowed=allowed)
        return allowed

    def store_biometric_data(self, user_id, template_hash):
        if user_id in self.allowed_users:
            self.biometric_data[user_id] = template_hash
            self._audit("biometric_stored", user_id=user_id)

    def remove_biometric_data(self, user_id):
        if user_id in self.allowed_users:
            self.biometric_data.pop(user_id, None)
            self._audit("biometric_removed", user_id=user_id)

    def set_retention(self, days):
        self.retention_days = days
        self._audit("retention_set", days=days)

    def _purge_expired(self):
        cutoff = time.time() - (self.retention_days * 86400)
        expired_users = [
            uid for uid, ts in self.access_log
            if ts < cutoff
        ]
        for uid in expired_users:
            self.access_log = [a for a in self.access_log if a[0] != uid]
        self._audit("access_purged", count=len(expired_users))

    def _audit(self, action, **kwargs):
        import structlog
        logger = structlog.get_logger("SATURDAY.Biometric")
        logger.info("biometric_action", action=action, **kwargs)