# Authentication API Endpoints

This document provides information about the direct authentication endpoints available in the backend API.

## Overview

The MovieLens Recommender now includes direct authentication endpoints for user registration and login. These endpoints interact with Supabase Auth behind the scenes while providing a simple REST API interface.

Key features:
- User registration with email/password
- User login with email/password
- Automatic data pipeline trigger on first registration

## Endpoints

### Register a New User

**Endpoint:** `POST /api/auth/register`

**Description:** Creates a new user in Supabase Auth and triggers the data pipeline process if it's the first user registration.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword",
  "full_name": "John Doe"  // Optional
}
```

**Success Response (201 Created):**
```json
{
  "message": "Registration successful. Please check your email for verification.",
  "user_id": "a1b2c3d4-e5f6-7890-1234-abcdef123456",
  "email": "user@example.com"
}
```

**Error Responses:**
- `409 Conflict`: User already exists
- `400 Bad Request`: Invalid request or registration failed
- `422 Unprocessable Entity`: Validation error (password too short, invalid email, etc.)

### User Login

**Endpoint:** `POST /api/auth/login`

**Description:** Authenticates a user and returns session tokens.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```

**Success Response (200 OK):**
```json
{
  "session": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "long_opaque_refresh_token_string",
    "token_type": "bearer",
    "expires_in": 3600
  },
  "user": {
    "id": "a1b2c3d4-e5f6-7890-1234-abcdef123456",
    "email": "user@example.com",
    "full_name": "John Doe",  // If provided during registration
    "avatar_url": null,
    "roles": ["authenticated"]
  }
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid email or password

## Testing with cURL

You can test these endpoints using cURL commands:

### Register:
```bash
curl -X POST https://your-api-url/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123","full_name":"Test User"}'
```

### Login:
```bash
curl -X POST https://your-api-url/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```

### Using the Access Token:
```bash
curl -X GET https://your-api-url/api/recommendations/user/your-user-id \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Data Pipeline Trigger

Upon successful registration, if this is the first user in the system, the backend will automatically trigger an asynchronous data pipeline process that:

1. Downloads the MovieLens Small dataset
2. Processes the movies and ratings data
3. Generates embeddings using Hugging Face Sentence Transformers
4. Loads the processed data into MongoDB

This process runs in a separate Google Cloud Function and may take a few minutes to complete.

## Notes

- In production, consider enabling email verification.
- This implementation uses Supabase Auth behind the scenes, but provides a direct API for applications that prefer a simpler REST interface.
- The JWT tokens from Supabase Auth are compatible with all protected endpoints in the API. 