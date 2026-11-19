from fastapi import APIRouter,Depends
from ..config.database import db_session
from ..schemas.run import RunInput
from ..services.auth import current_user,writer
from ..services.export import run_csv
from ..controllers.runs import RunsController as C
router=APIRouter()
@router.get('/runs')
def runs(db=Depends(db_session),u=Depends(current_user)):return C.list(db)
@router.post('/runs')
def create(data:RunInput,db=Depends(db_session),u=Depends(writer)):return C.create(db,u,data)
@router.get('/runs/{id}')
def detail(id:int,db=Depends(db_session),u=Depends(current_user)):return C.get(db,id)
@router.get('/runs/{id}/export')
def export(id:int,db=Depends(db_session),u=Depends(current_user)):return run_csv(db,id)
