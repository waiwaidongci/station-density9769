from fastapi import APIRouter, Depends
from ..config.database import db_session
from ..schemas.retest import RetestInput
from ..services.auth import current_user, writer, admin
from ..controllers.retest import RetestController as C

router = APIRouter()


@router.get('/retest-studies')
def studies(db=Depends(db_session), u=Depends(current_user)):
    return C.list(db, u)


@router.post('/retest-studies')
def create(data: RetestInput, db=Depends(db_session), u=Depends(writer)):
    return C.create(db, u, data)


@router.get('/retest-studies/{id}')
def detail(id: int, db=Depends(db_session), u=Depends(current_user)):
    return C.get(db, id, u)


@router.post('/retest-studies/{id}/retry')
def retry(id: int, db=Depends(db_session), u=Depends(writer)):
    return C.retry(db, u, id)


@router.post('/retest-studies/{id}/publish')
def publish(id: int, db=Depends(db_session), u=Depends(admin)):
    return C.publish(db, u, id)
