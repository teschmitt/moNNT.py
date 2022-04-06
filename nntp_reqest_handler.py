from tortoise import run_async

from logger import global_logger
from socketserver import StreamRequestHandler

from nntp_commands import call_dict
from settings import settings
from status_codes import StatusCodes
from version import get_version


class NNTPRequestHandler(StreamRequestHandler):
    data = None
    broken_oe_checker = 0
    terminated = False
    # fileConfig("logging_conf.ini")
    logger = global_logger
    # logger.debug("Request handler started")

    def handle_timeout(self, signum, frame):
        self.terminated = True
        self.logger.warning(f"Connection timed out from {self.client_address[0]}")

    def send_response(self, message: str) -> None:
        self.logger.debug(f"server > {message}")
        self.wfile.write(bytes(f"{message}\r\n", "utf-8", "replace"))
        self.wfile.flush()

    def send_array(self, msg=None):
        """
        Send response to client but take an array in input
        Add \r\n at each line end
        """

        if msg is None:
            msg = []
        for m in msg:
            self.logger.debug(f"       > {m}")
            self.wfile.write(bytes(m + "\r\n", "utf-8", "replace"))
        self.wfile.flush()

    def handle(self) -> None:

        self.logger.debug("In request handler")


        if settings.SERVER_TYPE == "read-only":
            self.send_response(
                StatusCodes.STATUS_READYNOPOST % (settings.NNTP_HOSTNAME, get_version())
            )
        else:
            self.send_response(
                StatusCodes.STATUS_READYOKPOST % (settings.NNTP_HOSTNAME, get_version())
            )

        self.logger.info(f"Client connected > address: {self.client_address}")
        self.logger.debug("Received data:")

        while not self.terminated:
            try:
                tokens = self.rfile.readline().strip().decode("utf-8", "replace").lower().split(" ")
            except IOError:
                continue
            self.logger.debug(tokens)
            if all([t == "" for t in tokens]):
                self.broken_oe_checker += 1
                if self.broken_oe_checker == 10:
                    self.logger.debug(f"WARNING: Noping out because client is sending too many empty requests")
                    self.terminated = 1
                continue

            self.logger.debug(f"{self.client_address[0]} > {tokens}")

            command = tokens.pop(0)
            self.logger.debug(f"Command: {command}")

            if command in ["mode", "group", "capabilities"]:
                self.send_response(call_dict[command](tokens))
            elif command in ["list"]:
                self.send_array(await call_dict[command](tokens))


