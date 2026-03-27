# Backend (Spring Boot)

This folder contains the backend service for the privacy-preserving medical recommendation system.

## Stack

- Java 17
- Spring Boot 3
- Spring Security + JWT
- Spring Data JPA
- Flyway
- MySQL

## Quick start

1. Create a MySQL database:

```sql
CREATE DATABASE medrec CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

2. Set environment variables (PowerShell):

```powershell
$env:DB_URL="jdbc:mysql://localhost:3306/medrec?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai&characterEncoding=utf8"
$env:DB_USERNAME="root"
$env:DB_PASSWORD="root"
$env:JWT_SECRET="replace_this_with_at_least_32_bytes_secret_key"
$env:CORS_ALLOWED_ORIGINS="http://localhost:5173"
```

3. Run backend:

```powershell
mvn -f server\pom.xml spring-boot:run
```

The service runs on `http://localhost:8080`.

## Seed data

The backend auto-seeds these demo accounts on first startup:

- `admin / 123456`
- `user / 123456`

## Core APIs

- `POST /api/auth/login`
- `GET /api/auth/me`
- `GET|POST|PUT|DELETE /api/patients`
- `GET|PUT /api/privacy/config`
- `GET|DELETE /api/privacy/events`
- `POST /api/recommendations/generate`
- `GET /api/recommendations/history`
- `GET /api/admin/users`
- `PATCH /api/admin/users/{id}/status`
- `POST /api/admin/training/start`
- `GET /api/admin/training/history`
- `GET /api/dashboard/visualization`

## Notes

- Flyway migration script is at `server/src/main/resources/db/migration/V1__init.sql`.
- In this environment, Maven dependency download may be blocked by network policy. If that happens, run the same command on a machine with Maven central access.
