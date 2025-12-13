from osu import Client, UserScoreType
import os
from dotenv import load_dotenv


load_dotenv(dotenv_path="sec.env")

client_id = int(os.getenv('AUTH_ID'))
client_secret = os.getenv('AUTH_TOKEN')
redirect_url = "https://rt4d-production.up.railway.app/"


client = Client.from_credentials(client_id, client_secret, redirect_url)

user_id = 12997443

top_scores = client.get_user_scores(user_id, UserScoreType.BEST, limit=1)

from osu.objects import LazerMod
from osu.enums import Mod

def format_lazer_mods(mod_list: list[LazerMod]) -> str:
    if not mod_list:
        return "NM"  # No Mods

    mod_strings = []
    
    for lazer_mod in mod_list:
        # 1. Get the acronym (e.g., "DT", "HR")
        # lazer_mod.mod is usually an Enum, so .acronym or .value gets the string
        acronym = getattr(lazer_mod.mod, 'acronym', str(lazer_mod.mod))
        print(lazer_mod.mod.value)
        
        # 2. Check for settings (e.g., Speed increase, DA settings)
        if lazer_mod.settings:
            # Format settings as (key: value)
            # Example: DT (speed_change: 1.2)
            setting_parts = []
            for k, v in lazer_mod.settings.items():
                # Clean up the key names if needed (e.g. 'speed_change' -> 'Speed')
                clean_key = k.replace('_', ' ').capitalize()
                # Round floats to look nicer
                if isinstance(v, float):
                    v = f"{v:.2f}"
                setting_parts.append(f"{clean_key}: {v}")
            
            # Combine acronym + settings
            mod_strings.append(f"{acronym} ({', '.join(setting_parts)})")
        else:
            # Just the acronym
            mod_strings.append(acronym)

    # Join them with a plus sign for the classic look
    return "+" + "".join(mod_strings)

for i, score in enumerate(top_scores):
    score1 = score.total_score
    mods = score.mods
    print(format_lazer_mods(mods))
    date = int(score.ended_at.timestamp())
    print(date)
    acc = f"{score.accuracy*100:.1f}%"
    map = score.beatmapset
    mapp = score.beatmap
    star = f"{mapp.difficulty_rating:.1f}★"
    id = map.id
    link = f"https://osu.ppy.sh/beatmapsets/{id}"
    print(score1)
    print(acc)
    print(star)
    print(link)
    user = score.user
    code  = user.country_code
    flag_emoji = f":flag_{code.lower()}:"
    print(flag_emoji)


from osu.objects import LazerMod

def format_lazer_mods(mod_list: list[LazerMod]) -> str:
    if not mod_list:
        return "NM"  # No Mods

    mod_strings = []
    
    for lazer_mod in mod_list:
        # 1. Get the acronym (e.g., "DT", "HR")
        # lazer_mod.mod is usually an Enum, so .acronym or .value gets the string
        acronym = getattr(lazer_mod.mod, 'acronym', str(lazer_mod.mod))
        
        # 2. Check for settings (e.g., Speed increase, DA settings)
        if lazer_mod.settings:
            # Format settings as (key: value)
            # Example: DT (speed_change: 1.2)
            setting_parts = []
            for k, v in lazer_mod.settings.items():
                # Clean up the key names if needed (e.g. 'speed_change' -> 'Speed')
                clean_key = k.replace('_', ' ').capitalize()
                # Round floats to look nicer
                if isinstance(v, float):
                    v = f"{v:.2f}"
                setting_parts.append(f"{clean_key}: {v}")
            
            # Combine acronym + settings
            mod_strings.append(f"{acronym} ({', '.join(setting_parts)})")
        else:
            # Just the acronym
            mod_strings.append(acronym)

    # Join them with a plus sign for the classic look
    return "+" + "".join(mod_strings)