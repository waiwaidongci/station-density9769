from sqlalchemy import Column,Integer,String,Text
from ..config.database import Base
class Audit(Base):
    __tablename__='audit_events'
    id=Column(Integer,primary_key=True)
    actor=Column(String(120),nullable=False)
    action=Column(String(80),nullable=False)
    target=Column(String(160),nullable=False)
    detail=Column(Text,default='')
    created_at=Column(String(40),nullable=False)
