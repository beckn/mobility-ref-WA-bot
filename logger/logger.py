import os
import logging.config
from pathlib import Path


class BotLogger:
    name = "bot"
    os.environ['BOT_LOG_DIR'] = str(Path(f"logs/{name}").resolve())

    @staticmethod
    def logger(logger_name):
        config_file = Path(Path(__file__).parent,
                           "bot_logger.conf").resolve(strict=True)
        logging.config.fileConfig(
            fname=config_file, disable_existing_loggers=False)
        logger = logging.getLogger(logger_name)
        return logger
