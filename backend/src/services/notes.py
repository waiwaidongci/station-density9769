from fastapi import HTTPException
from sqlalchemy import select
from ..models.note import Note
from ..utils.serialization import row
from .runs import get_run
from .audit import log
def list_notes(db):return [row(n) for n in db.scalars(select(Note).order_by(Note.id.desc()))]
def create_note(db,user,data):
    r=get_run(db,data.run_id)
    if r.state!='completed':raise HTTPException(409,'只可为已完成结果提交说明')
    n=Note(run_id=r.id,title=data.title,body=data.body,state='draft',frozen_result=r.result,author=user.email)
    db.add(n);db.flush();log(db,user,'note.created',n.id,n.title);db.commit();return row(n)
def approve_note(db,user,id):
    n=db.get(Note,id)
    if not n:raise HTTPException(404,'未找到说明')
    if n.state!='draft':raise HTTPException(409,'该说明已经批准')
    n.state='approved';n.approved_by=user.email;log(db,user,'note.approved',n.id,n.title);db.commit();return row(n)
