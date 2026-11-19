from sqlalchemy import Column,Integer,String,JSON,ForeignKey,UniqueConstraint
from ..config.database import Base
from ..config.settings import CONFIG
class Record(Base):
    __tablename__=CONFIG['record_table']
    __table_args__=(UniqueConstraint('source_id','reference',name='uq_record_reference'),)
    id=Column(Integer,primary_key=True)
    source_id=Column(Integer,ForeignKey(CONFIG['source_table']+'.id'),nullable=False)
    reference=Column(String(120),nullable=False)
    values=Column(JSON,nullable=False)
