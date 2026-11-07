# Requirements Document

## Introduction

A local, containerized chess review engine that integrates with chess.com to fetch a user's games and analyzes them using the Stockfish open-source engine. The application provides a web-based UI for browsing games, viewing move-by-move analysis with best move suggestions, mid-game performance ratings, evaluation graphs, and learning insights to help users improve their chess skills. The entire system runs end-to-end locally via Docker with no external dependencies beyond the chess.com public API.

## Glossary

- **Review_Engine**: The backend analysis service that processes chess games using the Stockfish engine to produce evaluations, move classifications, and learning insights.
- **Game_Fetcher**: The service component responsible for retrieving game data from the chess.com public API.
- **Analysis_UI**: The web-based user interface for browsing games, navigating positions, and viewing analysis results.
- **Stockfish**: An open-source chess engine used for position evaluation and best move computation.
- **Container_Runtime**: The Docker-based runtime environment that packages and orchestrates all application services.
- **PGN**: Portable Game Notation, the standard text format for recording chess games including moves and metadata.
- **FEN**: Forsyth-Edwards Notation, a standard string format for describing a specific board position.
- **Centipawn**: A unit of positional advantage equal to one hundredth of a pawn, used by Stockfish to score positions.
- **Move_Classification**: A label assigned to each move indicating its quality: best move, excellent, good, inaccuracy, mistake, or blunder.
- **Performance_Rating**: An estimated ELO rating derived from move accuracy over a sequence of moves within a game.
- **Evaluation_Bar**: A visual indicator on the UI showing the current position's advantage for white or black.

## Requirements

### Requirement 1: Game Retrieval by Profile

**User Story:** As a chess player, I want to load all my chess.com games by entering my username, so that I can review my complete game history in one place.

#### Acceptance Criteria

1. WHEN a chess.com username is submitted, THE Game_Fetcher SHALL retrieve all available games for that username from the chess.com public API, up to a maximum of 10,000 games ordered from most recent to oldest.
2. WHEN the Game_Fetcher retrieves games, THE Game_Fetcher SHALL parse each game's PGN data and store the parsed results locally for subsequent analysis.
3. WHEN games are successfully retrieved and the total number of fetched games is fewer than 10,000, THE Analysis_UI SHALL display the actual number of games fetched.
4. WHEN games are successfully retrieved and the total number of fetched games equals 10,000 (the capped maximum), THE Analysis_UI SHALL display a count of 10,000 regardless of the actual total available on chess.com.
5. IF the chess.com API does not respond within 30 seconds per request, THEN THE Game_Fetcher SHALL display an error message indicating the connection to chess.com failed.
6. IF the submitted username is empty or exceeds 25 characters, THEN THE Game_Fetcher SHALL display an error message indicating the username format is invalid.
7. IF the provided username exists on chess.com but has no game history, THEN THE Game_Fetcher SHALL display a message indicating no games were found for that username.
8. IF the provided username does not exist on chess.com, THEN THE Game_Fetcher SHALL display an error message indicating the username was not found.
9. WHILE the Game_Fetcher is retrieving games from the chess.com API, THE Analysis_UI SHALL display a progress indicator showing the retrieval is in progress.

### Requirement 2: Single Game Retrieval

**User Story:** As a chess player, I want to load a specific chess.com game by its URL, so that I can analyze a particular game of interest without loading my entire history.

#### Acceptance Criteria

1. WHEN a chess.com game URL is submitted, THE Game_Fetcher SHALL retrieve that specific game's PGN data from the chess.com public API within 30 seconds.
2. WHEN a single game is successfully retrieved, THE Game_Fetcher SHALL parse the PGN data and store the parsed result locally for subsequent analysis.
3. IF the submitted URL does not match a recognized chess.com game URL format, THEN THE Game_Fetcher SHALL display an error message indicating that the URL is not a valid chess.com game URL.
4. IF the URL format is valid but the specified game does not exist on chess.com, THEN THE Game_Fetcher SHALL display an error message indicating that the game was not found.
5. IF the chess.com API is unreachable during single game retrieval, THEN THE Game_Fetcher SHALL display an error message indicating that the connection to chess.com failed.
6. WHEN a single game is successfully retrieved from chess.com AND PGN parsing and local storage complete successfully, THE Analysis_UI SHALL display a confirmation indicating the game was loaded and is available for analysis.
7. IF a single game is successfully retrieved from chess.com but PGN parsing fails, THEN THE Game_Fetcher SHALL display an error message indicating that parsing of the retrieved game failed, and THE Analysis_UI SHALL NOT display a success confirmation.

### Requirement 3: Game List Display

**User Story:** As a chess player, I want to see a browsable list of all my fetched games with key details, so that I can choose which game to analyze.

#### Acceptance Criteria

1. WHEN games have been fetched for a profile, THE Analysis_UI SHALL display a scrollable list of all retrieved games sorted by date with the most recent game first.
2. THE Analysis_UI SHALL display the date played, opponent username, game result (win, loss, or draw from the fetched player's perspective), time control, and opening name for each game entry in the list.
3. WHEN the user selects a game from the list, THE Analysis_UI SHALL navigate to the move-by-move analysis view for that game.
4. THE Analysis_UI SHALL allow the user to sort the game list by date, result, or time control in both ascending and descending order.
5. IF no games have been fetched for the current profile, THEN THE Analysis_UI SHALL display a message indicating that no games are available.
6. IF a game entry is missing one or more metadata fields (opponent username, time control, or opening name), THEN THE Analysis_UI SHALL display a placeholder indicating the information is unavailable for each missing field.

### Requirement 4: PGN Parsing

**User Story:** As a chess player, I want my games to be accurately parsed from PGN format, so that the analysis reflects the correct moves and metadata.

#### Acceptance Criteria

1. WHEN a PGN string is received, THE Review_Engine SHALL parse the PGN into a structured game representation containing the move list in standard algebraic notation, the Seven Tag Roster metadata headers (Event, Site, Date, Round, White, Black, Result), any additional tag pairs present, and any comment annotations.
2. THE Review_Engine SHALL format structured game representations back into PGN strings that conform to the PGN standard export format.
3. THE Review_Engine SHALL preserve round-trip fidelity such that formatting a parsed game back to a PGN string and re-parsing the result produces a structured representation with the same move sequence, metadata header values, and comment annotations as the original.
4. IF a PGN string is malformed or contains invalid move notation, THEN THE Review_Engine SHALL return an error message indicating the nature of the failure and the move number or header name where parsing failed.
5. IF a PGN string contains no moves after the header section, THEN THE Review_Engine SHALL return an error message indicating that no moves were found.

### Requirement 5: Move-by-Move Stockfish Analysis

**User Story:** As a chess player, I want each move in my game evaluated by Stockfish, so that I can understand the quality of every decision I made.

#### Acceptance Criteria

1. WHEN a game is selected for analysis, THE Review_Engine SHALL evaluate the initial position and each subsequent position after every half-move in the game using Stockfish at a minimum search depth of 20 plies.
2. THE Review_Engine SHALL compute a centipawn evaluation score from White's perspective for each position in the game.
3. IF Stockfish detects a forced checkmate in a position, THEN THE Review_Engine SHALL report a mate-in-N indicator specifying the number of moves to mate instead of a centipawn score.
4. THE Review_Engine SHALL identify up to 3 top candidate moves ranked by Stockfish evaluation for each position that has at least one legal move.
5. WHILE the Review_Engine is analyzing a game, THE Analysis_UI SHALL display a progress indicator showing the percentage of moves analyzed.
6. WHEN analysis of all positions in a game is complete, THE Analysis_UI SHALL atomically replace the progress indicator with an analysis-complete indicator such that the progress indicator is removed before the complete indicator appears, and the two indicators are never displayed simultaneously.
7. IF Stockfish encounters an invalid position during analysis, THEN THE Review_Engine SHALL skip to the next position and include the skipped position in the analysis results marked as an error.

### Requirement 6: Move Classification

**User Story:** As a chess player, I want each of my moves classified by quality, so that I can quickly identify my best and worst decisions.

#### Acceptance Criteria

1. WHEN a position has been evaluated, THE Review_Engine SHALL classify the player's move into exactly one of the following categories: best move, excellent, good, inaccuracy, mistake, or blunder.
2. THE Review_Engine SHALL assign each Move_Classification based on the centipawn loss between the player's move and the best available move identified by Stockfish using the following thresholds: best move for a centipawn loss of 0, excellent for a centipawn loss from 1 to 10 inclusive, good for a centipawn loss from 11 to 30 inclusive, inaccuracy for a centipawn loss from 31 to 80 inclusive, mistake for a centipawn loss from 81 to 200 inclusive, and blunder for a centipawn loss of 201 or greater.
3. THE Analysis_UI SHALL display the Move_Classification for each move using one unique color-coded icon per category, such that no two categories share the same color or the same icon shape.
4. THE Analysis_UI SHALL display a game summary showing the count of each Move_Classification category for both players.
5. IF the Review_Engine cannot determine the centipawn loss for a move, THEN THE Review_Engine SHALL omit the Move_Classification for that move and THE Analysis_UI SHALL display an indicator that classification is unavailable for that move.

### Requirement 7: Best Move Suggestions

**User Story:** As a chess player, I want to see the best possible move at each position alongside my actual move, so that I can learn what I should have played.

#### Acceptance Criteria

1. THE Analysis_UI SHALL display up to 3 candidate moves identified by Stockfish in descending order of centipawn evaluation, using standard algebraic notation, alongside the player's actual move for each position. WHEN a position has fewer than 3 legal moves available, THE Analysis_UI SHALL display only the available legal moves.
2. IF the player's move differs from the top-ranked candidate move, THEN THE Analysis_UI SHALL visually indicate the top-ranked candidate move's origin and destination squares on the board, using a display style distinct from the player's actual move.
3. THE Analysis_UI SHALL display the centipawn evaluation for each of the top 3 candidate moves and for the player's actual move.
4. IF the player's actual move is among the top 3 candidate moves, THEN THE Analysis_UI SHALL visually mark the player's move within the candidate move list.

### Requirement 8: Mid-Game Performance Rating

**User Story:** As a chess player, I want to see an estimated performance ELO throughout the game, so that I can track how well I played at different stages.

#### Acceptance Criteria

1. WHEN a move has been evaluated by Stockfish, THE Review_Engine SHALL compute a cumulative Performance_Rating for each player based on centipawn loss between the player's moves and the best moves identified by Stockfish for all moves evaluated up to that point, expressed as a whole number in the range 0 to 3000.
2. WHEN a game analysis is displayed, THE Analysis_UI SHALL display a line graph of the Performance_Rating for both players with move number on the horizontal axis and Performance_Rating value on the vertical axis.
3. WHEN a game analysis is complete, THE Analysis_UI SHALL display the Performance_Rating computed after the last evaluated move for each player in the game summary.
4. IF Performance_Rating data is not available for a game, THEN THE Analysis_UI SHALL display a message indicating that performance rating data requires completed game analysis.

### Requirement 9: Learning Insights

**User Story:** As a chess player, I want to receive explanations about my suboptimal moves, so that I can understand my mistakes and improve.

#### Acceptance Criteria

1. WHEN a move is classified as an inaccuracy, mistake, or blunder, THE Review_Engine SHALL generate a textual explanation that includes the centipawn loss between the played move and the best move identified by Stockfish.
2. THE Review_Engine SHALL include the suggested best move and the principal variation line of up to 5 moves in each explanation.
3. WHEN the user navigates to a move classified as an inaccuracy, mistake, or blunder, THE Analysis_UI SHALL display that move's explanation in a dedicated insight panel.
4. WHEN the user reviews a completed game analysis, THE Analysis_UI SHALL display a learning summary listing all moves classified as an inaccuracy, mistake, or blunder, along with their explanations.
5. WHEN the user navigates to a move not classified as an inaccuracy, mistake, or blunder, THE Analysis_UI SHALL clear the insight panel.

### Requirement 10: Interactive Board Display

**User Story:** As a chess player, I want an interactive chess board to navigate through my game visually, so that I can follow the analysis in context.

#### Acceptance Criteria

1. THE Analysis_UI SHALL render an 8×8 chess board displaying the current position with visually distinct representations of each of the 6 piece types (king, queen, rook, bishop, knight, pawn) for both white and black.
2. WHEN the user clicks forward or backward navigation controls, THE Analysis_UI SHALL update the board to the next or previous position within 100 milliseconds.
3. THE Analysis_UI SHALL provide first-move, previous-move, next-move, and last-move navigation controls.
4. THE Analysis_UI SHALL support keyboard navigation where the left arrow key triggers previous-move and the right arrow key triggers next-move.
5. THE Analysis_UI SHALL display an Evaluation_Bar adjacent to the board showing the current position's advantage in centipawns, where positive values indicate White advantage and negative values indicate Black advantage.
6. IF the current position is checkmate, THEN THE Analysis_UI SHALL display the Evaluation_Bar at its maximum extent in the winning side's direction.
7. IF the board is displaying the initial position of the game, THEN THE Analysis_UI SHALL disable the first-move and previous-move navigation controls.
8. IF the board is displaying the final position of the game, THEN THE Analysis_UI SHALL disable the next-move and last-move navigation controls.

### Requirement 11: Evaluation Graph

**User Story:** As a chess player, I want to see a graph of the position evaluation across the entire game, so that I can identify turning points and critical moments.

#### Acceptance Criteria

1. THE Analysis_UI SHALL display a line graph plotting centipawn evaluation scores on the Y-axis against sequential move numbers on the X-axis for all moves by both players in the game, with Y-axis values clamped to a range of −2000 to +2000 centipawns and checkmate evaluations represented at the ±2000 boundary.
2. WHEN the user clicks on the evaluation graph, THE Analysis_UI SHALL navigate the board to the move position nearest to the clicked location on the X-axis.
3. THE Analysis_UI SHALL display a distinct marker at each point on the evaluation graph where the centipawn evaluation changed by more than 100 centipawns between consecutive moves, visually distinguishable from non-highlighted data points by a difference in color or shape.
4. WHEN the current move displayed on the board changes, THE Analysis_UI SHALL update a position indicator on the evaluation graph to mark the corresponding move's data point.
5. IF evaluation data is unavailable for one or more positions in the game, THEN THE Analysis_UI SHALL omit those positions from the evaluation graph and connect the nearest evaluated positions.

### Requirement 12: Containerized Local Deployment

**User Story:** As a user, I want the entire application to run locally in Docker containers with a single command, so that I can use it without configuring individual services.

#### Acceptance Criteria

1. THE Container_Runtime SHALL package the Analysis_UI, Review_Engine, Game_Fetcher, and Stockfish into Docker containers defined in a docker-compose configuration.
2. WHEN the user executes a single docker compose up command, THE Container_Runtime SHALL start all required services and make the Analysis_UI accessible in a web browser within 120 seconds.
3. THE Container_Runtime SHALL expose the Analysis_UI on a local port configurable via an environment variable, defaulting to port 3000.
4. THE Container_Runtime SHALL require no external service dependencies beyond the chess.com public API for game fetching.
5. WHEN the user executes a docker compose down command, THE Container_Runtime SHALL stop and remove all running containers and their associated networks.
6. IF any container fails to start during docker compose up, THEN THE Container_Runtime SHALL output a log message identifying the failed service.
