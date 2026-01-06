import os
from quart import Quart

from load_env import ENV
from utils_v2 import LogHandler
from web_utils import HomeView, DashboardView, WebHelper


class QuartApp:
    def __init__(self):
        self.app = Quart(__name__)

        self.web_helper = None
        self.log_handler = LogHandler(logger_name="web")
        self.app.secret_key = ENV.QUART_SECKEY

        self.register_routes()

    async def get_web_helper(self):
        if self.web_helper is None:
            self.web_helper = await WebHelper.create(self.log_handler)
        return self.web_helper

    def register_routes(self):
        home_view = HomeView.as_view("home", get_helper_func=self.get_web_helper)
        self.app.add_url_rule("/", view_func=home_view, methods=["GET"])

        dash_view = DashboardView.as_view(
            "dashboard",
        )
        self.app.add_url_rule("/dashboard", view_func=dash_view, methods=["GET"])

    def run(self):
        port = int(os.environ.get("PORT", 8080))
        self.app.run(host="0.0.0.0", port=port, debug=True)


def create_app():
    server = QuartApp()
    return server.app


if __name__ == "__main__":
    server = QuartApp()
    server.run()
