from .core_v2 import create_supabase


async def add_points(player, points):
    supabase = await create_supabase()
    try:
        response = (
            await supabase.rpc("add_points", {"player": player, "given_points": points})
            .single()
            .execute()
        )
        if response and response.data:
            return response.data
    except Exception as e:
        print(f"Error at function add_points() {e}")
    return False
