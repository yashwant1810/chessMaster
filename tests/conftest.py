"""Root-level conftest for the Chess Review Engine smoke tests."""


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "docker: marks tests that require Docker Compose (deselect with '-m \"not docker\"')",
    )
