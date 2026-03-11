# Backend Architecture
## Core Responsibility

The API is the "brain" behind the HappyRobot agent. It does three things: **verifies carriers**, **searches loads**, and **records call outcomes** for the dashboard. The HappyRobot workflow calls it via webhook tool nodes.

## Tech Stack (FastAPI + SQLite + Docker)

- **FastAPI** gives you automatic OpenAPI docs (useful for your demo and the build description), async support, and Pydantic models for clean validation. 
- **SQLite** keeps things simple — no separate database container, single file, zero config. Use SQLAlchemy as the ORM so the DB layer is swappable for Postgres if needed.
- **Docker + Railway** for containerization and deployment.