from pydantic import BaseModel

class UserCreate(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    detail: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str