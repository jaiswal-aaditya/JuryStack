# Architecture

JuryStack is a three-service modular monolith. Nginx is the only host-facing
service on port 8080, serving the React build and forwarding `/api` to FastAPI.
FastAPI owns validation, authentication, authorization, transactions, scoring,
exports, fixture loading, and OpenAPI. PostgreSQL is the only persistent store.

Backend packages are divided into `auth`, `events`, `teams`, `projects`,
`judging`, `results`, `audit`, and shared `core`. Future routes should validate
transport data and call services; services own use cases and transaction
boundaries; repositories own SQLAlchemy queries.

This document is a scaffold placeholder. Material architectural decisions will
be recorded under `docs/adr/` as implementation proceeds.
