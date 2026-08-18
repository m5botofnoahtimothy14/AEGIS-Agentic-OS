class NotificationRouter:
    def __init__(self):
        self.routes = {}
        self.priority_queues = {}
        self.default_handler = None
        self.rate_limiter = {}

    def register_route(self, source, handler, priority=1):
        self.routes[source] = {"handler": handler, "priority": priority}
        if priority not in self.priority_queues:
            self.priority_queues[priority] = []
        self.priority_queues[priority].append(source)

    def set_default_handler(self, handler):
        self.default_handler = handler

    async def route(self, source, payload):
        if source in self.routes:
            route_info = self.routes[source]
            handler = route_info["handler"]
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(payload)
                else:
                    handler(payload)
            except Exception as e:
                import structlog
                logger = structlog.get_logger("SATURDAY.Notification")
                logger.error("notification_route_error", source=source, error=str(e))
                if self.default_handler:
                    try:
                        if asyncio.iscoroutinefunction(self.default_handler):
                            await self.default_handler(payload)
                        else:
                            self.default_handler(payload)
                    except Exception:
                        pass
        elif self.default_handler:
            try:
                if asyncio.iscoroutinefunction(self.default_handler):
                    await self.default_handler(payload)
                else:
                    self.default_handler(payload)
            except Exception:
                pass
        else:
            import structlog
            logger = structlog.get_logger("SATURDAY.Notification")
            logger.warning("notification_no_handler", source=source)

    async def broadcast(self, payload, source_filter=None):
        tasks = []
        for source, route_info in self.routes.items():
            if source_filter and source != source_filter:
                continue
            handler = route_info["handler"]
            try:
                if asyncio.iscoroutinefunction(handler):
                    tasks.append(asyncio.create_task(handler(payload)))
                else:
                    tasks.append(asyncio.create_task(asyncio.get_event_loop().run_in_executor(None, handler, payload)))
            except Exception:
                pass
        if self.default_handler:
            try:
                if asyncio.iscoroutinefunction(self.default_handler):
                    tasks.append(asyncio.create_task(self.default_handler(payload)))
                else:
                    tasks.append(asyncio.create_task(asyncio.get_event_loop().run_in_executor(None, self.default_handler, payload)))
            except Exception:
                pass
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def rate_limit(self, source, window_sec=60):
        now = time.time()
        if source not in self.rate_limiter:
            self.rate_limiter[source] = []
        self.rate_limiter[source] = [t for t in self.rate_limiter[source] if now - t < window_sec]
        return len(self.rate_limiter[source]) < 10