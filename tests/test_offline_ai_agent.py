from pathlib import Path

from core.ai_agent import OfflineAIAgent


def test_agent_handles_offline_queries(tmp_path: Path) -> None:
    agent = OfflineAIAgent(storage_dir=tmp_path)

    result = agent.process_command("what can you do")

    assert result["mode"] == "offline"
    assert result["intent"] == "info"
    assert "offline" in result["message"].lower()
    assert result["confidence"] >= 0.6


def test_agent_persists_memory(tmp_path: Path) -> None:
    agent = OfflineAIAgent(storage_dir=tmp_path)
    agent.process_command("remember that I like robotics")

    saved = agent.save_state()

    assert saved["memory"]["preferences"]
    assert (tmp_path / "agent_state.json").exists()


def test_agent_manages_notes_and_memory(tmp_path: Path) -> None:
    agent = OfflineAIAgent(storage_dir=tmp_path)

    note_result = agent.process_command("write note offline features are alive")
    memory_result = agent.process_command("remember that I like robotics")
    recall_result = agent.process_command("show memory")

    assert note_result["action"] == "file"
    assert (tmp_path / "notes" / "offline-features-are-alive.md").exists()
    assert memory_result["action"] == "remember"
    assert recall_result["action"] == "memory"


def test_agent_supports_tasks_and_note_listing(tmp_path: Path) -> None:
    agent = OfflineAIAgent(storage_dir=tmp_path)

    task_result = agent.process_command("create task test the new agent workflow")
    list_result = agent.process_command("list notes")

    assert task_result["action"] == "task"
    assert list_result["action"] == "list_notes"
    assert task_result["task_id"].startswith("task-")
