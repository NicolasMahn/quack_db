from typing import Annotated

from fastapi import APIRouter, Depends

from api.deps import require_user
from quack_db.db.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/validate")
def validate(user: Annotated[User, Depends(require_user)]):
    return {
        "valid": True,
        "user_id": str(user.id),
        "email": user.email,
        "entra_oid": user.entra_oid,
        "tier": user.tier,
        "is_dev_student": user.is_dev_student,
        "is_dev_admin": user.is_dev_admin,
    }
