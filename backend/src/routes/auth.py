from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from ..config.database import db_session
from ..models.user import User
from ..schemas.note import LoginInput
from ..utils.security import verify_password,token_for
from ..services.auth import current_user
from ..services.audit import log
router=APIRouter()
@router.post('/auth/login')
def login(data:LoginInput,db=Depends(db_session)):
    u=db.scalar(select(User).where(User.email==data.email))
    if not u or not verify_password(data.password,u.password_hash):raise HTTPException(401,'邮箱或密码错误')
    log(db,u,'auth.login',u.role);db.commit()
    return {'token':token_for(u),'user':{'email':u.email,'role':u.role}}
@router.get('/me')
def me(u=Depends(current_user)):return {'email':u.email,'role':u.role}
