import sqlite3


with sqlite3.connect("instance/rt4d.db") as conn:
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
    ]
    gold_update = [
        ('rzye', 'rz15i', 5397),
        ('EonDuoLatios', 'eonduolatias', 5329),
        ('6 digit forever', 'johnyy4', 5060),
        ('Daribush', 'daribush.', 5006),
        ('Egorixxz', 'egorixxz', 4971),
        ('spinneracc', 'ssssoup', 4863),
        ('thatanimeguy0', 'thatg_y', 4852),
        ('golem', 'goi3m',5917),
        ('Stagz','imtwilk',5878),
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
    conn.commit()