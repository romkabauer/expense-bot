import logging


class Logger:

    def __init__(self) -> None:
        self._sep = '||'
        self._log_format = self._sep.join(['%(asctime)s', '%(levelname)s', '%(message)s'])
        logging.basicConfig(level=logging.INFO, format=self._log_format, filename='log.log', filemode='w+')
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter(self._log_format))
        self.logger.addHandler(ch)

    def log(self, action, user: str = '', extra_text: str = '', level: str = "info"):
        action = action.__class__.__name__
        extra_text = extra_text.replace(self._sep, '//')
        if user:
            user = str(user)
        message = self._sep.join([action, user, extra_text])
        match level:
            case "warn":
                self.logger.warning(message)
            case "error":
                self.logger.error(message)
            case _:
                self.logger.info(message)
