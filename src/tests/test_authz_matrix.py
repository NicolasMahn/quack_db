import uuid

from quack_db.authz import matrix
from quack_db.db.models import User


def _u(tier, *, ds=False, da=False):
    return User(
        id=uuid.uuid4(),
        email="t@example.com",
        tier=tier,
        is_dev_student=ds,
        is_dev_admin=da,
    )


def test_everyone_reads_public_only():
    u = _u("everyone")
    assert matrix.rwmd_for_repo(u, "public").read
    assert not matrix.rwmd_for_repo(u, "student").read


def test_board_rwmd_public():
    u = _u("board")
    p = matrix.rwmd_for_repo(u, "public")
    assert p.read and p.write and p.modify and p.delete


def test_user_ctx_name():
    uid = uuid.uuid4()
    assert matrix.user_ctx_collection_name(uid) == f"user_ctx_{uid}"


def test_resolve_repo_user_ctx():
    uid = uuid.uuid4()
    name = matrix.user_ctx_collection_name(uid)
    assert matrix.resolve_repo(name, uid) == "user_agent_context"
    assert matrix.resolve_repo(name, uuid.uuid4()) is None
