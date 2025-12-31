import sys
from quart import redirect, url_for, render_template, request, session
from quart.views import MethodView
from itsdangerous import URLSafeSerializer

from load_env import ENV
from utils_v2.enums.status import FuncStatus
from utils_v2.enums.tables_internals import DiscordOsuColumn
from .web_helper import WebHelper

LEAGUE_MODES = {
    1000: "master",
    3000: "elite",
    10000: "diamond",
    30000: "platinum",
    80000: "gold",
    150000: "silver",
    250000: "bronze",
    sys.maxsize: "novice",
}


class HomeView(MethodView):
    init_every_request = False

    def __init__(self, get_helper_func):
        self.get_helper = get_helper_func
        self.serializer = URLSafeSerializer(ENV.SEC_KEY)

    async def get(self):
        load = request.args.get("state")
        code = request.args.get("code")
        if not load or not code:
            if "user_data" in session:
                return redirect(url_for("dashboard"))
            return await render_template("welcome.html")

        helper: WebHelper = await self.get_helper()

        validation_result = await self._validate_state(helper, load)
        if not isinstance(validation_result, tuple):
            return validation_result

        discord_id, discord_name = validation_result

        existing_user_result = await self._check_existing_user(helper, discord_id)
        if existing_user_result:
            return existing_user_result

        # checks if the osu account is already linked to sm other discord acc is done inside
        return await self._link_new_user(helper, code, discord_id, discord_name)

    async def _validate_state(self, helper: WebHelper, load):
        try:
            data = self.serializer.loads(load)
            discord_name = data.get("user_name")
            discord_id = data.get("user_id")
            created_at = data.get("created_at")
        except Exception as e:
            await helper.log_handler.report_error("HomeView Decrypt", e)
            return "Invalid state. Please try again.", 400

        validity = await helper.load_validity(discord_id, created_at)

        if validity == FuncStatus.BAD_REQ:
            return await render_template("bad_req.html")
        if validity == FuncStatus.TOO_LATE:
            return await render_template("too_late.html")
        discord_id = validity

        return discord_id, discord_name

    async def _check_existing_user(self, helper: WebHelper, discord_id: int):
        entry = await helper.search_and_find(discord_id)

        if entry is FuncStatus.ERROR:
            return await render_template("error.html")
        if entry is FuncStatus.BAD_REQ:
            return await render_template("bad_req.html")

        if entry:
            session["user_data"] = {
                "username": entry["osu_username"],
                "pp": entry["initial_pp"],
                "league": entry["league"],
                "msg": "You already have a linked account. Contact admin to change it.",
            }
            return redirect(url_for("dashboard"))

        return None

    async def _link_new_user(self, helper: WebHelper, code, discord_id, discord_name):
        try:
            response = await helper.get_osu_user(code, discord_id)

            if response == FuncStatus.ERROR:
                return await render_template("error.html")
            if response == FuncStatus.BAD_REQ:
                return await render_template("bad_req.html")

            osu_id = response[DiscordOsuColumn.OSU_ID]
            # checking if the osu account is already linked
            check_ouser = await helper.check_ouser_existence(osu_id)
            if check_ouser == FuncStatus.ERROR:
                return await render_template("error.html")
            if check_ouser:
                redundent_discord_id = check_ouser
                error = Exception("Duplicate connection detected")
                await helper.log_handler.report_error(
                    "HomeView._link_new_user()",
                    error,
                    f"<@{discord_id}> tried authenticating with osu_account : {response[DiscordOsuColumn.OSU_USERNAME]}, but it is already connected with <@{redundent_discord_id}>.",
                )
                return await render_template("old_account.html")

            if response == FuncStatus.ERROR:
                return await render_template("error.html")
            if response == FuncStatus.BAD_REQ:
                return await render_template("bad_req.html")

            response[DiscordOsuColumn.DISCORD_USERNAME] = discord_name.strip()
            response[DiscordOsuColumn.DISCORD_ID] = discord_id
            response[DiscordOsuColumn.FUTURE_LEAGUE] = response[DiscordOsuColumn.LEAGUE]

            result = await helper.add_user(response)

            if result == FuncStatus.ERROR:
                return await render_template("error.html")
            if result == FuncStatus.GOOD:
                await helper.log_handler.report_info(
                    f"Successfully signed in new user: <@{response[DiscordOsuColumn.DISCORD_ID]}>"
                )

            session["user_data"] = {
                "username": response[DiscordOsuColumn.OSU_USERNAME],
                "pp": response[DiscordOsuColumn.CURRENT_PP],
                "league": response[DiscordOsuColumn.LEAGUE],
                "msg": "You have been verified, you can safely exit this page.",
            }
            return redirect(url_for("dashboard"))

        except Exception as e:
            await helper.log_handler.report_error("HomeView._link_new_user", e)
            return await render_template("error.html")


class DashboardView(MethodView):
    init_every_request = False

    async def get(self):
        data = session.get("user_data")
        if not data:
            return redirect(url_for("home"))

        return await render_template(
            "dashboard.html",
            username=data["username"],
            pp=data["pp"],
            msg=data["msg"],
            league=data["league"],
        )
