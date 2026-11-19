from sqlalchemy import Column,Integer,String
from ..config.database import Base
class User(Base):
    __tablename__='users'
    id=Column(Integer,primary_key=True)
    email=Column(String(120),unique=True,nullable=False)
    password_hash=Column(String(256),nullable=False)
    role=Column(String(20),nullable=False)
