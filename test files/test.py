import sqlite3
from datetime import datetime, timezone

import sqlite3

# Adapter: convert datetime to ISO string
def adapt_datetime(dt):
    return dt.isoformat()

# Converter: parse ISO string back to datetime
def convert_datetime(b):
    return datetime.fromisoformat(b.decode())

# Register adapter and converter
sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("DATETIME", convert_datetime)

# When connecting, enable detect_types for converters
conn = sqlite3.connect("instance/rt4d.db", detect_types=sqlite3.PARSE_DECLTYPES)
now = datetime.now(timezone.utc)
cursor = conn.cursor()

cursor = conn.cursor()
bronze_update = [
    ('richard_riderr', 'Slowpoke1360', 1694),
    ('taichi1717', 'Solar_Taichi', 2478),
    ('ilovewalterwhite', 'NotPole', 2819)
]
silver_update = [
    ('yanamiannapout','Rika Voort',3346),
    ('evolhsif', 'shira1',4628),
    ('rafelandroid2', 'castor', 4131),
    ('kero727','xXKero',3620),
    ('strivial','Strivial', 4359),         
    ('xavier_hi','SqueakSqueak',4159),
    ('rhythmic_ocean','Rhythmic_Ocean',3066),
    ('alonsz','alonsz',4785),
    ('supneit','SupNeit',3122),
    ('beatmaps','Kqma',3070),
    ('booba.b','jefferson bobbe',4403),
    ('amamiya.mitoro','Amamiya Mitoro',4453),
    ('pathetic_and_sad', 'somebody_home', 0)
]
gold_update = [
    ('rzye', 'rz15i', 5397),
    ('EonDuoLatios', 'eonduolatias', 5329),
    ('6 digit forever', 'johnyy4', 5060),
    ('Daribush', 'daribush.', 5006),
    ('Egorixxz', 'egorixxz', 4971),
    ('thatanimeguy0', 'thatg_y', 4852),
    ('golem', 'goi3m',5917),
    ('Stagz','imtwilk',5878),
    ('ssssoup', 'spinneracc', 4863),
    ('Death9208','death9208',5566),
    ('Xapped','xapped',4400),
]
platinum_update = [
    ('Saiba', 'akasaiba', 6234),
    ('plus', 'catzfx', 7029),
    ('oppanboy', 'oppanboy', 6976),
    ('Arirret', 'arirret', 6810),
    ('Yumirai', 'oshmkufa_', 6800),
    ('Demideum', 'demideum', 6712),
    ('FinBois', 'a_cool_toast', 6552),
    ('zeppelinn', 'serrrved', 6518),
    ('durante', 'vnxt.', 6287),
    ('[Kanna]', 'kanna.dc', 5405),
    ('Elo4373', 'elo4373', 5989),
    ('wetratz0', 'wetratz0', 5590),
]
diamond_update = [
    ('Wutever', 'wutever', 8724),
    ('DZHEYLO', 'mrcursed', 8004),
    ('nunk7', 'nunk7', 7975),
    ('zacfr', 'zacfrfr', 7800),
    ('InkLyned', 'inklyned', 7771),
    ('Am1x', 'am1x', 7658),
    ('- mimic -', 'johwn', 7904),
]
elite_update = [
    ('rockhard', 'rosedive', 9033),
    ('Floofies', 'sillierkel', 9036),
    ('bowiepro', 'bowiepro', 9868),

]
master_update = [
    ('OnlyHadley', 'onlyhadley', 18280),
    ('EthantrixV3', 'boybeef', 13401),
    ('miinr', 'miinr', 13611),
]


rivals_update = [
('Platinum','plus','Arirret',7375,7348, now, "Unfinished", 750),
('Silver', 'Rika Voort', 'Rhythmic_Ocean', 3687,3700, now, "Unfinished", 750)
]

all_updates = [
    # Bronze
    ('richard_riderr', 'Slowpoke1360'),
    ('taichi1717', 'Solar_Taichi'),
    ('ilovewalterwhite', 'NotPole'),

    # Silver
    ('yanamiannapout', 'Rika Voort'),
    ('evolhsif', 'shira1'),
    ('rafelandroid2', 'castor'),
    ('kero727', 'xXKero'),
    ('strivial', 'Strivial'),
    ('xavier_hi', 'SqueakSqueak'),
    ('rhythmic_ocean', 'Rhythmic_Ocean'),
    ('alonsz', 'alonsz'),
    ('supneit', 'SupNeit'),
    ('beatmaps', 'Kqma'),
    ('booba.b', 'jefferson bobbe'),
    ('ssssoup', 'spinneracc'),
    ('amamiya.mitoro', 'Amamiya Mitoro'),
    ('pathetic_and_sad', 'somebody_home'),

    # Gold (flipped)
    ('rz15i', 'rzye'),
    ('eonduolatias', 'EonDuoLatios'),
    ('johnyy4', '6 digit forever'),
    ('daribush.', 'Daribush'),
    ('egorixxz', 'Egorixxz'),
    ('thatg_y', 'thatanimeguy0'),
    ('goi3m', 'golem'),
    ('imtwilk', 'Stagz'),
    ('death9208', 'Death9208'),
    ('xapped', 'Xapped'),

    # Platinum (flipped)
    ('akasaiba', 'Saiba'),
    ('catzfx', 'plus'),
    ('oppanboy', 'oppanboy'),
    ('arirret', 'Arirret'),
    ('oshmkufa_', 'Yumirai'),
    ('demideum', 'Demideum'),
    ('a_cool_toast', 'FinBois'),
    ('serrrved', 'zeppelinn'),
    ('vnxt.', 'durante'),
    ('kanna.dc', '[Kanna]'),
    ('elo4373', 'Elo4373'),
    ('wetratz0', 'wetratz0'),

    # Diamond (flipped)
    ('wutever', 'Wutever'),
    ('mrcursed', 'DZHEYLO'),
    ('nunk7', 'nunk7'),
    ('zacfrfr', 'zacfr'),
    ('inklyned', 'InkLyned'),
    ('am1x', 'Am1x'),
    ('johwn', '- mimic -'),

    # Elite (flipped)
    ('rosedive', 'rockhard'),
    ('sillierkel', 'Floofies'),
    ('bowiepro', 'bowiepro'),

    # Master (flipped)
    ('onlyhadley', 'OnlyHadley'),
    ('boybeef', 'EthantrixV3'),
    ('miinr', 'miinr'),
]

cursor.executemany(
    f"INSERT INTO discord_osu (discord_username, osu_username) VALUES (?, ?)", all_updates
)

cursor.executemany(
    f"INSERT INTO Bronze (discord_username, osu_username, initial_pp) VALUES (?,?,?)", bronze_update
)
cursor.executemany(
    f"INSERT INTO Silver (discord_username, osu_username, initial_pp) VALUES (?,?,?)", silver_update
)
cursor.executemany(
    f"INSERT INTO Gold (osu_username, discord_username, initial_pp) VALUES (?,?,?)", gold_update
)
cursor.executemany(
    f"INSERT INTO Platinum (osu_username, discord_username, initial_pp) VALUES (?,?,?)", platinum_update
)
cursor.executemany(
    f"INSERT INTO Diamond (osu_username, discord_username, initial_pp) VALUES (?,?,?)", diamond_update
)
cursor.executemany(
    f"INSERT INTO Elite (osu_username, discord_username, initial_pp) VALUES (?,?,?)", elite_update
)
cursor.executemany(
    f"INSERT INTO Master (osu_username, discord_username, initial_pp) VALUES (?,?,?)", master_update
)

cursor.executemany(
    f"INSERT INTO Rivals (league, challenger, challenged, challenger_initial_pp, challenged_initial_pp, issued_at, challenge_status, for_pp) VALUES(?, ?, ?, ?, ?, ?, ?, ?)", rivals_update
)
conn.commit()

cursor.close()
conn.close()