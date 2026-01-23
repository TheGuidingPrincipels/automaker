# Project Notes

## Authentication Ideas

JWT tokens should be validated on every request. Consider implementing:

- Token refresh mechanism
- Blacklist for revoked tokens

## Database Schema

The users table needs these fields:

- id (UUID)
- email (unique)
- password_hash
- created_at

## Random Thoughts

Remember to review the API rate limiting approach next week.
