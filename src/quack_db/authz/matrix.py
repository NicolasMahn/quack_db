"""Repo × tier `rwmd` matrix (plan § Repos × tiers)."""

from __future__ import annotations

from dataclasses import dataclass

from quack_db.db.models import User

# Logical repos → default Chroma collection names (shared corpora)
REPO_TO_COLLECTION: dict[str, str] = {
    "public": "public",
    "student": "student",
    "member": "member",
    "board_internal": "board_internal",
    "dev": "dev",
}

COLLECTION_TO_REPO: dict[str, str] = {v: k for k, v in REPO_TO_COLLECTION.items()}

# user_agent_context is special — collection name user_ctx_{user_id}
USER_CTX_PREFIX = "user_ctx_"


def user_ctx_collection_name(user_id) -> str:
    return f"{USER_CTX_PREFIX}{user_id}"


def is_user_ctx_collection(name: str) -> bool:
    return name.startswith(USER_CTX_PREFIX)


@dataclass(frozen=True)
class Rwmd:
    read: bool
    write: bool
    modify: bool
    delete: bool


def parse_rwmd(s: str) -> Rwmd:
    s = (s or "----").ljust(4, "-")[:4]
    return Rwmd(
        read=s[0] == "r",
        write=s[1] == "w",
        modify=s[2] == "m",
        delete=s[3] == "d",
    )


# (repo -> column_key -> rwmd string). column_key ∈
# everyone | students | members | board | dev_student | dev_admin
_MATRIX: dict[str, dict[str, str]] = {
    "public": {
        "everyone": "r---",
        "students": "rwmd",
        "members": "rw--",
        "board": "rwmd",
        "dev_student": "rwmd",
        "dev_admin": "rwmd",
    },
    "student": {
        "everyone": "----",
        "students": "rw--",
        "members": "rw--",
        "board": "rwmd",
        "dev_student": "rwmd",
        "dev_admin": "rwmd",
    },
    "member": {
        "everyone": "----",
        "students": "----",
        "members": "rw--",
        "board": "rwmd",
        "dev_student": "----",
        "dev_admin": "rwmd",
    },
    "board_internal": {
        "everyone": "----",
        "students": "----",
        "members": "----",
        "board": "rwmd",
        "dev_student": "----",
        "dev_admin": "rwmd",
    },
    "dev": {
        "everyone": "----",
        "students": "rwmd",
        "members": "rwmd",
        "board": "rwmd",
        "dev_student": "rwmd",
        "dev_admin": "rwmd",
    },
    "user_agent_context": {
        "everyone": "----",
        "students": "rwmd",
        "members": "rwmd",
        "board": "rwmd",
        "dev_student": "rwmd",
        "dev_admin": "rwmd",
    },
}


def _column_key(user: User) -> str:
    if user.is_dev_admin:
        return "dev_admin"
    if user.is_dev_student:
        return "dev_student"
    return user.tier


def rwmd_for_repo(user: User, repo: str) -> Rwmd:
    col = _column_key(user)
    cell = _MATRIX.get(repo, {}).get(col, "----")
    return parse_rwmd(cell)


def resolve_repo(collection_name: str, user_id) -> str | None:
    """Map Chroma collection name → logical repo, or None if unknown."""
    if is_user_ctx_collection(collection_name):
        uid = str(user_id)
        if collection_name != user_ctx_collection_name(uid):
            return None
        return "user_agent_context"
    return COLLECTION_TO_REPO.get(collection_name)


def list_readable_collections(user: User) -> list[str]:
    names: list[str] = []
    for repo, chroma_name in REPO_TO_COLLECTION.items():
        if rwmd_for_repo(user, repo).read:
            names.append(chroma_name)
    if rwmd_for_repo(user, "user_agent_context").read:
        names.append(user_ctx_collection_name(user.id))
    return sorted(set(names))
