from pydantic import BaseModel,Field
class RunInput(BaseModel):
    source_id:int
    name:str=Field(min_length=2,max_length=160)
    parameters:dict
