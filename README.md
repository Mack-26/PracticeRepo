# Gmail Analytics Web Application

A web application that provides analytics for your Gmail account, including email metrics, top senders, and time distribution analysis.

## Features

- Gmail OAuth2 authentication
- Email metrics analysis
- Top senders analysis
- Time distribution analysis
- Email size distribution
- Modern and responsive UI

## Prerequisites

- Python 3.8+
- Node.js 14+
- PostgreSQL
- Google Cloud Platform account with Gmail API enabled

## Setup

### Backend Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy the environment file and update the values:
```bash
cp backend/.env.example backend/.env
```

4. Update the `.env` file with your Google OAuth2 credentials and database configuration.

5. Run the backend server:
```bash
cd backend
uvicorn main:app --reload
```

### Frontend Setup

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Start the development server:
```bash
npm start
```

## API Endpoints

- `GET /auth/google` - Initiate Google OAuth2 flow
- `GET /auth/google/callback` - OAuth2 callback endpoint
- `GET /api/analytics` - Get email analytics
- `GET /api/analytics/top-senders` - Get top email senders
- `GET /api/analytics/time-distribution` - Get email time distribution

## Security

- All API endpoints are protected with OAuth2 authentication
- Sensitive data is stored securely in environment variables
- CORS is configured to allow requests only from the frontend application

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 