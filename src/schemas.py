# schemas.py is used to define the data models for the API endpoints. 
# It uses Pydantic's BaseModel to create data validation and serialization for the request and response bodies.

from pydantic import BaseModel

class PostCreate(BaseModel):
    title: str
    content: str
    
class PostResponse(BaseModel):
    title: str
    content: str