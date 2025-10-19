# SwinSACA Backend API

A Flask-based REST API with JWT authentication for the SwinSACA medical triage application.

## Features

- User registration and login
- JWT-based authentication
- MySQL database integration (phpMyAdmin compatible)
- Swagger API documentation
- CORS support for frontend integration

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file based on `env_example.txt`:
```bash
cp env_example.txt .env
```

3. Update the `.env` file with your database credentials:
```
DATABASE_URL=mysql+pymysql://your_username:your_password@localhost/your_database_name
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=jwt-secret-string
```

4. Create the database in phpMyAdmin:
```sql
CREATE DATABASE your_database_name;
```

5. Run the application:
```bash
python app.py
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:5000/api/swagger/
- API Base URL: http://localhost:5000/api/

## Endpoints

### Authentication
- `POST /api/auth/register` - Register a new user
- `POST /api/auth/login` - Login user
- `GET /api/auth/profile` - Get user profile (requires JWT)
- `PUT /api/auth/profile` - Update user profile (requires JWT)
- `GET /api/auth/verify` - Verify JWT token

## Database Schema

The `users` table includes:
- id (Primary Key)
- username (Unique)
- email (Unique)
- password_hash
- first_name
- last_name
- is_active
- created_at
- updated_at

## Security Features

- Password hashing using Werkzeug
- JWT token authentication
- Input validation
- CORS configuration
- SQL injection protection via SQLAlchemy ORM

