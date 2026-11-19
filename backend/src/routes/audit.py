from fastapi import APIRouter,Depends
from sqlalchemy import select
from ..config.database import db_session
from ..models.audit import Audit
from ..services.auth import current_user
from ..utils.serialization import row
router=APIRouter()
@router.get('/audit')
def audit(db=Depends(db_session),u=Depends(current_user)):
    return [row(x) for x in db.scalars(select(Audit).order_by(Audit.id.desc()).limit(200))]
