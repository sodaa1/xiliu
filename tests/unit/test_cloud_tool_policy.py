import pytest

from xiliu.cloud.policy import CloudPolicyEngine


@pytest.mark.parametrize(
    "permission,source",
    [
        ("process.execute.safe", "builtin"),
        ("process.execute", "builtin"),
        ("filesystem.read.workspace", "builtin"),
        ("filesystem.write.workspace", "builtin"),
        ("network.read", "mcp"),
        ("package.install", "builtin"),
    ],
)
@pytest.mark.parametrize("profile", ["interactive", "background", "cloud"])
def test_cloud_policy_cannot_be_downgraded(permission, source, profile):
    decision = CloudPolicyEngine().evaluate(
        actor="human",
        source=source,
        capability_id="builtin:test",
        permission=permission,
        arguments={},
        profile=profile,
    )
    assert decision.effect == "deny"


def test_cloud_preserves_business_permissions():
    for permission in ("knowledge.write", "tasks.write", "feed.read", "conversations.read"):
        assert (
            CloudPolicyEngine()
            .evaluate(
                actor="agent",
                source="builtin",
                capability_id="builtin:app:test",
                permission=permission,
                arguments={},
                profile="background",
            )
            .effect
            == "allow"
        )
