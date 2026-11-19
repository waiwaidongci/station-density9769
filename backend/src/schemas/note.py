from pydantic import BaseModel,Field
class NoteInput(BaseModel):
    run_id:int
    title:str=Field(min_length=2,max_length=160)
    body:str=Field(min_length=5,max_length=4000)
class LoginInput(BaseModel):
    email:str
    password:str
