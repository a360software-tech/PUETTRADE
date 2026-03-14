import logging


def configure_logging(app_name: str, debug: bool) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format=f"%(asctime)s %(levelname)s [{app_name}] %(name)s - %(message)s",
    )
