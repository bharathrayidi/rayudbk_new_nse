import os
import jwt
from datetime import datetime, timedelta
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# --- CONFIGURATION ---
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "nse_dashboard_secret_key_12345")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

security = HTTPBearer()
router = APIRouter(prefix="/auth", tags=["auth"])

# --- UTILITIES ---
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Dependency for protected routes
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = decode_access_token(token)
    username = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return {"username": username}

# --- Pydantic Models ---
class UserAuth(BaseModel):
    username: str
    password: str

# --- ENDPOINTS ---
@router.post("/login")
def login(user: UserAuth):
    # Hardcoded single admin access
    if user.username == "Bharath" and user.password == "RBC@99":
        access_token = create_access_token(data={"sub": user.username})
        return {"access_token": access_token, "token_type": "bearer"}
    else:
        raise HTTPException(status_code=401, detail="Incorrect username or password")

@router.get("/me")
def read_users_me(current_user: dict = Depends(get_current_user)):
    return {"username": current_user["username"]}
