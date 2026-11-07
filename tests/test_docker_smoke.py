"""
Smoke tests for Docker Compose deployment of the Chess Review Engine.

These tests verify the docker-compose.yml configuration behaves correctly:
- Services start and the UI is accessible within 120 seconds
- `docker compose down` removes all containers and networks
- Frontend port is configurable via FRONTEND_PORT env var
- Failed container logs identify the failed service

Requirements: 12.2, 12.3, 12.5, 12.6

Usage:
    pytest tests/test_docker_smoke.py -m docker -v

These tests are slow (build + start containers) and require Docker to be installed.
They are skipped automatically when Docker is unavailable.
"""

import os
import subprocess
import time
import urllib.request
import urllib.error

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# ── Skip helpers ──────────────────────────────────────────────────────────────


def _docker_available() -> bool:
    """Return True if docker compose is available on this machine."""
    try:
        result = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


skip_no_docker = pytest.mark.skipif(
    not _docker_available(),
    reason="Docker Compose is not available",
)

# Mark all tests in this module with a custom `docker` marker so they can be
# selected (or excluded) with `pytest -m docker` / `pytest -m 'not docker'`.
pytestmark = [pytest.mark.docker, skip_no_docker]


# ── Helpers ───────────────────────────────────────────────────────────────────


def _compose(*args: str, env: dict[str, str] | None = None, timeout: int = 300) -> subprocess.CompletedProcess:
    """Run a `docker compose` command in the project root."""
    merged_env = {**os.environ, **(env or {})}
    return subprocess.run(
        ["docker", "compose", *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=merged_env,
    )


def _compose_down(env: dict[str, str] | None = None) -> None:
    """Tear down all services, suppressing errors."""
    try:
        _compose("down", "--volumes", "--remove-orphans", env=env, timeout=60)
    except (subprocess.TimeoutExpired, Exception):
        pass


def _wait_for_http(url: str, timeout: int = 120) -> bool:
    """Poll *url* until it returns HTTP 200, or *timeout* seconds elapse."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            req = urllib.request.urlopen(url, timeout=5)
            if req.status == 200:
                return True
        except (urllib.error.URLError, OSError, ConnectionResetError):
            pass
        time.sleep(2)
    return False


def _running_container_names() -> set[str]:
    """Return the set of currently-running container names for the project."""
    result = _compose("ps", "--format", "{{.Name}}", "--status", "running")
    if result.returncode != 0:
        return set()
    return {name.strip() for name in result.stdout.splitlines() if name.strip()}


def _all_container_names() -> set[str]:
    """Return the set of all (running or stopped) container names for the project."""
    result = _compose("ps", "-a", "--format", "{{.Name}}")
    if result.returncode != 0:
        return set()
    return {name.strip() for name in result.stdout.splitlines() if name.strip()}


def _project_networks() -> set[str]:
    """Return docker network names that belong to the compose project."""
    result = subprocess.run(
        ["docker", "network", "ls", "--format", "{{.Name}}"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        return set()
    # The compose project creates networks prefixed with the project directory
    # name.  For the chessEngine project this is typically
    # "chessengine_chess-engine-net" or similar.
    return {
        name.strip()
        for name in result.stdout.splitlines()
        if "chess-engine-net" in name.strip()
    }


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestDockerComposeUp:
    """Requirement 12.2 – `docker compose up` starts services and UI is accessible within 120s."""

    @pytest.fixture(autouse=True)
    def _cleanup(self):
        """Ensure containers are torn down after each test."""
        yield
        _compose_down()

    def test_services_start_and_ui_accessible(self):
        """docker compose up -d starts both services and the frontend responds on port 3000."""
        # Build and start
        result = _compose("up", "-d", "--build", timeout=600)
        assert result.returncode == 0, (
            f"docker compose up failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

        # Both containers should be running
        running = _running_container_names()
        assert "chess-engine-backend" in running, (
            f"Backend container not running. Running: {running}"
        )
        assert "chess-engine-frontend" in running, (
            f"Frontend container not running. Running: {running}"
        )

        # UI must be reachable within 120 seconds (Requirement 12.2)
        assert _wait_for_http("http://localhost:3000", timeout=120), (
            "Frontend UI was not accessible at http://localhost:3000 within 120 seconds"
        )


class TestDockerComposeDown:
    """Requirement 12.5 – `docker compose down` removes all containers and networks."""

    def test_down_removes_containers_and_networks(self):
        """After `docker compose down`, no project containers or networks remain."""
        # Start services first
        result = _compose("up", "-d", "--build", timeout=600)
        assert result.returncode == 0, (
            f"docker compose up failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
        _wait_for_http("http://localhost:3000", timeout=120)

        # Now bring everything down
        down_result = _compose("down", "--volumes", "--remove-orphans", timeout=60)
        assert down_result.returncode == 0, (
            f"docker compose down failed:\nstdout: {down_result.stdout}\nstderr: {down_result.stderr}"
        )

        # No project containers should exist (running or stopped)
        remaining = _all_container_names()
        assert len(remaining) == 0, (
            f"Containers still present after docker compose down: {remaining}"
        )

        # Project network should be removed
        nets = _project_networks()
        assert len(nets) == 0, (
            f"Project networks still present after docker compose down: {nets}"
        )


class TestFrontendPortConfigurable:
    """Requirement 12.3 – frontend port is configurable via FRONTEND_PORT env var."""

    @pytest.fixture(autouse=True)
    def _cleanup(self):
        """Tear down with the custom port env so compose finds the right project."""
        yield
        _compose_down(env={"FRONTEND_PORT": "3080"})

    def test_custom_frontend_port(self):
        """Setting FRONTEND_PORT=3080 makes the UI accessible on port 3080."""
        custom_env = {"FRONTEND_PORT": "3080"}

        result = _compose("up", "-d", "--build", env=custom_env, timeout=600)
        assert result.returncode == 0, (
            f"docker compose up with FRONTEND_PORT=3080 failed:\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

        # UI should be available on the custom port
        assert _wait_for_http("http://localhost:3080", timeout=120), (
            "Frontend UI was not accessible at http://localhost:3080 within 120 seconds"
        )


class TestFailedContainerLogs:
    """Requirement 12.6 – failed container logs identify the failed service."""

    @pytest.fixture(autouse=True)
    def _cleanup(self):
        """Tear down after the test."""
        yield
        _compose_down()

    def test_logs_identify_failed_service(self):
        """Container logs include the service name so failures can be traced."""
        # Start services (they may or may not succeed; we only care about log output)
        _compose("up", "-d", "--build", timeout=600)

        # Give containers a moment to produce log output
        time.sleep(5)

        # Fetch logs for each defined service
        for service in ("backend", "frontend"):
            log_result = _compose("logs", "--no-color", service, timeout=30)
            # docker compose logs prefixes each line with the service name,
            # e.g. "chess-engine-backend  | ..."
            assert log_result.returncode == 0, (
                f"Could not retrieve logs for service '{service}':\n{log_result.stderr}"
            )
            # The combined output should reference the container / service name
            # so a developer can tell which service produced each log line.
            combined = log_result.stdout + log_result.stderr
            assert service in combined or f"chess-engine-{service}" in combined, (
                f"Logs for service '{service}' do not identify the service.\n"
                f"Log output:\n{combined[:2000]}"
            )
