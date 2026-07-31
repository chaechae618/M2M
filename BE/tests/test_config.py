from pathlib import Path

from app.core.config import Settings


def test_comma_separated_cors_origins_from_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "CORS_ORIGINS=http://localhost:3000,http://localhost:5173",
                "JWT_SECRET_KEY=test-secret-key-that-is-at-least-32-characters",
            ]
        ),
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert settings.cors_origins == [
        "http://localhost:3000",
        "http://localhost:5173",
    ]
