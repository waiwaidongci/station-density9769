from sqlalchemy import Column,Integer,String,Text,JSON,ForeignKey
from ..config.database import Base
from ..config.settings import CONFIG
class Note(Base):
    __tablename__=CONFIG['note_table']
    id=Column(Integer,primary_key=True)
    run_id=Column(Integer,ForeignKey(CONFIG['run_table']+'.id'),nullable=False)
    title=Column(String(160),nullable=False)
    body=Column(Text,nullable=False)
    state=Column(String(20),default='draft')
    frozen_result=Column(JSON,nullable=False)
    author=Column(String(120),nullable=False)
    approved_by=Column(String(120),default='')
