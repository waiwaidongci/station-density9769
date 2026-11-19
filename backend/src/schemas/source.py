from pydantic import BaseModel,Field
class SourceInput(BaseModel):
    name:str=Field(min_length=2,max_length=160)
    filename:str=Field(min_length=3,max_length=160)
    description:str=Field(default='',max_length=2000)
class RecordInput(BaseModel):
    reference:str=Field(min_length=1,max_length=120)
    values:dict
class RecordBatch(BaseModel):
    records:list[RecordInput]=Field(min_length=1,max_length=1000)
