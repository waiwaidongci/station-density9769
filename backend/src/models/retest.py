from sqlalchemy import Column,Integer,String,Text,JSON,ForeignKey
from ..config.database import Base
from ..config.settings import CONFIG
class RetestStudy(Base):
    __tablename__='retest_studies'
    id=Column(Integer,primary_key=True)
    name=Column(String(160),nullable=False)
    early_run_id=Column(Integer,ForeignKey(CONFIG['run_table']+'.id'),nullable=False)
    period1_source_id=Column(Integer,ForeignKey(CONFIG['source_table']+'.id'),nullable=False)
    period2_source_id=Column(Integer,ForeignKey(CONFIG['source_table']+'.id'),nullable=False)
    pairing=Column(String(20),nullable=False,default='suffix')
    state=Column(String(20),default='queued')
    parameters=Column(JSON,nullable=False)
    snapshot=Column(JSON,nullable=False)
    progress=Column(JSON,nullable=False)
    result=Column(JSON,nullable=True)
    verification=Column(JSON,nullable=True)
    error=Column(Text,default='')
    run_token=Column(String(64),default='')
    heartbeat_at=Column(String(40),default='')
    created_at=Column(String(40),nullable=False)
    updated_at=Column(String(40),nullable=False)
