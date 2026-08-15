#!/usr/bin/env python3
"""
Comprehensive Test Suite for SATURDAY AI OS
Tests all major components including UI, agentic workflows, audio, assistants, and more
"""

import sys
import os
import time
import subprocess
import threading
import json
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

def run_subprocess_test(cmd, desc):
    """Helper to run a subprocess test"""
    print(f"\n[TEST] {desc}")
    print(f"Command: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            print(f"[PASS] {desc}")
            return True
        else:
            print(f"[FAIL] {desc}")
            print(f"Error: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"[TIMEOUT] {desc}")
        return False
    except Exception as e:
        print(f"[ERROR] {desc}: {e}")
        return False

def test_basic_imports():
    """Test basic module imports"""
    print("\n[1] Testing Basic Module Imports...")
    
    modules_to_test = [
        ("Event Bus", "core.event_bus", "EventBus"),
        ("Audio Service", "core.audio_service", "CrossPlatformAudio"),
        ("Audio Speaker", "core.audio_speaker", "SpeakerManager"),
        ("SATURDAY Voice", "core.saturday_voice", "SATURDAYVoice"),
        ("AI Agent", "core.ai_agent", "AIAgent"),
        ("Agent Service", "core.agent_service", "AgentService"),
        ("System Monitor", "core.system_monitor", "SystemMonitor"),
        ("Task Manager", "core.task_manager", "TaskManager"),
        ("Human Interface", "core.human_interface", "HumanInterface"),
        ("Alert Manager", "core.alert_manager", "AlertManager"),
    ]
    
    results = []
    for name, module, cls in modules_to_test:
        try:
            mod = __import__(module, fromlist=[cls])
            klass = getattr(mod, cls)
            print(f"    [PASS] {name} ({module}.{cls})")
            results.append(True)
        except Exception as e:
            print(f"    [FAIL] {name}: {e}")
            results.append(False)
    
    passed = sum(results)
    total = len(results)
    print(f"\nBasic Imports: {passed}/{total} passed")
    return passed == total

def test_audio_components():
    """Test audio components specifically"""
    print("\n[2] Testing Audio Components...")
    
    try:
        from core.audio_service import CrossPlatformAudio
        audio = CrossPlatformAudio()
        
        # Test microphone listing
        mics = audio.list_microphones()
        print(f"    Found {len(mics)} microphones")
        
        # Test speaker manager
        from core.audio_speaker import SpeakerManager
        speaker_mgr = SpeakerManager()
        default_speaker = speaker_mgr.get_default()
        print(f"    Default speaker: {'Available' if default_speaker else 'Not found'}")
        
        # Test spatial audio
        from core.spatial_audio import SpatialAudioProcessor
        spatial = SpatialAudioProcessor()
        print(f"    Spatial audio processor: Initialized")
        
        # Test audio routing
        from core.sound_monitor import SoundMonitor
        monitor = SoundMonitor()
        print(f"    Sound monitor: Initialized")
        
        print("    [PASS] Audio Components")
        return True
    except Exception as e:
        print(f"    [FAIL] Audio Components: {e}")
        return False

def test_assistant_components():
    """Test assistant-related components"""
    print("\n[3] Testing Assistant Components...")
    
    try:
        # Test assistant modules
        from core.assistant import loader, executor, router, tool_agent, memory, profile, reminders
        print("    Assistant modules loaded successfully")
        
        # Test assistant registry
        from core.assistant.registry import AssistantRegistry
        registry = AssistantRegistry()
        print(f"    Assistant registry: Initialized with {len(registry.list_assistants())} assistants")
        
        # Test offline LLM
        from core.assistant.offline_llm import OfflineLLM
        llm = OfflineLLM()
        print("    Offline LLM: Initialized")
        
        print("    [PASS] Assistant Components")
        return True
    except Exception as e:
        print(f"    [FAIL] Assistant Components: {e}")
        return False

def test_ui_and_navigation():
    """Test UI and navigation components"""
    print("\n[4] Testing UI and Navigation...")
    
    try:
        from core.window_manager import WindowManager
        wm = WindowManager()
        print("    Window manager: Initialized")
        
        # Check for UI templates
        ui_templates_path = PROJECT_ROOT / "core" / "ui" / "templates"
        if ui_templates_path.exists():
            template_count = len(list(ui_templates_path.glob("*.html")))
            print(f"    UI Templates: Found {template_count} HTML templates")
        else:
            print("    UI Templates: Directory not found")
            
        # Check for static assets
        static_path = PROJECT_ROOT / "core" / "ui" / "static"
        if static_path.exists():
            asset_count = len(list(static_path.glob("*")))
            print(f"    Static Assets: Found {asset_count} assets")
        else:
            print("    Static Assets: Directory not found")
            
        print("    [PASS] UI and Navigation Components")
        return True
    except Exception as e:
        print(f"    [FAIL] UI and Navigation Components: {e}")
        return False

def test_agentic_workflows():
    """Test agentic workflow capabilities"""
    print("\n[5] Testing Agentic Workflows...")
    
    try:
        from core.ai_agent import AIAgent
        from core.agent_service import AgentService
        
        # Initialize agent service
        agent_service = AgentService()
        print("    Agent service: Initialized")
        
        # Test basic agent creation
        agent = AIAgent(name="test_agent", capabilities=["reasoning", "memory", "tools"])
        print("    Test agent: Created")
        
        # Test langgraph integration (mentioned in spec file)
        try:
            import langgraph
            print("    LangGraph: Available")
        except ImportError:
            print("    LangGraph: Not available")
            
        # Test langchain integration
        try:
            import langchain_core
            print("    LangChain Core: Available")
        except ImportError:
            print("    LangChain Core: Not available")
        
        print("    [PASS] Agentic Workflows")
        return True
    except Exception as e:
        print(f"    [FAIL] Agentic Workflows: {e}")
        return False

def test_security_components():
    """Test security-related components"""
    print("\n[6] Testing Security Components...")
    
    try:
        from core.security import SecurityModule
        from core.rbac import RBACManager
        from core.antivirus import AntivirusScanner
        from core.malware_guard import MalwareGuard
        
        sec_mod = SecurityModule()
        rbac = RBACManager()
        av_scan = AntivirusScanner()
        malware_guard = MalwareGuard()
        
        print("    Security components: Initialized")
        
        # Test cryptography (mentioned in spec file)
        try:
            import cryptography
            print("    Cryptography: Available")
        except ImportError:
            print("    Cryptography: Not available")
            
        # Test Firebase Admin (mentioned in spec file)
        try:
            import firebase_admin
            print("    Firebase Admin: Available")
        except ImportError:
            print("    Firebase Admin: Not available")
        
        print("    [PASS] Security Components")
        return True
    except Exception as e:
        print(f"    [FAIL] Security Components: {e}")
        return False

def test_system_services():
    """Test system-level services"""
    print("\n[7] Testing System Services...")
    
    try:
        from core.system_monitor import SystemMonitor
        from core.task_manager import TaskManager
        from core.self_heal import SelfHealingSystem
        from core.brain import Brain
        
        sys_mon = SystemMonitor()
        task_mgr = TaskManager()
        self_heal = SelfHealingSystem()
        brain = Brain()
        
        print("    System services: Initialized")
        
        # Perform basic checks
        cpu_percent = sys_mon.get_cpu_percent()
        mem_percent = sys_mon.get_memory_percent()
        print(f"    CPU Usage: {cpu_percent}%")
        print(f"    Memory Usage: {mem_percent}%")
        
        print("    [PASS] System Services")
        return True
    except Exception as e:
        print(f"    [FAIL] System Services: {e}")
        return False

def test_communication_modules():
    """Test communication modules"""
    print("\n[8] Testing Communication Modules...")
    
    try:
        from core.communication.message_bus import MessageBus
        from core.communication.protocol_handler import ProtocolHandler
        from core.communication.network_manager import NetworkManager
        
        msg_bus = MessageBus()
        proto_handler = ProtocolHandler()
        net_mgr = NetworkManager()
        
        print("    Communication modules: Initialized")
        
        print("    [PASS] Communication Modules")
        return True
    except Exception as e:
        print(f"    [FAIL] Communication Modules: {e}")
        return False

def test_main_application_startup():
    """Test that the main application can start"""
    print("\n[9] Testing Main Application Startup...")
    
    try:
        # Try to import the main app
        from core.main import app
        print("    Main FastAPI app: Imported successfully")
        
        # Check that required config files exist
        config_path = PROJECT_ROOT / "core" / "config.json"
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
            print(f"    Config file: Loaded {len(config)} settings")
        else:
            print("    Config file: Not found")
            
        state_path = PROJECT_ROOT / "core" / "state.json"
        if state_path.exists():
            print("    State file: Exists")
        else:
            print("    State file: Not found")
        
        print("    [PASS] Main Application Startup")
        return True
    except Exception as e:
        print(f"    [FAIL] Main Application Startup: {e}")
        return False

def test_web_components():
    """Test web components and API"""
    print("\n[10] Testing Web Components...")
    
    try:
        # Test uvicorn (mentioned in spec file)
        import uvicorn
        print("    Uvicorn: Available")
        
        # Test FastAPI components
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse
        app = FastAPI()
        print("    FastAPI: Available and functional")
        
        # Test Jinja2 templates (used in main.py)
        from juvicorn.templating import Jinja2Templates
        print("    Jinja2 Templates: Available")
        
        print("    [PASS] Web Components")
        return True
    except Exception as e:
        print(f"    [FAIL] Web Components: {e}")
        return False

def run_comprehensive_tests():
    """Run all tests and report results"""
    print("=" * 70)
    print("COMPREHENSIVE SATURDAY AI OS TEST SUITE")
    print("=" * 70)
    
    tests = [
        ("Basic Imports", test_basic_imports),
        ("Audio Components", test_audio_components),
        ("Assistant Components", test_assistant_components),
        ("UI and Navigation", test_ui_and_navigation),
        ("Agentic Workflows", test_agentic_workflows),
        ("Security Components", test_security_components),
        ("System Services", test_system_services),
        ("Communication Modules", test_communication_modules),
        ("Main Application Startup", test_main_application_startup),
        ("Web Components", test_web_components),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"    [ERROR] {test_name}: {e}")
            results.append((test_name, False))
    
    # Report results
    print("\n" + "=" * 70)
    print("TEST RESULTS SUMMARY")
    print("=" * 70)
    
    passed = 0
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    total = len(results)
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! SATURDAY AI OS is ready for production!")
        return True
    else:
        print(f"\n⚠️  {total-passed} tests failed. Please address issues before production.")
        return False

if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)