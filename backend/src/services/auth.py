from fastapi import Depends,HTTPException
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import jwt
from ..config.database import db_session
from ..config.settings import JWT_SECRET
from ..models.user import User
bearer=HTTPBearer(auto_error=False)
def current_user(credentials:HTTPAuthorizationCredentials=Depends(bearer),db:Session=Depends(db_session)):
    try:
        if not credentials:raise ValueError('missing')
        data=jwt.decode(credentials.credentials,JWT_SECRET,algorithms=['HS256'])
        user=db.get(User,int(data['sub']))
        if not user:raise ValueError('missing user')
        return user
    except Exception:raise HTTPException(401,'登录已过期，请重新登录')
def writer(user=Depends(current_user)):
    if user.role not in ('admin','analyst'):raise HTTPException(403,'当前账号只能阅读')
    return user
def admin(user=Depends(current_user)):
    if user.role!='admin':raise HTTPException(403,'仅负责人可以批准')
    return user
