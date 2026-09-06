from hermes_drive_index.hermes_adapter.tools import drive_index_search, drive_index_status, drive_index_update
from hermes_drive_index import hermes_adapter
from hermes_drive_index.hermes_adapter import tools as adapter_tools
import json


class _FakeRegistry:
    def __init__(self):
        self.registered = {}

    def register(self, **kw):
        self.registered[kw["name"]] = kw

    # ctx-style alias
    def register_tool(self, **kw):
        self.register(**kw)


EXPECTED_TOOLS = {
    "drive_index_search",
    "drive_index_status",
    "drive_index_update",
    "file_organizer_analyze",
    "file_organizer_plan",
    "file_organizer_execute",
    "duplicate_file_detector",
    "old_file_cleanup",
    "auto_organize_downloads",
    "intelligent_document_organizer",
    "local_drive_index",
    "selective_sync_plan",
}


def test_register_tools_and_register_agree_on_names():
    reg = _FakeRegistry()
    adapter_tools.register_tools(reg)
    ctx = _FakeRegistry()
    hermes_adapter.register(ctx)
    assert set(reg.registered) == EXPECTED_TOOLS
    assert set(ctx.registered) == EXPECTED_TOOLS
    # Same schemas via both entry points.
    for name in EXPECTED_TOOLS:
        assert reg.registered[name]["schema"] == ctx.registered[name]["schema"]


def test_schemas_are_byte_stable():
    assert adapter_tools.DRIVE_INDEX_SEARCH_SCHEMA["name"] == "drive_index_search"
    assert adapter_tools.DRIVE_INDEX_SEARCH_SCHEMA["parameters"]["required"] == ["query"]
    assert adapter_tools.DRIVE_INDEX_UPDATE_SCHEMA["parameters"]["required"] == []


def test_plugin_context_spec_preserves_legacy_register_tool_kwargs():
    update = next(spec for spec in adapter_tools.TOOL_SPECS if spec["name"] == "drive_index_update")
    plugin_spec = adapter_tools.plugin_context_spec(update)

    assert "max_result_size_chars" in update
    assert "max_result_size_chars" not in plugin_spec
    assert set(plugin_spec) == {"name", "toolset", "schema", "handler", "check_fn", "emoji"}


def test_all_handler_outputs_json_roundtrip(monkeypatch):
    # Error path: search with empty query.
    assert json.loads(drive_index_search(""))["success"] is False

    # Mocked success path for status.
    monkeypatch.setattr(adapter_tools, "status", lambda: {"exists": True, "counts": {}})
    payload = json.loads(drive_index_status())
    assert payload["success"] is True
    assert "package_version" in payload


def test_adapter_handlers_return_json_for_validation_errors():
    payload = json.loads(drive_index_search(""))
    assert payload["success"] is False


def test_adapter_status_returns_json():
    payload = json.loads(drive_index_status())
    assert "success" in payload


def test_update_default_is_incremental_manifest(monkeypatch):
    calls = {}
    import hermes_drive_index.hermes_adapter.tools as tools

    def fake_incremental():
        calls["incremental"] = True
        return {"mode": "incremental_manifest"}

    monkeypatch.setattr(tools, "incremental_update", fake_incremental)
    payload = json.loads(drive_index_update())
    assert payload["success"] is True
    assert calls["incremental"] is True
    assert payload["requested_mode"] == "incremental_manifest"
