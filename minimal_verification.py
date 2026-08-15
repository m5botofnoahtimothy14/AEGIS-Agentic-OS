#!/usr/bin/env python3
"""
Minimal verification script for SATURDAY AI OS components
This script tests imports and basic functionality without starting the full system
"""

import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

def test_core_imports():
    """Test that core modules can be imported without errors"""
    print("Testing core module imports...")
    
    core_modules = [
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
        ("Brain", "core.brain", "Brain"),
        ("Self Healing", "core.self_heal", "SelfHealingSystem"),
        ("Window Manager", "core.window_manager", "WindowManager"),
        ("Security Module", "core.security", "SecurityModule"),
        ("RBAC Manager", "core.rbac", "RBACManager"),
    ]
    
    successful_imports = 0
    failed_imports = 0
    
    for name, module_path, class_name in core_modules:
        try:
            module = __import__(module_path, fromlist=[class_name])
            klass = getattr(module, class_name)
            print(f"  ✓ {name} - {module_path}.{class_name}")
            successful_imports += 1
        except ImportError as e:
            print(f"  ✗ {name} - {module_path}.{class_name}: {e}")
            failed_imports += 1
        except AttributeError as e:
            print(f"  ✗ {name} - {module_path}.{class_name}: {e}")
            failed_imports += 1
        except Exception as e:
            print(f"  ? {name} - {module_path}.{class_name}: {e}")
            failed_imports += 1
    
    print(f"\nCore Import Summary: {successful_imports} successful, {failed_imports} failed")
    return successful_imports, failed_imports

def test_assistant_components():
    """Test assistant-related components"""
    print("\nTesting assistant components...")
    
    assistant_modules = [
        ("Assistant Loader", "core.assistant.loader"),
        ("Assistant Executor", "core.assistant.executor"),
        ("Assistant Router", "core.assistant.router"),
        ("Tool Agent", "core.assistant.tool_agent"),
        ("Assistant Memory", "core.assistant.memory"),
        ("Assistant Profile", "core.assistant.profile"),
        ("Assistant Reminders", "core.assistant.reminders"),
        ("Assistant Registry", "core.assistant.registry"),
        ("Offline LLM", "core.assistant.offline_llm"),
    ]
    
    successful_imports = 0
    failed_imports = 0
    
    for name, module_path in assistant_modules:
        try:
            __import__(module_path)
            print(f"  ✓ {name} - {module_path}")
            successful_imports += 1
        except ImportError as e:
            print(f"  ✗ {name} - {module_path}: {e}")
            failed_imports += 1
        except Exception as e:
            print(f"  ? {name} - {module_path}: {e}")
            failed_imports += 1
    
    print(f"\nAssistant Import Summary: {successful_imports} successful, {failed_imports} failed")
    return successful_imports, failed_imports

def test_ui_components():
    """Test UI-related components"""
    print("\nTesting UI components...")
    
    ui_exists = Path("core/ui").exists()
    templates_exist = Path("core/ui/templates").exists()
    static_exist = Path("core/ui/static").exists()
    
    print(f"  UI directory exists: {ui_exists}")
    print(f"  Templates directory exists: {templates_exist}")
    print(f"  Static directory exists: {static_exist}")
    
    return ui_exists, templates_exist, static_exist

def test_config_files():
    """Test that required config files exist"""
    print("\nTesting configuration files...")
    
    config_json = Path("core/config.json").exists()
    state_json = Path("core/state.json").exists()
    
    print(f"  Config JSON exists: {config_json}")
    print(f"  State JSON exists: {state_json}")
    
    if config_json:
        try:
            import json
            with open("core/config.json", 'r') as f:
                config = json.load(f)
            print(f"  Config entries: {len(config)} found")
        except Exception as e:
            print(f"  Config error: {e}")
    
    return config_json, state_json

def test_data_files():
    """Test that required data files exist"""
    print("\nTesting data files...")
    
    required_data = [
        "first_boot_setup.json",
        "audio_calibration.json",
        "directory.json"
    ]
    
    found_files = 0
    for filename in required_data:
        file_path = Path("data") / filename
        exists = file_path.exists()
        print(f"  {filename}: {'✓' if exists else '✗'}")
        if exists:
            found_files += 1
    
    print(f"\nData files: {found_files}/{len(required_data)} found")
    return found_files, len(required_data)

def main():
    """Main verification function"""
    print("="*60)
    print("MINIMAL VERIFICATION FOR SATURDAY AI OS")
    print("="*60)
    
    # Run all tests
    core_success, core_fail = test_core_imports()
    assist_success, assist_fail = test_assistant_components()
    ui_exists, templates_exist, static_exist = test_ui_components()
    config_exists, state_exists = test_config_files()
    data_found, data_total = test_data_files()
    
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)
    
    print(f"Core modules: {core_success} successful, {core_fail} failed")
    print(f"Assistant modules: {assist_success} successful, {assist_fail} failed")
    print(f"UI components: Directories exist = {ui_exists}, Templates = {templates_exist}, Static = {static_exist}")
    print(f"Config files: Config = {config_exists}, State = {state_exists}")
    print(f"Data files: {data_found}/{data_total} found")
    
    # Overall assessment
    total_possible = core_success + assist_success
    total_failed = core_fail + assist_fail
    
    if total_failed == 0 and config_exists and state_exists and data_found == data_total:
        print("\n🎉 MINIMAL VERIFICATION PASSED!")
        print("All core components are available and properly structured.")
        print("System is likely ready for production with proper Python environment.")
        return True
    else:
        print(f"\n⚠️  MINIMAL VERIFICATION INCOMPLETE")
        print(f"Potential issues: {total_failed} module import failures")
        if not config_exists or not state_exists:
            print("Missing config/state files")
        if data_found < data_total:
            print(f"Missing {data_total - data_found} data files")
        print("These issues may prevent the system from running properly.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)