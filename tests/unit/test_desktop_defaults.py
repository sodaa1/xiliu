from pathlib import Path

from xiliu.api.desktop_defaults import seed_mcp_defaults
from xiliu.capabilities.mcp import MCPManager


def test_desktop_seeds_public_aihot_settings_and_preserves_user_changes(tmp_path):
    defaults = Path(__file__).resolve().parents[2] / "desktop" / "defaults"
    seed_mcp_defaults(tmp_path, defaults)
    manager = MCPManager(tmp_path / "mcp")
    assert manager.servers() == ["aihot"]
    assert manager.server_permissions("aihot") == ("network.read",)
    target = tmp_path / "mcp/aihot/mcp.json"
    target.write_text('{"servers":{"aihot":{"enabled":false}}}')
    seed_mcp_defaults(tmp_path, defaults)
    assert MCPManager(tmp_path / "mcp").servers() == []
