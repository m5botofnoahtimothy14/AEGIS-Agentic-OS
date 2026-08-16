# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for SATURDAY AI OS Windows .exe build."""

from pathlib import Path

ROOT = Path(SPECPATH).parent

hiddenimports = [
    # Web stack
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    # Security / auth
    "jsonschema",
    "firebase_admin",
    "cryptography",
    # Agents
    "langgraph",
    "langchain_core",
    # Assistant package
    "core.assistant.builtins",
    "core.assistant.registry",
    "core.assistant.loader",
    "core.assistant.executor",
    "core.assistant.offline_llm",
    "core.assistant.router",
    "core.assistant.tool_agent",
    "core.assistant.memory",
    "core.assistant.profile",
    "core.assistant.reminders",
]

datas = [
    (str(ROOT / "core" / "config.json"), "core"),
    (str(ROOT / "core" / "state.json"), "core"),
    (str(ROOT / "core" / "ui" / "templates"), "core/ui/templates"),
    (str(ROOT / "core" / "ui" / "static"), "core/ui/static"),
    (str(ROOT / "core" / "ui" / "dashboard"), "core/ui/dashboard"),
    (str(ROOT / "data" / "first_boot_setup.json"), "data"),
    (str(ROOT / "data" / "audio_calibration.json"), "data"),
    (str(ROOT / "data" / "directory.json"), "data"),
]

a = Analysis(
    [str(ROOT / "saturday_launcher.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "jupyter",
        "IPython",
        "pandas",
        "tensorflow",
        "torch",
        "torchvision",
        "deepface",
        "cv2",
        "ultralytics",
        "mediapipe",
        "dlib",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="SATURDAY",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
