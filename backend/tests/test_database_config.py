import os
import subprocess
import sys


def run_database_check(database_url=None):
    env = os.environ.copy()
    env.pop("DATABASE_URL", None)

    if database_url is not None:
        env["DATABASE_URL"] = database_url

    code = """
from app.database import DATABASE_URL, engine

if DATABASE_URL == "sqlite:///./tourist_safety.db":
    assert engine.dialect.name == "sqlite"
    assert engine.url.database == "./tourist_safety.db"
elif DATABASE_URL == "sqlite://":
    assert engine.dialect.name == "sqlite"
    assert engine.url.database is None
    with engine.connect() as connection:
        assert connection.exec_driver_sql("SELECT 1").scalar_one() == 1
else:
    raise AssertionError(f"Unexpected DATABASE_URL: {DATABASE_URL}")

engine.dispose()
print("PASS")
"""

    result = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, (
        f"Database check failed.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    assert "PASS" in result.stdout


def test_default_database_url_is_preserved():
    run_database_check()


def test_environment_database_url_override_works():
    run_database_check("sqlite://")
