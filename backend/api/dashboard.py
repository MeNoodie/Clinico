from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from backend.auth.dependencies import get_current_admin

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/dashboard")
def dashboard(
    admin: Annotated[dict, Depends(get_current_admin)]
):
    return {
        "message": "Welcome to admin dashboard"
    }
    



    