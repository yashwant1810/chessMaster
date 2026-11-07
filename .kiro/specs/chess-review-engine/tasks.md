# Implementation Plan: Chess Review Engine

## Overview

Implementation of a containerized chess review engine with a React/TypeScript frontend and Python/FastAPI backend. The system fetches games from chess.com, analyzes them with Stockfish, and presents move-by-move analysis with classifications, performance ratings, evaluation graphs, and learning insights. All services are orchestrated via Docker Compose for single-command local deployment.

## Tasks

- [x] 1. Set up project structure and core types
  - [x] 1.1 Initialize backend Python project with FastAPI
    - Create `backend/` directory with `pyproject.toml` including dependencies: `fastapi`, `uvicorn`, `python-chess`, `httpx`
    - Add dev dependencies: `pytest`, `hypothesis`, `httpx[test]`
    - Set up `backend/app/` package with `__init__.py` and `main.py` entry point
    - Configure pytest in `pyproject.toml`
    - _Requirements: 12.1_

  - [x] 1.2 Initialize frontend React/TypeScript project
    - Scaffold with Vite: `npm create vite@latest frontend -- --template react-ts`
    - Install dependencies: `react-chessboard`, `chess.js`, `recharts`
    - Install dev dependencies: `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `fast-check`, `jsdom`
    - Configure Vitest in `vite.config.ts`
    - _Requirements: 12.1_

  - [x] 1.3 Define backend domain models and enums
    - Create `backend/app/models.py` with all dataclasses: `ParsedGame`, `GameSummary`, `PositionEvaluation`, `CandidateMove`, `AnalyzedMove`, `LearningInsight`, `GameAnalysis`, `PlayerAnalysisSummary`, `AnalysisStatus`
    - Define enums: `MoveClassification` (best, excellent, good, inaccuracy, mistake, blunder) and `GameResult` (win, loss, draw)
    - _Requirements: 4.1, 5.1, 6.1, 6.2, 8.1, 9.1_

  - [x] 1.4 Define frontend TypeScript interfaces and types
    - Create `frontend/src/types/index.ts` with interfaces: `GameSummary`, `GameAnalysis`, `AnalyzedMove`, `PositionEvaluation`, `CandidateMove`, `LearningInsight`, `PlayerAnalysisSummary`, `AnalysisStatus`, `FetchResult`
    - Define `MoveClassification` and `GameResult` enums
    - Define `ChessReviewAPI` interface with all API method signatures
    - Define `SortField` and `SortOrder` types
    - _Requirements: 3.2, 5.5, 6.3, 7.1, 8.2, 9.3_

  - [x] 1.5 Create SQLite schema and database access layer
    - Create `backend/app/database.py` with schema initialization
    - Implement `games`, `analysis_results`, and `analysis_summaries` tables with indexes per design schema
    - Implement CRUD functions: `insert_game`, `get_game`, `list_games`, `insert_analysis_result`, `get_analysis`, `upsert_analysis_summary`
    - Wrap write operations in transactions with single retry on failure
    - _Requirements: 1.2, 2.2, 5.1_

- [x] 2. Implement PGN parsing and input validation
  - [x] 2.1 Implement PGN parser and formatter using python-chess
    - Create `backend/app/services/pgn_parser.py`
    - Implement `parse_pgn(pgn_string: str) -> ParsedGame` extracting Seven Tag Roster, additional headers, SAN move list, comments, and FEN per half-move via `chess.pgn`
    - Implement `format_pgn(game: ParsedGame) -> str` producing PGN export format
    - Return error with move number or header name on malformed PGN input
    - Return error indicating no moves found when PGN contains empty move section
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 2.2 Implement username and game URL validators
    - Create `backend/app/services/validators.py`
    - Implement `validate_username(username: str) -> ValidationResult` rejecting empty strings and strings exceeding 25 characters
    - Implement `validate_game_url(url: str) -> ValidationResult` rejecting strings not matching the chess.com game URL pattern
    - Return structured `ValidationResult` with `is_valid`, `error_code`, `error_message`
    - _Requirements: 1.6, 2.3_

  - [x] 2.3 Write property test for PGN round-trip fidelity
    - **Property 1: PGN Round-Trip Fidelity**
    - Create `backend/tests/test_pgn_roundtrip_property.py`
    - Generate random valid PGN games using Hypothesis strategies for move sequences, headers, and comments
    - Assert: parse → format → re-parse produces identical move sequence, Seven Tag Roster values, additional headers, and comments
    - Minimum 100 iterations
    - **Validates: Requirements 4.1, 4.2, 4.3**

  - [x] 2.4 Write property test for malformed PGN error reporting
    - **Property 2: Malformed PGN Error Reporting**
    - Create `backend/tests/test_pgn_malformed_property.py`
    - Generate random invalid PGN strings: corrupt move notation, missing required headers, truncated data
    - Assert: parser returns error (not success) with location info (move number or header name)
    - Minimum 100 iterations
    - **Validates: Requirements 4.4**

  - [x] 2.5 Write property test for username validation
    - **Property 5: Username Validation Rejects Invalid Input**
    - Create `backend/tests/test_username_validation_property.py`
    - Generate random strings of varying lengths (0–100) with Hypothesis
    - Assert: empty or >25 chars → rejected; 1–25 chars → accepted
    - Minimum 100 iterations
    - **Validates: Requirements 1.6**

  - [x] 2.6 Write property test for URL validation
    - **Property 6: URL Validation Rejects Invalid Format**
    - Create `backend/tests/test_url_validation_property.py`
    - Generate random strings and valid-but-wrong URL formats with Hypothesis
    - Assert: non-matching URLs → rejected with error
    - Minimum 100 iterations
    - **Validates: Requirements 2.3**

- [x] 3. Implement Game Fetcher service
  - [x] 3.1 Implement chess.com API client with httpx
    - Create `backend/app/services/chess_api_client.py`
    - Configure `httpx.AsyncClient` with 30-second timeout per request
    - Implement `get_player_archives(username: str)` calling `/pub/player/{user}/games/archives`
    - Implement `get_monthly_games(archive_url: str)` fetching games from monthly archive endpoint
    - Implement `get_game_by_url(url: str)` fetching a single game
    - Map HTTP 404 to username/game-not-found errors; network errors and timeouts to connection-failed errors
    - _Requirements: 1.1, 1.5, 2.1, 2.5_

  - [x] 3.2 Implement fetch_profile_games with progress tracking
    - Create `backend/app/services/game_fetcher.py` with `GameFetcher` class
    - Implement `fetch_profile_games(username: str) -> FetchResult` fetching up to 10,000 most recent games from chess.com
    - Validate username before fetching; parse each game's PGN via pgn_parser; store in database
    - Track progress (archives processed / total archives) for SSE streaming
    - Handle empty game list (username exists but no games)
    - Handle username not found on chess.com
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.7, 1.8, 1.9_

  - [x] 3.3 Implement fetch_game_by_url
    - Add `fetch_game_by_url(url: str) -> FetchResult` to `GameFetcher` class
    - Validate URL format before fetching
    - Parse PGN and store in database; return structured error if PGN parsing fails
    - Return confirmation on success; handle game-not-found and connection-failed errors
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

  - [x] 3.4 Write unit tests for Game Fetcher
    - Create `backend/tests/test_game_fetcher.py`
    - Test fetch_profile_games with mocked chess.com API responses (valid games, empty list)
    - Test fetch_game_by_url with valid URL, invalid URL, nonexistent game
    - Test error scenarios: HTTP 404, 30s timeout, empty game list, PGN parse failure
    - _Requirements: 1.1, 1.5, 1.6, 1.7, 1.8, 2.1, 2.4, 2.5, 2.7_

- [x] 4. Checkpoint - Ensure backend foundation tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement Review Engine core
  - [x] 5.1 Implement Stockfish UCI interface via python-chess
    - Create `backend/app/services/stockfish_engine.py`
    - Implement `StockfishEngine` class wrapping `chess.engine.SimpleEngine.popen_uci()`
    - Implement `evaluate_position(fen: str, depth: int = 20, multi_pv: int = 3) -> PositionEvaluation`
    - Return centipawn score from White's perspective, or mate-in-N indicator
    - Return up to 3 candidate moves ranked by evaluation via MultiPV
    - Mark invalid positions as errors instead of crashing
    - Manage engine lifecycle: startup, reuse across analyses, restart on unexpected termination
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.7_

  - [x] 5.2 Implement move classification logic
    - Create `backend/app/services/move_classifier.py`
    - Implement `classify_move(centipawn_loss: int) -> MoveClassification` with thresholds: 0→best, 1–10→excellent, 11–30→good, 31–80→inaccuracy, 81–200→mistake, 201+→blunder
    - Implement `compute_classification_summary(moves: list[AnalyzedMove], is_white: bool) -> dict` aggregating counts per classification for a single player
    - Handle missing centipawn loss by returning None classification
    - _Requirements: 6.1, 6.2, 6.4, 6.5_

  - [x] 5.3 Implement performance rating computation
    - Create `backend/app/services/performance_rating.py`
    - Implement `compute_performance_rating(centipawn_losses: list[int]) -> int` returning cumulative rating as whole integer in [0, 3000]
    - Implement `compute_cumulative_ratings(centipawn_losses: list[int]) -> list[int]` returning rating after each move for the performance graph
    - _Requirements: 8.1_

  - [x] 5.4 Implement learning insight generation
    - Create `backend/app/services/insight_generator.py`
    - Implement `generate_insight(move_number, is_white, played_move, best_move, centipawn_loss, classification, principal_variation) -> LearningInsight` for moves classified as inaccuracy, mistake, or blunder
    - Include centipawn loss, suggested best move in SAN, and principal variation line of up to 5 moves
    - Implement `generate_learning_summary(moves: list[AnalyzedMove]) -> list[LearningInsight]` collecting all suboptimal move insights, excluding best/excellent/good
    - _Requirements: 9.1, 9.2, 9.4_

  - [x] 5.5 Implement full game analysis orchestration
    - Create `backend/app/services/review_engine.py` with `ReviewEngine` class
    - Implement `analyze_game(game_id: str) -> GameAnalysis`: load game from DB → iterate positions → evaluate each with Stockfish at depth ≥ 20 → classify moves → compute performance ratings → generate insights → store results → return complete analysis
    - Track progress (positions analyzed / total) for SSE streaming
    - Skip invalid positions and mark as error in results
    - Compute per-player `PlayerAnalysisSummary` with classification counts and cumulative performance ratings
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 6.1, 6.2, 6.4, 8.1, 9.1_

  - [x] 5.6 Write property test for move classification thresholds
    - **Property 3: Move Classification Threshold Correctness**
    - Create `backend/tests/test_classification_property.py`
    - Generate random non-negative integers as centipawn loss with Hypothesis
    - Assert: exactly one classification per value; classification matches defined thresholds
    - Minimum 100 iterations
    - **Validates: Requirements 6.1, 6.2**

  - [x] 5.7 Write property test for classification summary aggregation
    - **Property 4: Classification Summary Aggregation**
    - Create `backend/tests/test_summary_property.py`
    - Generate random lists of AnalyzedMove with random classifications for two players
    - Assert: per-player classification counts equal actual occurrences in move list
    - Minimum 100 iterations
    - **Validates: Requirements 6.4**

  - [x] 5.8 Write property test for performance rating range
    - **Property 10: Performance Rating Range Invariant**
    - Create `backend/tests/test_performance_rating_property.py`
    - Generate random sequences of non-negative centipawn losses (0–500) with Hypothesis
    - Assert: every cumulative rating is a whole integer in [0, 3000]
    - Minimum 100 iterations
    - **Validates: Requirements 8.1**

  - [x] 5.9 Write property test for learning insight completeness
    - **Property 11: Learning Insight Completeness**
    - Create `backend/tests/test_insight_property.py`
    - Generate random moves classified as inaccuracy, mistake, or blunder with centipawn loss, best move, and PV
    - Assert: insight contains centipawn loss, best move in SAN, and PV of ≤ 5 moves
    - Minimum 100 iterations
    - **Validates: Requirements 9.1, 9.2**

  - [x] 5.10 Write property test for learning summary completeness
    - **Property 12: Learning Summary Includes All Suboptimal Moves**
    - Create `backend/tests/test_learning_summary_property.py`
    - Generate random analysis results with mixed classifications
    - Assert: summary lists exactly inaccuracy/mistake/blunder moves with explanations; excludes best/excellent/good
    - Minimum 100 iterations
    - **Validates: Requirements 9.4**

- [x] 6. Implement backend API layer
  - [x] 6.1 Implement game fetching endpoints
    - Create `backend/app/routers/games.py`
    - `POST /api/games/fetch-profile` — validate username, call `GameFetcher.fetch_profile_games`, return game count and status
    - `POST /api/games/fetch-url` — validate URL, call `GameFetcher.fetch_game_by_url`, return confirmation or error
    - `GET /api/games` — list fetched games with optional `sort_by` (date, result, time_control) and `order` (asc, desc) query params, default sort by date descending
    - `GET /api/games/{game_id}` — return single game details
    - _Requirements: 1.1, 1.3, 1.4, 1.6, 1.7, 1.8, 2.1, 2.3, 2.4, 2.6, 2.7, 3.1, 3.4, 3.5_

  - [x] 6.2 Implement analysis endpoints
    - Create `backend/app/routers/analysis.py`
    - `POST /api/analysis/{game_id}` — start analysis, return 409 if already in progress
    - `GET /api/analysis/{game_id}` — return analysis results, 404 if not yet analyzed
    - `GET /api/analysis/{game_id}/status` — return progress percentage and completion flag
    - _Requirements: 5.1, 5.5, 5.6_

  - [x] 6.3 Implement SSE streaming endpoints
    - Create `backend/app/routers/streams.py`
    - `GET /api/stream/fetch/{username}` — SSE stream for game fetching progress
    - `GET /api/stream/analysis/{game_id}` — SSE stream for analysis progress with positions analyzed percentage
    - Use `StreamingResponse` with `text/event-stream` content type
    - _Requirements: 1.9, 5.5_

  - [x] 6.4 Implement error handling and CORS middleware
    - Create `backend/app/middleware.py`
    - Add global exception handler mapping domain errors to HTTP status codes per design error table (400, 404, 409, 422, 502, 504)
    - Add CORS middleware allowing frontend origin
    - Wire all routers (`games`, `analysis`, `streams`) into `main.py`
    - _Requirements: 1.5, 1.6, 1.8, 2.3, 2.4, 2.5, 4.4, 4.5, 5.7, 6.5_

  - [x] 6.5 Write unit tests for API endpoints
    - Create `backend/tests/test_api.py`
    - Test game fetch endpoints with mocked services: valid username, invalid username, not found
    - Test analysis endpoints: start analysis, get status, get results, 409 conflict
    - Test error responses: invalid username (400), invalid URL (400), not found (404), timeout (504)
    - Use FastAPI `TestClient`
    - _Requirements: 1.5, 1.6, 1.8, 2.3, 2.4, 2.5_

- [x] 7. Checkpoint - Ensure full backend tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Implement frontend core and game list
  - [x] 8.1 Set up App shell with routing and global state
    - Create `frontend/src/App.tsx` with route definitions: home (`/`), analysis (`/analysis/:gameId`)
    - Set up React context for global state: current username, fetched games list
    - Create layout with header and main content area
    - _Requirements: 3.3_

  - [x] 8.2 Implement ProfileInput component with validation
    - Create `frontend/src/components/ProfileInput.tsx`
    - Accept chess.com username or game URL input
    - Client-side validation: non-empty, max 25 chars for username; URL pattern match for game URL
    - Display loading state during fetch; show inline error messages on failure
    - Call appropriate API method based on input type
    - _Requirements: 1.6, 2.3, 2.6_

  - [x] 8.3 Implement ProgressIndicator component
    - Create `frontend/src/components/ProgressIndicator.tsx`
    - Accept `progress: number` and `type: 'fetch' | 'analysis'` props
    - Display progress bar with percentage for analysis; activity indicator for fetch
    - _Requirements: 1.9, 5.5, 5.6_

  - [x] 8.4 Implement GameList and GameListItem components with sorting
    - Create `frontend/src/components/GameList.tsx` and `frontend/src/components/GameListItem.tsx`
    - Display scrollable list sorted by date (most recent first) by default
    - Each item shows: date played, opponent username, result (from fetched player's perspective), time control, opening name
    - Display "unavailable" placeholder for missing metadata fields
    - Sort controls for date, result, time control in ascending and descending order
    - Navigate to analysis view on game selection
    - Display "no games available" message when list is empty
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x] 8.5 Implement frontend API client with SSE support
    - Create `frontend/src/api/client.ts` implementing `ChessReviewAPI` interface
    - Implement all REST API call methods with shared error interceptor
    - Implement SSE connections for fetch and analysis progress with exponential backoff reconnection (1s, 2s, 4s, max 30s)
    - Show toast notifications on network and timeout errors
    - _Requirements: 1.9, 5.5_

  - [x] 8.6 Write property test for game list sort correctness
    - **Property 7: Game List Sort Correctness**
    - Create `frontend/src/__tests__/gameListSort.property.test.ts`
    - Generate random game summary arrays using fast-check
    - Apply each sort field (date, result, time control) and order (ascending, descending)
    - Assert: output contains same games as input; consecutive pairs satisfy ordering
    - Minimum 100 iterations
    - **Validates: Requirements 3.1, 3.4**

  - [x] 8.7 Write property test for game list item completeness
    - **Property 8: Game List Item Completeness**
    - Create `frontend/src/__tests__/gameListItem.property.test.ts`
    - Generate random GameSummary objects with optional null fields using fast-check
    - Assert: all present fields rendered; all null fields show "unavailable" placeholder
    - Minimum 100 iterations
    - **Validates: Requirements 3.2, 3.6**

- [x] 9. Implement frontend analysis view
  - [x] 9.1 Implement ChessBoard with EvaluationBar
    - Create `frontend/src/components/ChessBoard.tsx`
    - Render 8×8 board using `react-chessboard` with FEN-based positioning
    - Display visually distinct pieces for all 6 types (king, queen, rook, bishop, knight, pawn) in both colors
    - Highlight best move origin/destination squares when player's move differs from top candidate, using a style distinct from the player's move
    - Create `frontend/src/components/EvaluationBar.tsx` adjacent to board
    - Display centipawn advantage: positive → White, negative → Black
    - Show max extent for checkmate positions
    - _Requirements: 7.2, 10.1, 10.5, 10.6_

  - [x] 9.2 Implement MoveNavigator with keyboard support
    - Create `frontend/src/components/MoveNavigator.tsx`
    - Provide first-move, previous-move, next-move, and last-move buttons
    - Update board position within 100ms on navigation
    - Support keyboard: left arrow → previous-move, right arrow → next-move
    - Disable first/previous at initial position; disable next/last at final position
    - _Requirements: 10.2, 10.3, 10.4, 10.7, 10.8_

  - [x] 9.3 Implement MoveList with classification indicators
    - Create `frontend/src/components/MoveList.tsx`
    - Display tabular move list with move number, White move, Black move
    - Show one unique color-coded icon per classification category (6 distinct colors and icon shapes)
    - Highlight current move; navigate to move on click
    - Display "classification unavailable" indicator when classification is missing
    - _Requirements: 6.3, 6.5_

  - [x] 9.4 Implement CandidateMoves component
    - Create `frontend/src/components/CandidateMoves.tsx`
    - Display up to 3 candidate moves in descending evaluation order using SAN notation
    - Show centipawn evaluation for each candidate and for the player's actual move
    - Visually mark the player's move if it appears in the candidate list
    - Display fewer candidates when position has fewer than 3 legal moves
    - _Requirements: 7.1, 7.3, 7.4_

  - [x] 9.5 Implement InsightPanel and learning summary
    - Create `frontend/src/components/InsightPanel.tsx`
    - Display insight for inaccuracy/mistake/blunder moves: centipawn loss, best move, principal variation line, explanation text
    - Clear panel when navigating to best/excellent/good moves
    - Create `frontend/src/components/LearningSummary.tsx` listing all suboptimal moves with explanations
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

  - [x] 9.6 Implement GameSummary component
    - Create `frontend/src/components/GameSummary.tsx`
    - Display classification counts per category for both players
    - Display final performance rating for each player
    - Display message indicating performance data requires completed analysis when data is unavailable
    - _Requirements: 6.4, 8.3, 8.4_

  - [x] 9.7 Wire AnalysisView container component
    - Create `frontend/src/components/AnalysisView.tsx`
    - Compose: ChessBoard, EvaluationBar, MoveNavigator, MoveList, CandidateMoves, InsightPanel, GameSummary, EvaluationGraph, PerformanceGraph
    - Manage analysis state: fetch analysis on mount, subscribe to SSE for progress during analysis
    - Atomically replace ProgressIndicator with analysis-complete indicator (never show both simultaneously)
    - Synchronize current move index across all child components
    - _Requirements: 5.5, 5.6, 10.1_

  - [x] 9.8 Write property test for candidate moves display correctness
    - **Property 9: Candidate Moves Display Correctness**
    - Create `frontend/src/__tests__/candidateMoves.property.test.ts`
    - Generate random candidate move arrays with evaluations using fast-check
    - Assert: displays min(N, 3) candidates in descending eval order; shows eval for each; marks player's move if present
    - Minimum 100 iterations
    - **Validates: Requirements 7.1, 7.3, 7.4**

- [x] 10. Implement frontend graphs
  - [x] 10.1 Implement EvaluationGraph with click navigation and critical moment markers
    - Create `frontend/src/components/EvaluationGraph.tsx` using Recharts `LineChart`
    - Plot centipawn evaluations on Y-axis (clamped to ±2000) vs move number on X-axis
    - Represent mate-in-N evaluations at ±2000 boundary (positive for White mate, negative for Black mate)
    - Navigate board to nearest move position on graph click
    - Display distinct markers (different color or shape) where evaluation changes by >100cp between consecutive moves
    - Show position indicator for current move on graph
    - Omit positions with unavailable evaluation data; connect nearest evaluated positions preserving move-number mapping
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

  - [x] 10.2 Implement PerformanceGraph for both players
    - Create `frontend/src/components/PerformanceGraph.tsx` using Recharts `LineChart`
    - Plot performance rating (Y-axis) vs move number (X-axis) for both White and Black
    - Use distinct line colors/styles for each player
    - _Requirements: 8.2_

  - [x] 10.3 Write property test for evaluation graph clamping
    - **Property 13: Evaluation Graph Clamping**
    - Create `frontend/src/__tests__/evalGraphClamping.property.test.ts`
    - Generate random integers and mate-in-N values using fast-check
    - Assert: all values clamped to [−2000, +2000]; mate-in-N displayed at ±2000 boundary
    - Minimum 100 iterations
    - **Validates: Requirements 11.1**

  - [x] 10.4 Write property test for critical moment detection
    - **Property 14: Critical Moment Detection**
    - Create `frontend/src/__tests__/criticalMoment.property.test.ts`
    - Generate random evaluation sequences using fast-check
    - Assert: marker at position i if and only if |eval[i] − eval[i−1]| > 100
    - Minimum 100 iterations
    - **Validates: Requirements 11.3**

  - [x] 10.5 Write property test for evaluation graph gap handling
    - **Property 15: Evaluation Graph Gap Handling**
    - Create `frontend/src/__tests__/evalGraphGaps.property.test.ts`
    - Generate random evaluation sequences with null gaps using fast-check
    - Assert: unavailable positions omitted; nearest evaluated positions connected; move-number mapping preserved on X-axis
    - Minimum 100 iterations
    - **Validates: Requirements 11.5**

- [x] 11. Checkpoint - Ensure frontend tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Implement Docker deployment
  - [x] 12.1 Create backend Dockerfile
    - Create `backend/Dockerfile`
    - Base image: `python:3.12-slim`
    - Install Stockfish 17 binary
    - Copy backend source and install Python dependencies
    - Expose API port and set `CMD` to run uvicorn
    - _Requirements: 12.1, 12.4_

  - [x] 12.2 Create frontend Dockerfile
    - Create `frontend/Dockerfile`
    - Multi-stage build: Node 20 for `npm run build`, Nginx for serving static files
    - Configure Nginx to serve React build and proxy `/api` requests to backend container
    - _Requirements: 12.1_

  - [x] 12.3 Create docker-compose.yml with environment configuration
    - Create `docker-compose.yml` at project root
    - Define `frontend` and `backend` services with build contexts
    - Configure frontend port via environment variable, defaulting to 3000
    - Set up internal network for inter-container communication
    - Configure Stockfish binary path as environment variable for backend
    - Log failed container startups with service identification
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_

  - [x] 12.4 Write smoke tests for Docker deployment
    - Create `tests/test_docker_smoke.py`
    - Test: `docker compose up` starts services and UI is accessible within 120 seconds
    - Test: `docker compose down` removes all containers and networks
    - Test: frontend port is configurable via environment variable
    - Test: failed container logs identify the failed service
    - _Requirements: 12.2, 12.3, 12.5, 12.6_

- [x] 13. Final checkpoint - Ensure all tests pass and system is ready
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation of backend foundation, full backend, frontend, and deployment
- Property tests validate 15 universal correctness properties defined in the design document
- Backend uses Python 3.12 with FastAPI, python-chess, httpx, Hypothesis (property tests), and pytest
- Frontend uses React 18 with TypeScript, react-chessboard, chess.js, Recharts, fast-check (property tests), and Vitest
- Stockfish 17 runs as a subprocess inside the backend container via `python-chess`'s `chess.engine` module
- SQLite is used for local persistence with no external database dependency

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["1.3", "1.4"] },
    { "id": 2, "tasks": ["1.5", "2.1", "2.2"] },
    { "id": 3, "tasks": ["2.3", "2.4", "2.5", "2.6", "3.1", "5.1"] },
    { "id": 4, "tasks": ["3.2", "5.2", "5.3", "5.4"] },
    { "id": 5, "tasks": ["3.3", "5.5"] },
    { "id": 6, "tasks": ["3.4", "5.6", "5.7", "5.8", "5.9", "5.10"] },
    { "id": 7, "tasks": ["6.1", "6.2", "6.3", "6.4"] },
    { "id": 8, "tasks": ["6.5", "8.1", "8.5"] },
    { "id": 9, "tasks": ["8.2", "8.3", "8.4"] },
    { "id": 10, "tasks": ["8.6", "8.7", "9.1", "9.2", "9.3", "9.4"] },
    { "id": 11, "tasks": ["9.5", "9.6", "10.1", "10.2"] },
    { "id": 12, "tasks": ["9.7", "9.8", "10.3", "10.4", "10.5"] },
    { "id": 13, "tasks": ["12.1", "12.2"] },
    { "id": 14, "tasks": ["12.3"] },
    { "id": 15, "tasks": ["12.4"] }
  ]
}
```
