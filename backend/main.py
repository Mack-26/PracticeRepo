from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os
from dotenv import load_dotenv
from utils.gmail_utils import GmailAnalytics
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Gmail Analytics API")

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OAuth2 configuration
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send"
]

# After loading environment variables
print(f"CLIENT_ID loaded: {CLIENT_ID is not None}")
print(f"CLIENT_SECRET loaded: {CLIENT_SECRET is not None}")
print(f"REDIRECT_URI: {REDIRECT_URI}")

# After loading environment variables
if not all([CLIENT_ID, CLIENT_SECRET, REDIRECT_URI]):
    missing = []
    if not CLIENT_ID: missing.append("GOOGLE_CLIENT_ID")
    if not CLIENT_SECRET: missing.append("GOOGLE_CLIENT_SECRET")
    if not REDIRECT_URI: missing.append("GOOGLE_REDIRECT_URI")
    raise ValueError(f"Missing environment variables: {', '.join(missing)}")

# Initialize OAuth2 flow
flow = Flow.from_client_config(
    {
        "web": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI],
        }
    },
    scopes=SCOPES,
)

# Token storage (in production, use a proper database)
tokens = {}

@app.get("/auth/google/callback")
async def google_auth_callback(code: str):
    try:
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Store the full credentials (including refresh token)
        token_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        
        # In production, you'd want to associate this with the user
        tokens['current_user'] = token_data
        
        return {"access_token": credentials.token, "refresh_token": credentials.refresh_token}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error during authentication: {str(e)}"
        )

async def get_credentials():
    try:
        # Get stored token data
        token_data = tokens.get('current_user')
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No credentials found"
            )
        
        # Recreate credentials object
        credentials = Credentials(
            token=token_data['token'],
            refresh_token=token_data['refresh_token'],
            token_uri=token_data['token_uri'],
            client_id=token_data['client_id'],
            client_secret=token_data['client_secret'],
            scopes=token_data['scopes']
        )
        
        # Refresh if expired
        if not credentials.valid:
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
                # Update stored token
                tokens['current_user']['token'] = credentials.token
        
        return credentials
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid credentials: {str(e)}"
        )
    
@app.get("/")
async def root():
    return {"message": "Welcome to Gmail Analytics API"}

@app.get("/api/verify-token")
async def verify_token(credentials: Credentials = Depends(get_credentials)):
    try:
        service = build("gmail", "v1", credentials=credentials)
        profile = service.users().getProfile(userId='me').execute()
        return {
            "valid": True,
            "email": profile.get('emailAddress'),
            "messages_total": profile.get('messagesTotal', 0),
            "threads_total": profile.get('threadsTotal', 0)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {str(e)}"
        )
    
@app.get("/auth/google")
async def google_auth():
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )
    return {"authorization_url": authorization_url}

@app.get("/auth/google/callback")
async def google_auth_callback(code: str):
    try:
        flow.fetch_token(code=code)
        credentials = flow.credentials
        return {"access_token": credentials.token}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error during authentication: {str(e)}"
        )

@app.get("/api/analytics")
async def get_gmail_analytics(days: int = 30, credentials: Credentials = Depends(get_credentials)):
    try:
        analytics = GmailAnalytics(credentials)
        metrics = analytics.get_email_metrics(days)
        return metrics
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching analytics: {str(e)}"
        )

class EmailRequest(BaseModel):
    to: str
    subject: str
    body: str

class ReplyRequest(BaseModel):
    message_id: str
    body: str

@app.post("/api/send-email")
async def send_email(
    request: EmailRequest,
    credentials: Credentials = Depends(get_credentials)
):
    try:
        analytics = GmailAnalytics(credentials)
        result = analytics.send_email(request.to, request.subject, request.body)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending email: {str(e)}"
        )

@app.post("/api/reply-email")
async def reply_email(
    request: ReplyRequest,
    credentials: Credentials = Depends(get_credentials)
):
    try:
        analytics = GmailAnalytics(credentials)
        result = analytics.reply_to_email(request.message_id, request.body)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error replying to email: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 