import asyncio
import os
from dotenv import load_dotenv
from osu import AsynchronousClient, GameModeStr, RequestException
from supabase import AsyncClient, create_async_client

load_dotenv(dotenv_path="local.env")

OSU_CLIENT_ID = int(os.getenv("OSU_CLIENT_ID"))
OSU_CLIENT_SECRET = os.getenv("OSU_CLIENT_SECRET")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

TABLE_NAME = "discord_osu"


async def fetch_playtime(
    osu_client: AsynchronousClient,
    osu_id: int,
    semaphore: asyncio.Semaphore,
    mode: GameModeStr = GameModeStr.STANDARD,
) -> tuple[int, int | None]:
    async with semaphore:
        try:
            user = await osu_client.get_user(osu_id, mode=mode)
            seconds = user.statistics.play_time if user.statistics else 0
            return osu_id, int(seconds // 3600)
        except RequestException as error:
            if error.status == 404:
                print(f"[SKIP] osu_id {osu_id} not found or banned (404)")
                return osu_id, None
            print(f"[ERROR] HTTP {error.status} for osu_id {osu_id}: {error}")
            return osu_id, None
        except Exception as error:
            print(f"[ERROR] Unexpected error for osu_id {osu_id}: {error}")
            return osu_id, None


async def update_single_player(
    supabase: AsyncClient,
    osu_id: int,
    username: str,
    playtime: int,
    db_sem: asyncio.Semaphore,
) -> bool:
    async with db_sem:
        try:
            await (
                supabase.table(TABLE_NAME)
                .update({"playtime": playtime})
                .eq("osu_id", osu_id)
                .execute()
            )
            print(f"Updated: {username} ({osu_id}) -> {playtime} hrs")
            return True
        except Exception as error:
            print(f"[DB ERROR] Failed updating {username} ({osu_id}): {error}")
            return False


async def main() -> None:
    supabase = await create_async_client(SUPABASE_URL, SUPABASE_KEY)
    osu_client = AsynchronousClient.from_credentials(
        client_id=OSU_CLIENT_ID,
        client_secret=OSU_CLIENT_SECRET,
        redirect_url=None,
    )

    # 1. Fetch all players from Supabase
    response = (
        await supabase.table(TABLE_NAME)
        .select("osu_id, osu_username, playtime")
        .execute()
    )
    players = response.data or []
    print(f"Found {len(players)} players in '{TABLE_NAME}'. Fetching playtimes...")

    # 2. Fetch current playtimes concurrently from osu! API
    osu_sem = asyncio.Semaphore(5)
    fetch_tasks = [
        fetch_playtime(osu_client, row["osu_id"], osu_sem)
        for row in players
        if row.get("osu_id")
    ]
    results = await asyncio.gather(*fetch_tasks)
    playtime_map = {osu_id: hours for osu_id, hours in results if hours is not None}

    # 3. Update Supabase concurrently using .update().eq() (avoids NOT NULL upsert error)
    db_sem = asyncio.Semaphore(15)
    update_tasks = []
    for row in players:
        osu_id = row.get("osu_id")
        if osu_id not in playtime_map:
            continue
        username = row.get("osu_username") or str(osu_id)
        update_tasks.append(
            update_single_player(
                supabase, osu_id, username, playtime_map[osu_id], db_sem
            )
        )

    update_results = await asyncio.gather(*update_tasks)
    success_count = sum(1 for ok in update_results if ok)
    print(f"\nDone! Updated playtime for {success_count}/{len(update_tasks)} players.")


if __name__ == "__main__":
    asyncio.run(main())
