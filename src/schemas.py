# schemas.py is used to define the data models for the API endpoints. 
# It uses Pydantic's BaseModel to create data validation and serialization for the request and response bodies.

from pydantic import BaseModel
from fastapi_users import schemas
import uuid

class PostCreate(BaseModel):
    title: str
    content: str
    
class PostResponse(BaseModel):
    title: str
    content: str
    
class UserRead(schemas.BaseUser[uuid.UUID]):
    pass

class UserCreate(schemas.BaseUserCreate):
    pass

class UserUpdate(schemas.BaseUserUpdate):
    pass