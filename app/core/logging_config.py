import logging


def setup_logging() -> None:
    """Configure console logging for the whole app. Call once at startup."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
