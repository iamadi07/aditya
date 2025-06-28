from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from pymongo import MongoClient
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
import os
import hashlib
import secrets
from typing import Optional
import uuid

# Initialize FastAPI app
app = FastAPI(title="Xgen Cloud API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017/')
client = MongoClient(MONGO_URL)
db = client.xgen_cloud
users_collection = db.users

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# JWT Configuration
SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Pydantic models
class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    id: str
    name: str
    email: str
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str
    user: User

class ContactMessage(BaseModel):
    name: str
    email: EmailStr
    message: str

# Utility functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = users_collection.find_one({"email": email})
    if user is None:
        raise credentials_exception
    return user

# API Routes
@app.get("/")
async def root():
    return {"message": "Xgen Cloud API is running!", "version": "1.0.0"}

@app.post("/api/register", response_model=Token)
async def register_user(user_data: UserRegister):
    try:
        # Check if user already exists
        existing_user = users_collection.find_one({"email": user_data.email})
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create new user
        user_id = str(uuid.uuid4())
        hashed_password = get_password_hash(user_data.password)
        
        new_user = {
            "id": user_id,
            "name": user_data.name,
            "email": user_data.email,
            "password": hashed_password,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Insert user into database
        result = users_collection.insert_one(new_user)
        
        if not result.inserted_id:
            raise HTTPException(status_code=500, detail="Failed to create user")
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user_data.email}, expires_delta=access_token_expires
        )
        
        # Prepare user response
        user_response = User(
            id=user_id,
            name=user_data.name,
            email=user_data.email,
            created_at=new_user["created_at"]
        )
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user=user_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.post("/api/login", response_model=Token)
async def login_user(user_data: UserLogin):
    try:
        # Find user by email
        user = users_collection.find_one({"email": user_data.email})
        
        if not user or not verify_password(user_data.password, user["password"]):
            raise HTTPException(
                status_code=401,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user_data.email}, expires_delta=access_token_expires
        )
        
        # Prepare user response
        user_response = User(
            id=user["id"],
            name=user["name"],
            email=user["email"],
            created_at=user["created_at"]
        )
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user=user_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

@app.get("/api/profile", response_model=User)
async def get_profile(current_user = Depends(get_current_user)):
    """Get current user profile"""
    try:
        user_response = User(
            id=current_user["id"],
            name=current_user["name"],
            email=current_user["email"],
            created_at=current_user["created_at"]
        )
        return user_response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get profile: {str(e)}")

@app.post("/api/contact")
async def submit_contact_message(message_data: ContactMessage):
    """Submit contact form message"""
    try:
        # Store contact message in database
        contact_message = {
            "id": str(uuid.uuid4()),
            "name": message_data.name,
            "email": message_data.email,
            "message": message_data.message,
            "created_at": datetime.utcnow(),
            "status": "new"
        }
        
        result = db.contact_messages.insert_one(contact_message)
        
        if not result.inserted_id:
            raise HTTPException(status_code=500, detail="Failed to submit message")
        
        return {
            "message": "Thank you! Your message has been submitted successfully.",
            "id": contact_message["id"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit message: {str(e)}")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db.command('ismaster')
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")

@app.get("/api/services")
async def get_services():
    """Get available services information"""
    services = [
        {
            "id": "telecom",
            "name": "Telecom Provider",
            "description": "Advanced telecommunications infrastructure and connectivity solutions",
            "features": [
                "Network Infrastructure",
                "VoIP Solutions",
                "Enterprise Communications",
                "5G Implementation"
            ]
        },
        {
            "id": "cloud",
            "name": "Cloud Services",
            "description": "Scalable cloud infrastructure and migration services",
            "features": [
                "Cloud Migration",
                "Infrastructure as a Service",
                "Platform as a Service",
                "Cloud Security"
            ]
        },
        {
            "id": "marketing",
            "name": "Digital Marketing",
            "description": "Data-driven digital marketing strategies and brand building",
            "features": [
                "SEO Optimization",
                "Social Media Marketing",
                "Content Strategy",
                "Analytics & Reporting"
            ]
        }
    ]
    
    return {"services": services}

@app.get("/api/partners")
async def get_partners():
    """Get partner companies information"""
    partners = [
        {
            "id": "tata-tele",
            "name": "Tata Tele",
            "description": "Leading telecommunications provider in India",
            "industry": "Telecommunications",
            "partnership_since": "2020"
        },
        {
            "id": "jio",
            "name": "Jio",
            "description": "Digital services and connectivity leader",
            "industry": "Digital Services",
            "partnership_since": "2021"
        },
        {
            "id": "vi",
            "name": "VI (Vodafone Idea)",
            "description": "Major telecommunications operator",
            "industry": "Telecommunications",
            "partnership_since": "2019"
        },
        {
            "id": "microsoft",
            "name": "Microsoft",
            "description": "Global leader in cloud and technology solutions",
            "industry": "Technology",
            "partnership_since": "2018"
        }
    ]
    
    return {"partners": partners}

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {"error": "Endpoint not found", "status_code": 404}

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return {"error": "Internal server error", "status_code": 500}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)