import logging
import asyncio
from django.core.management.base import BaseCommand
from coap_server import server

class Command(BaseCommand):
    help = "Start a COAPS server for readers to connect to"

    def add_arguments(self, parser):
        parser.add_argument("--address", type=str, default="::", required=False)
        parser.add_argument("--port", type=int, default=5684, required=False)

    def handle(self, address, port, *args, **options):
        logging.basicConfig(level=logging.INFO)
        asyncio.run(server.run_server(address=address, port=port))
