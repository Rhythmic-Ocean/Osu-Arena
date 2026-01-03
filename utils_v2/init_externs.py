import asyncio
import sys
import logging
from supabase import AsyncClient
from osu import AsynchronousAuthHandler, AsynchronousClient, Scope

from utils_v2 import LogHandler


class InitExterns:
    def __init__(self, log_handler: LogHandler):
        self.log_handler = log_handler
        self.logger = getattr(log_handler, "logger", logging.getLogger("InitExterns"))

        self.supabase_client = None
        self.osu_client = None
        self.osu_auth = None

    async def setup_supabase_client(
        self, supabase_url: str, supabase_key: str
    ) -> AsyncClient:
        max_tries = 3
        self.logger.info("-------------------")
        self.logger.info("Creating Supabase Client....")

        for i in range(max_tries):
            try:
                client = await AsyncClient.create(
                    supabase_key=supabase_key, supabase_url=supabase_url
                )

                self.supabase_client = client

                self.logger.info("Supabase client created successfully")
                self.logger.info("-------------------")

                return client

            except Exception as e:
                if i == max_tries - 1:
                    self.logger.critical(
                        f"CRITICAL FAILURE: Supabase Client creation failed after {max_tries} attempts.\n"
                        f"Error: {e}\n"
                        "Shutting down..."
                    )
                    sys.exit(1)
                else:
                    self.logger.error(
                        f"Supabase Client creation failed (Attempt {i + 1}/{max_tries}).\n"
                        f"Error: {e}\n"
                        "Retrying in 5 seconds..."
                    )
                    await asyncio.sleep(5)

    async def setup_osu_client(
        self, osu_auth: AsynchronousAuthHandler
    ) -> AsynchronousClient:
        max_tries = 3
        self.logger.info("-------------------")
        self.logger.info("Creating Osu Client....")

        for i in range(max_tries):
            try:
                client = AsynchronousClient(osu_auth)
                self.osu_client = client

                self.logger.info("Osu client created successfully")
                self.logger.info("-------------------")
                return client

            except Exception as e:
                if i == max_tries - 1:
                    self.logger.critical(
                        f"CRITICAL FAILURE: Osu Client creation failed after {max_tries} attempts.\n"
                        f"Error: {e}\n"
                        "Shutting down..."
                    )
                    sys.exit(1)
                else:
                    self.logger.error(
                        f"Osu Client creation failed (Attempt {i + 1}/{max_tries}).\n"
                        f"Error: {e}\n"
                        "Retrying in 5 seconds..."
                    )
                    await asyncio.sleep(5)

    async def setup_osu_auth(
        self, osu_client_id: int, osu_client_sec: str, redirect_url: str
    ) -> AsynchronousAuthHandler:
        max_tries = 3
        self.logger.info("-------------------")
        self.logger.info("Creating Osu Auth Handler....")

        for i in range(max_tries):
            try:
                auth = AsynchronousAuthHandler(
                    osu_client_id,
                    osu_client_sec,
                    redirect_url,
                    Scope.identify(),
                )
                self.osu_auth = auth

                self.logger.info("Osu Auth created successfully")
                self.logger.info("-------------------")
                return auth

            except Exception as e:
                if i == max_tries - 1:
                    self.logger.critical(
                        f"CRITICAL FAILURE: Osu Auth creation failed after {max_tries} attempts.\n"
                        f"Error: {e}\n"
                        "Shutting down..."
                    )
                    sys.exit(1)
                else:
                    self.logger.error(
                        f"Osu Auth creation failed (Attempt {i + 1}/{max_tries}).\n"
                        f"Error: {e}\n"
                        "Retrying in 5 seconds..."
                    )
                    await asyncio.sleep(5)
