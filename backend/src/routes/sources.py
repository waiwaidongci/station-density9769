from fastapi import APIRouter,Depends
from ..config.database import db_session
from ..schemas.source import SourceInput,RecordBatch
from ..services.auth import current_user,writer
from ..controllers.sources import SourcesController as C
router=APIRouter()
@router.get('/sources')
def all_sources(db=Depends(db_session),u=Depends(current_user)):return C.list(db)
@router.post('/sources')
def create_source(data:SourceInput,db=Depends(db_session),u=Depends(writer)):return C.save(db,u,data)
@router.put('/sources/{id}')
def update_source(id:int,data:SourceInput,db=Depends(db_session),u=Depends(writer)):return C.save(db,u,data,id)
@router.get('/sources/{id}/records')
def records(id:int,db=Depends(db_session),u=Depends(current_user)):return C.records(db,id)
@router.post('/sources/{id}/records')
def add(id:int,data:RecordBatch,db=Depends(db_session),u=Depends(writer)):return C.add_records(db,u,id,data)
