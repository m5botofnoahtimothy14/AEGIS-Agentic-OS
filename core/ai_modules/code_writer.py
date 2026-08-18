import sys
sys.path.insert(0, r'D:\S.A.T.U.R.D.A.Y\core')
import structlog
from core.event_bus import EventBus

logger = structlog.get_logger("SATURDAY.AI.CodeWriter")

# Registered code snippets for common Python patterns
CODE_SNIPPETS = {
    "web_server": """import asyncio
from aiohttp import web

async def handle_root(request):
    return web.Response(text="Hello SATURDAY")

async def main():
    app = web.Application()
    app.router.add_get("/", handle_root)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    logger.info("Web server started on port 8080")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
""",
    "data_parser": """import json
import csv
from datetime import datetime

def parse_timestamp(ts_str):
    try:
        return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return datetime.now()

def extract_fields(data, fields):
    result = {}
    for field in fields:
        if field in data:
            result[field] = data[field]
    return result

def clean_data(data):
    cleaned = {}
    for k, v in data.items():
        if v is None:
            cleaned[k] = ""
        elif isinstance(v, (str, int, float, bool)):
            cleaned[k] = v
        else:
            cleaned[k] = str(v)
    return cleaned
""",
    "api_client": """import aiohttp
import asyncio

class APIClient:
    def __init__(self, base_url, api_key=None):
        self.base_url = base_url
        self.api_key = api_key
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={"Authorization": "Bearer " + self.api_key}
            if self.api_key
            else {}
        )
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    async def get(self, endpoint, params=None):
        url = self.base_url + "/" + endpoint
        async with self.session.get(url, params=params) as resp:
            return await resp.json()

    async def post(self, endpoint, data):
        url = self.base_url + "/" + endpoint
        async with self.session.post(url, json=data) as resp:
            return await resp.json()
"""
}

class CodeWriter:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.event_bus.subscribe("code_request", self.generate_code)
        self.snippet_registry = CODE_SNIPPETS

    def generate_code(self, data):
        prompt = data.get("prompt", "")
        language = data.get("language", "python")
        style = data.get("style", "standard")

        logger.info("Generating " + language + " code for: " + prompt[:80])

        # Try snippet registry first
        if prompt.lower().strip() in self.snippet_registry:
            code = self.snippet_registry[prompt.lower().strip()]
        else:
            # Generate template code based on language and prompt
            code = self._generate_template_code(prompt, language, style)

        self.event_bus.publish("code_response", {"code": code, "prompt": prompt, "language": language})
        return code

    def _generate_template_code(self, prompt, language, style):
        if language == "python":
            if "web" in prompt.lower():
                return CODE_SNIPPETS["web_server"]
            elif "data" in prompt.lower() or "csv" in prompt.lower():
                return CODE_SNIPPETS["data_parser"]
            elif "api" in prompt.lower() or "client" in prompt.lower():
                return CODE_SNIPPETS["api_client"]
            else:
                return "# Python code for: " + prompt + "\n\ndef process():\n    # TODO: Implement based on: " + prompt + "\n    return None"
        else:
            return "# " + language + " code for: " + prompt + "\n# TODO: Implement based on the prompt\n"

    def list_snippets(self):
        return list(self.snippet_registry.keys())