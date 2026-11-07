# Chess Review Engine

It aint that serious bro; i was bored so i made it a few hours (claude did). 

A locally-deployed chess review engine that fetches your chess.com games and analyzes them with the Stockfish engine. Browse your games, view move-by-move evaluations, performance ratings, evaluation graphs, and learning insights — all running in Docker with no external dependencies beyond the chess.com public API.

## Features

- **Game Fetching** — Load all your chess.com games by username, or a single game by URL
- **Stockfish Analysis** — Every move evaluated at depth 20 with move classifications (best, excellent, good, inaccuracy, mistake, blunder)
- **Best Move Suggestions** — See the top 3 engine moves at each position alongside your actual move
- **Performance Rating** — Track your estimated ELO throughout the game
- **Evaluation Graph** — Visualize position advantage across the entire game with critical-moment markers
- **Learning Insights** — Get explanations for suboptimal moves with principal variation lines

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (with Docker Compose)

### Run the App

```bash
docker compose up
```

This builds and starts the frontend and backend containers. The UI will be accessible at **http://localhost:3000** within about two minutes.

### Configure the Port

The frontend port defaults to `3000`. To use a different port, set the `FRONTEND_PORT` environment variable:

```bash
FRONTEND_PORT=8080 docker compose up
```

The UI will then be available at **http://localhost:8080**.

You can also create a `.env` file in the project root (see `.env.example`):

```env
FRONTEND_PORT=8080
```

### Stop the App

```bash
docker compose down
```

This stops and removes all running containers and their associated networks.

## Architecture

| Service   | Technology           | Container              | Internal Port |
|-----------|----------------------|------------------------|---------------|
| Frontend  | React + TypeScript   | `chess-engine-frontend` | 80 (Nginx)   |
| Backend   | Python + FastAPI     | `chess-engine-backend`  | 8000         |
| Stockfish | Stockfish 17 binary  | (inside backend)       | —            |

The frontend Nginx container proxies `/api` requests to the backend. Stockfish runs as a subprocess inside the backend container to avoid network overhead for UCI communication.

## Development

### Backend

```bash
cd backend
pip install -e ".[dev]"
pytest
```

### Frontend

```bash
cd frontend
npm install
npm run dev     # Dev server at http://localhost:5173
npm test        # Run Vitest tests
```

### Smoke Tests

Docker deployment smoke tests live in `tests/test_docker_smoke.py`. They require Docker and are marked with `@pytest.mark.docker`:

```bash
pip install pytest
pytest tests/test_docker_smoke.py -m docker -v
```

These tests build and run the full Docker stack, so they take a few minutes.
