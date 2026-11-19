from fastapi import APIRouter,Depends
from ..config.database import db_session
from ..schemas.note import NoteInput
from ..services.auth import current_user,writer,admin
from ..services.export import note_csv
from ..controllers.notes import NotesController as C
router=APIRouter()
@router.get('/notes')
def notes(db=Depends(db_session),u=Depends(current_user)):return C.list(db)
@router.post('/notes')
def create(data:NoteInput,db=Depends(db_session),u=Depends(writer)):return C.create(db,u,data)
@router.post('/notes/{id}/approve')
def approve(id:int,db=Depends(db_session),u=Depends(admin)):return C.approve(db,u,id)
@router.get('/notes/{id}/export')
def export(id:int,db=Depends(db_session),u=Depends(current_user)):return note_csv(db,id)
