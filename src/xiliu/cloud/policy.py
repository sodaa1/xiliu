"""Server-owned cloud policy; account files and caller profiles cannot grant privileges."""

from xiliu.hooks.engine import HookEngine
from xiliu.policy.engine import DEFAULT_PROFILES, Decision, PolicyEngine


class CloudPolicyEngine(PolicyEngine):
    def __init__(self):
        self.allowed = frozenset(
            permission
            for permission, effect in DEFAULT_PROFILES["interactive"].items()
            if effect == "allow" and not permission.startswith(("filesystem.", "process."))
        )

    def evaluate(self, *, actor, source, capability_id, permission, arguments, profile):
        allowed = source == "builtin" and permission in self.allowed
        if permission == "agent.delegate":
            allowed = allowed and (
                capability_id == "builtin:call_search_agent"
                or (
                    capability_id == "builtin:agent_call"
                    and arguments.get("agent_id") in {"rag", "research"}
                )
            )
        return Decision("allow" if allowed else "deny", "云端服务器权限限制")


class NoCloudHooks(HookEngine):
    def __init__(self):
        self.hooks = []

    def before(self, *args, **kwargs):
        return [], False

    def after(self, *args, **kwargs):
        return []
