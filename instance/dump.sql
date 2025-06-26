PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "Rivals" (
	id INTEGER NOT NULL, 
	league VARCHAR(25) NOT NULL, 
	challenger VARCHAR(25) NOT NULL, 
	challenged VARCHAR(25) NOT NULL, 
	challenger_initial_pp INTEGER, 
	challenger_final_pp INTEGER, 
	challenged_initial_pp INTEGER, 
	challenged_final_pp INTEGER, 
	challenger_stats VARCHAR(25), 
	challenged_stats VARCHAR(25), 
	issued_at DATETIME, 
	challenge_status VARCHAR(25), 
	for_pp INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (id)
);
INSERT INTO Rivals VALUES(1,'Platinum','plus','Arirret',7375,NULL,7348,NULL,NULL,NULL,'2025-06-22T05:36:24.070567+00:00','Unfinished',750);
INSERT INTO Rivals VALUES(2,'Silver','Rika Voort','Rhythmic_Ocean',3687,NULL,3700,NULL,NULL,NULL,'2025-06-22T05:36:24.070567+00:00','Unfinished',750);
CREATE TABLE discord_osu (
	id INTEGER NOT NULL, 
	discord_username VARCHAR(25), 
	osu_username VARCHAR(25), 
	PRIMARY KEY (id), 
	UNIQUE (id)
);
INSERT INTO discord_osu VALUES(1,'richard_riderr','Slowpoke1360');
INSERT INTO discord_osu VALUES(2,'taichi1717','Solar_Taichi');
INSERT INTO discord_osu VALUES(3,'ilovewalterwhite','NotPole');
INSERT INTO discord_osu VALUES(4,'yanamiannapout','Rika Voort');
INSERT INTO discord_osu VALUES(5,'evolhsif','shira1');
INSERT INTO discord_osu VALUES(6,'rafelandroid2','castor');
INSERT INTO discord_osu VALUES(7,'kero727','xXKero');
INSERT INTO discord_osu VALUES(8,'strivial','Strivial');
INSERT INTO discord_osu VALUES(9,'xavier_hi','SqueakSqueak');
INSERT INTO discord_osu VALUES(10,'rhythmic_ocean','Rhythmic_Ocean');
INSERT INTO discord_osu VALUES(11,'alonsz','alonsz');
INSERT INTO discord_osu VALUES(12,'supneit','SupNeit');
INSERT INTO discord_osu VALUES(13,'beatmaps','Kqma');
INSERT INTO discord_osu VALUES(14,'booba.b','jefferson bobbe');
INSERT INTO discord_osu VALUES(15,'ssssoup','spinneracc');
INSERT INTO discord_osu VALUES(16,'amamiya.mitoro','Amamiya Mitoro');
INSERT INTO discord_osu VALUES(17,'pathetic_and_sad','somebody_home');
INSERT INTO discord_osu VALUES(18,'rz15i','rzye');
INSERT INTO discord_osu VALUES(19,'eonduolatias','EonDuoLatios');
INSERT INTO discord_osu VALUES(20,'johnyy4','6 digit forever');
INSERT INTO discord_osu VALUES(21,'daribush.','Daribush');
INSERT INTO discord_osu VALUES(22,'egorixxz','Egorixxz');
INSERT INTO discord_osu VALUES(23,'thatg_y','thatanimeguy0');
INSERT INTO discord_osu VALUES(24,'goi3m','golem');
INSERT INTO discord_osu VALUES(25,'imtwilk','Stagz');
INSERT INTO discord_osu VALUES(26,'death9208','Death9208');
INSERT INTO discord_osu VALUES(27,'xapped','Xapped');
INSERT INTO discord_osu VALUES(28,'akasaiba','Saiba');
INSERT INTO discord_osu VALUES(29,'catzfx','plus');
INSERT INTO discord_osu VALUES(30,'oppanboy','oppanboy');
INSERT INTO discord_osu VALUES(31,'arirret','Arirret');
INSERT INTO discord_osu VALUES(32,'oshmkufa_','Yumirai');
INSERT INTO discord_osu VALUES(33,'demideum','Demideum');
INSERT INTO discord_osu VALUES(34,'a_cool_toast','FinBois');
INSERT INTO discord_osu VALUES(35,'serrrved','zeppelinn');
INSERT INTO discord_osu VALUES(36,'vnxt.','durante');
INSERT INTO discord_osu VALUES(37,'kanna.dc','[Kanna]');
INSERT INTO discord_osu VALUES(38,'elo4373','Elo4373');
INSERT INTO discord_osu VALUES(39,'wetratz0','wetratz0');
INSERT INTO discord_osu VALUES(40,'wutever','Wutever');
INSERT INTO discord_osu VALUES(41,'mrcursed','DZHEYLO');
INSERT INTO discord_osu VALUES(42,'nunk7','nunk7');
INSERT INTO discord_osu VALUES(43,'zacfrfr','zacfr');
INSERT INTO discord_osu VALUES(44,'inklyned','InkLyned');
INSERT INTO discord_osu VALUES(45,'am1x','Am1x');
INSERT INTO discord_osu VALUES(46,'johwn','- mimic -');
INSERT INTO discord_osu VALUES(47,'rosedive','rockhard');
INSERT INTO discord_osu VALUES(48,'sillierkel','Floofies');
INSERT INTO discord_osu VALUES(49,'bowiepro','bowiepro');
INSERT INTO discord_osu VALUES(50,'onlyhadley','OnlyHadley');
INSERT INTO discord_osu VALUES(51,'boybeef','EthantrixV3');
INSERT INTO discord_osu VALUES(52,'miinr','miinr');
CREATE TABLE mesg_id (
	id INTEGER NOT NULL, 
	msg_id INTEGER, 
	challenge_id INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (id), 
	UNIQUE (msg_id), 
	UNIQUE (challenge_id)
);
CREATE TABLE IF NOT EXISTS "Master" (
	id INTEGER NOT NULL, 
	discord_username VARCHAR(25), 
	osu_username VARCHAR(25), 
	initial_pp INTEGER, 
	current_pp INTEGER, 
	pp_change INTEGER, 
	PRIMARY KEY (id)
);
INSERT INTO Master VALUES(1,'onlyhadley','OnlyHadley',18280,NULL,NULL);
INSERT INTO Master VALUES(2,'boybeef','EthantrixV3',13401,NULL,NULL);
INSERT INTO Master VALUES(3,'miinr','miinr',13611,NULL,NULL);
CREATE TABLE IF NOT EXISTS "Ranker" (
	id INTEGER NOT NULL, 
	discord_username VARCHAR(25), 
	osu_username VARCHAR(25), 
	initial_pp INTEGER, 
	current_pp INTEGER, 
	pp_change INTEGER, 
	PRIMARY KEY (id)
);
CREATE TABLE IF NOT EXISTS "Elite" (
	id INTEGER NOT NULL, 
	discord_username VARCHAR(25), 
	osu_username VARCHAR(25), 
	initial_pp INTEGER, 
	current_pp INTEGER, 
	pp_change INTEGER, 
	PRIMARY KEY (id)
);
INSERT INTO Elite VALUES(1,'rosedive','rockhard',9033,NULL,NULL);
INSERT INTO Elite VALUES(2,'sillierkel','Floofies',9036,NULL,NULL);
INSERT INTO Elite VALUES(3,'bowiepro','bowiepro',9868,NULL,NULL);
CREATE TABLE IF NOT EXISTS "Diamond" (
	id INTEGER NOT NULL, 
	discord_username VARCHAR(25), 
	osu_username VARCHAR(25), 
	initial_pp INTEGER, 
	current_pp INTEGER, 
	pp_change INTEGER, 
	PRIMARY KEY (id)
);
INSERT INTO Diamond VALUES(1,'wutever','Wutever',8724,NULL,NULL);
INSERT INTO Diamond VALUES(2,'mrcursed','DZHEYLO',8004,NULL,NULL);
INSERT INTO Diamond VALUES(3,'nunk7','nunk7',7975,NULL,NULL);
INSERT INTO Diamond VALUES(4,'zacfrfr','zacfr',7800,NULL,NULL);
INSERT INTO Diamond VALUES(5,'inklyned','InkLyned',7771,NULL,NULL);
INSERT INTO Diamond VALUES(6,'am1x','Am1x',7658,NULL,NULL);
INSERT INTO Diamond VALUES(7,'johwn','- mimic -',7904,NULL,NULL);
CREATE TABLE IF NOT EXISTS "Platinum" (
	id INTEGER NOT NULL, 
	discord_username VARCHAR(25), 
	osu_username VARCHAR(25), 
	initial_pp INTEGER, 
	current_pp INTEGER, 
	pp_change INTEGER, 
	PRIMARY KEY (id)
);
INSERT INTO Platinum VALUES(1,'akasaiba','Saiba',6234,NULL,NULL);
INSERT INTO Platinum VALUES(2,'catzfx','plus',7029,NULL,NULL);
INSERT INTO Platinum VALUES(3,'oppanboy','oppanboy',6976,NULL,NULL);
INSERT INTO Platinum VALUES(4,'arirret','Arirret',6810,NULL,NULL);
INSERT INTO Platinum VALUES(5,'oshmkufa_','Yumirai',6800,NULL,NULL);
INSERT INTO Platinum VALUES(6,'demideum','Demideum',6712,NULL,NULL);
INSERT INTO Platinum VALUES(7,'a_cool_toast','FinBois',6552,NULL,NULL);
INSERT INTO Platinum VALUES(8,'serrrved','zeppelinn',6518,NULL,NULL);
INSERT INTO Platinum VALUES(9,'vnxt.','durante',6287,NULL,NULL);
INSERT INTO Platinum VALUES(10,'kanna.dc','[Kanna]',5405,NULL,NULL);
INSERT INTO Platinum VALUES(11,'elo4373','Elo4373',5989,NULL,NULL);
INSERT INTO Platinum VALUES(12,'wetratz0','wetratz0',5590,NULL,NULL);
CREATE TABLE IF NOT EXISTS "Gold" (
	id INTEGER NOT NULL, 
	discord_username VARCHAR(25), 
	osu_username VARCHAR(25), 
	initial_pp INTEGER, 
	current_pp INTEGER, 
	pp_change INTEGER, 
	PRIMARY KEY (id)
);
INSERT INTO Gold VALUES(1,'rz15i','rzye',5397,5727,330);
INSERT INTO Gold VALUES(2,'eonduolatias','EonDuoLatios',5329,5435,106);
INSERT INTO Gold VALUES(3,'johnyy4','6 digit forever',5060,5468,408);
INSERT INTO Gold VALUES(4,'daribush.','Daribush',5006,5025,19);
INSERT INTO Gold VALUES(5,'egorixxz','Egorixxz',4971,4971,0);
INSERT INTO Gold VALUES(6,'thatg_y','thatanimeguy0',4852,5008,156);
INSERT INTO Gold VALUES(7,'goi3m','golem',5917,6009,92);
INSERT INTO Gold VALUES(8,'imtwilk','Stagz',5878,5926,48);
INSERT INTO Gold VALUES(9,'spinneracc','ssssoup',4863,4909,46);
INSERT INTO Gold VALUES(10,'death9208','Death9208',5566,5699,133);
INSERT INTO Gold VALUES(11,'xapped','Xapped',4400,4997,597);
CREATE TABLE IF NOT EXISTS "Silver" (
	id INTEGER NOT NULL, 
	discord_username VARCHAR(25), 
	osu_username VARCHAR(25), 
	initial_pp INTEGER, 
	current_pp INTEGER, 
	pp_change INTEGER, 
	PRIMARY KEY (id)
);
INSERT INTO Silver VALUES(1,'yanamiannapout','Rika Voort',3346,NULL,NULL);
INSERT INTO Silver VALUES(2,'evolhsif','shira1',4628,NULL,NULL);
INSERT INTO Silver VALUES(3,'rafelandroid2','castor',4131,NULL,NULL);
INSERT INTO Silver VALUES(4,'kero727','xXKero',3620,NULL,NULL);
INSERT INTO Silver VALUES(5,'strivial','Strivial',4359,NULL,NULL);
INSERT INTO Silver VALUES(6,'xavier_hi','SqueakSqueak',4159,NULL,NULL);
INSERT INTO Silver VALUES(7,'rhythmic_ocean','Rhythmic_Ocean',3066,NULL,NULL);
INSERT INTO Silver VALUES(8,'alonsz','alonsz',4785,NULL,NULL);
INSERT INTO Silver VALUES(9,'supneit','SupNeit',3122,NULL,NULL);
INSERT INTO Silver VALUES(10,'beatmaps','Kqma',3070,NULL,NULL);
INSERT INTO Silver VALUES(11,'booba.b','jefferson bobbe',4403,NULL,NULL);
INSERT INTO Silver VALUES(12,'amamiya.mitoro','Amamiya Mitoro',4453,NULL,NULL);
INSERT INTO Silver VALUES(13,'pathetic_and_sad','somebody_home',0,NULL,NULL);
CREATE TABLE IF NOT EXISTS "Bronze" (
	id INTEGER NOT NULL, 
	discord_username VARCHAR(25), 
	osu_username VARCHAR(25), 
	initial_pp INTEGER, 
	current_pp INTEGER, 
	pp_change INTEGER, 
	PRIMARY KEY (id)
);
INSERT INTO Bronze VALUES(1,'richard_riderr','Slowpoke1360',1694,NULL,NULL);
INSERT INTO Bronze VALUES(2,'taichi1717','Solar_Taichi',2478,NULL,NULL);
INSERT INTO Bronze VALUES(3,'ilovewalterwhite','NotPole',2819,NULL,NULL);
COMMIT;
