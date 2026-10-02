"""Installed console entry point: waaxalma-backend."""
def main() -> None:
    import uvicorn
    from app.core.settings import get_settings
    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.host, port=settings.port,
                log_level=settings.log_level, reload=False, workers=1,
                timeout_graceful_shutdown=settings.shutdown_timeout_seconds)


if __name__ == "__main__":
    main()
