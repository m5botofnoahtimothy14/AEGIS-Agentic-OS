from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

from core.ai_agent import OfflineAIAgent


def create_agent_app(agent: OfflineAIAgent | None = None) -> FastAPI:
    app = FastAPI(title="SATURDAY Production Agent", version="1.1.0")
    runtime_agent = agent or OfflineAIAgent()

    @app.get("/healthz")
    async def healthz() -> dict[str, Any]:
        return {"status": "ok", "mode": runtime_agent.get_status().get("mode", "offline")}

    @app.get("/status")
    async def status() -> dict[str, Any]:
        return runtime_agent.get_status()

    @app.post("/command")
    async def command(payload: dict[str, Any]) -> dict[str, Any]:
        command_text = str(payload.get("command", "")).strip()
        if not command_text:
            raise HTTPException(status_code=400, detail="command is required")
        result = runtime_agent.process_command(command_text)
        return result

    @app.post("/command/json")
    async def command_json(payload: dict[str, Any]) -> JSONResponse:
        command_text = str(payload.get("command", "")).strip()
        if not command_text:
            raise HTTPException(status_code=400, detail="command is required")
        return JSONResponse(runtime_agent.process_command(command_text))

    @app.get("/models")
    async def models() -> dict[str, Any]:
        from saturday_downloader import categories_summary

        return categories_summary()

    @app.post("/models/download")
    async def models_download(payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        categories = payload.get("category") or ["all"]
        from saturday_downloader import download

        code = download(categories=categories, offline=False)
        return {"status": "ok" if code == 0 else "partial", "categories": categories}

    return app


def run_agent_service(host: str = "127.0.0.1", port: int = 8765, storage_dir: str = "data") -> None:
    app = create_agent_app(OfflineAIAgent(storage_dir=storage_dir))
    uvicorn.run(app, host=host, port=port)
