


SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;


COMMENT ON SCHEMA "public" IS 'standard public schema';



CREATE EXTENSION IF NOT EXISTS "pg_graphql" WITH SCHEMA "graphql";






CREATE EXTENSION IF NOT EXISTS "pg_stat_statements" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "pgcrypto" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "supabase_vault" WITH SCHEMA "vault";






CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA "extensions";






CREATE OR REPLACE FUNCTION "public"."accept_challenge"("p_challenge_id" integer, OUT "out_challenger_id" bigint, OUT "out_challenged_id" bigint, OUT "out_for_pp" numeric) RETURNS "record"
    LANGUAGE "plpgsql"
    AS $$
BEGIN 

  UPDATE challenged s
  SET current_pp = u.current_pp, 
      osu_username = u.osu_username, 
      initial_pp = u.current_pp
  FROM discord_osu u
  WHERE s.discord_username = u.discord_username
    AND s.challenge_id = p_challenge_id;

  UPDATE challenger s
  SET current_pp = u.current_pp, 
      osu_username = u.osu_username, 
      initial_pp = u.current_pp
  FROM discord_osu u
  WHERE s.discord_username = u.discord_username
    AND s.challenge_id = p_challenge_id;

  UPDATE rivals s
  SET challenger_final_pp = u.current_pp, 
      challenger = u.osu_username, 
      challenger_initial_pp = u.current_pp, 
      challenge_status = 'Unfinished'
  FROM challenger u
  WHERE s.challenge_id = u.challenge_id
    AND s.challenge_id = p_challenge_id;

  UPDATE rivals s
  SET challenged_final_pp = u.current_pp, 
      challenged = u.osu_username, 
      challenged_initial_pp = u.current_pp, 
      challenge_status = 'Unfinished',
      accepted_at = now()
  FROM challenged u
  WHERE s.challenge_id = u.challenge_id
    AND s.challenge_id = p_challenge_id;

  SELECT 
    cr.discord_id, 
    cd.discord_id, 
    r.for_pp
  INTO 
    out_challenger_id, 
    out_challenged_id, 
    out_for_pp
  FROM rivals r
  JOIN challenger cr ON r.challenge_id = cr.challenge_id
  JOIN challenged cd ON r.challenge_id = cd.challenge_id
  WHERE r.challenge_id = p_challenge_id;
END;
$$;


ALTER FUNCTION "public"."accept_challenge"("p_challenge_id" integer, OUT "out_challenger_id" bigint, OUT "out_challenged_id" bigint, OUT "out_for_pp" numeric) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."add_points"("player" "text", "given_points" integer, OUT "new_points" integer, OUT "new_seasonal_points" integer) RETURNS "record"
    LANGUAGE "plpgsql"
    AS $$
begin
  update discord_osu
  set
    points = coalesce(points, 0) + given_points,
    seasonal_points = coalesce(seasonal_points, 0) + given_points
  where
    osu_username = player
  returning points, seasonal_points
  into new_points, new_seasonal_points;
end;
$$;


ALTER FUNCTION "public"."add_points"("player" "text", "given_points" integer, OUT "new_points" integer, OUT "new_seasonal_points" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."award_seasonal_points"("league_table_name" "text") RETURNS "void"
    LANGUAGE "plpgsql"
    AS $$
begin
  execute format('
    with calculate_point as(
      select
        osu_username,
        case
          when pp_change < 100 then 1
          when pp_change <= 1000 then ROUND(power(pp_change, 2)/1000)::INTEGER
          else pp_change::INTEGER
        end as points_to_add
      from %I
      where pp_change >= 0
  )
  update discord_osu as main
  set
    points = coalesce(main.points, 0) + cs.points_to_add,
    seasonal_points = coalesce(main.seasonal_points, 0) + cs.points_to_add
  from calculate_point as cs
  where main.osu_username = cs.osu_username;
  ', league_table_name);
  raise notice 'Processed end-of-season points for league: %', league_table_name;
end;
$$;


ALTER FUNCTION "public"."award_seasonal_points"("league_table_name" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."award_weekly_winner"("league_table_name" "text") RETURNS TABLE("osu_username" "text", "new_points" integer, "new_seasonal_points" integer)
    LANGUAGE "plpgsql"
    AS $$
begin
  return query execute format('
    update discord_osu
    set 
      points = coalesce(points, 0) + 100,
      seasonal_points = coalesce(seasonal_points, 0) + 100
    where osu_username in (
      select osu_username 
      from %I 
      where pp_change = (select max(pp_change) from %I)
    )
    returning osu_username, points, seasonal_points
  ', league_table_name, league_table_name);
end;
$$;


ALTER FUNCTION "public"."award_weekly_winner"("league_table_name" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."backup_historical_points"("column_name" "text") RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
begin

  insert into historical_points (osu_username, discord_username)
  select osu_username, discord_username
  from discord_osu d
  where not exists (
      select 1 
      from historical_points h 
      where h.osu_username = d.osu_username
  );
  
  execute format('alter table historical_points add column %I int default 0', column_name);

  execute format('
    update historical_points h
    set %I = d.seasonal_points
    from discord_osu d
    where h.osu_username = d.osu_username
  ', column_name); 
end;
$$;


ALTER FUNCTION "public"."backup_historical_points"("column_name" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."decline_challenge"("p_challenge_id" integer, OUT "out_challenger_id" bigint, OUT "out_challenged_id" bigint, OUT "out_for_pp" numeric) RETURNS "record"
    LANGUAGE "plpgsql"
    AS $$
BEGIN 

  UPDATE rivals s
  SET challenge_status = 'Declined',
      ended_at = now()
  WHERE s.challenge_id = p_challenge_id;

  SELECT 
    cr.discord_id, 
    cd.discord_id, 
    r.for_pp
  INTO 
    out_challenger_id, 
    out_challenged_id, 
    out_for_pp
  FROM rivals r
  JOIN challenger cr ON r.challenge_id = cr.challenge_id
  JOIN challenged cd ON r.challenge_id = cd.challenge_id
  WHERE r.challenge_id = p_challenge_id;
END;
$$;


ALTER FUNCTION "public"."decline_challenge"("p_challenge_id" integer, OUT "out_challenger_id" bigint, OUT "out_challenged_id" bigint, OUT "out_for_pp" numeric) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."duplicate_table"("source_table" "text", "new_table_name" "text") RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
begin
  execute format('
    create table %I as
    select * from %I; 
  ', new_table_name, source_table); 
end;
$$;


ALTER FUNCTION "public"."duplicate_table"("source_table" "text", "new_table_name" "text") OWNER TO "postgres";

SET default_tablespace = '';

SET default_table_access_method = "heap";


CREATE TABLE IF NOT EXISTS "public"."discord_osu" (
    "discord_username" "text" NOT NULL,
    "osu_username" "text",
    "current_pp" integer,
    "osu_id" bigint,
    "league" "text",
    "global_rank" bigint,
    "future_league" "text",
    "discord_id" bigint,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "ii" real,
    "top_play_map" "text",
    "top_play_pp" integer,
    "top_play_date" timestamp with time zone,
    "top_play_id" bigint,
    "top_play_announce" boolean DEFAULT false,
    "new_player_announce" boolean DEFAULT false,
    "points" integer DEFAULT 0,
    "seasonal_points" integer DEFAULT 0
);


ALTER TABLE "public"."discord_osu" OWNER TO "postgres";


COMMENT ON COLUMN "public"."discord_osu"."points" IS 'Stores points for players during each season';



CREATE OR REPLACE FUNCTION "public"."get_mismatched_rows"() RETURNS SETOF "public"."discord_osu"
    LANGUAGE "sql" SECURITY DEFINER
    AS $$
  select *
  from discord_osu
  where league != future_league; -- The logic you wanted
$$;


ALTER FUNCTION "public"."get_mismatched_rows"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."log_rivals"("challenger_uname" "text", "challenged_uname" "text", "for_pp" integer, "league" "text") RETURNS integer
    LANGUAGE "plpgsql"
    AS $$
DECLARE
    new_id int;
BEGIN
    INSERT INTO rivals (challenger, challenged, for_pp, league, challenge_status)
    VALUES (challenger_uname, challenged_uname, for_pp, league, 'Pending')
    RETURNING challenge_id INTO new_id;

    RETURN new_id;
END;
$$;


ALTER FUNCTION "public"."log_rivals"("challenger_uname" "text", "challenged_uname" "text", "for_pp" integer, "league" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."log_to_challenge_table"("discord_username" "text", "osu_username" "text", "discord_id" bigint, "challenge_id" "text", "challenge_table" "text") RETURNS boolean
    LANGUAGE "plpgsql"
    AS $$
BEGIN

    EXECUTE format(
        'INSERT INTO %I (discord_username, osu_username, challenge_id, discord_id)
         VALUES (%L, %L, %L, %L)', 
        challenge_table, 
        discord_username, 
        osu_username, 
        challenge_id, 
        discord_id
    );
    RETURN TRUE;

EXCEPTION WHEN OTHERS THEN
    RETURN FALSE;
END;
$$;


ALTER FUNCTION "public"."log_to_challenge_table"("discord_username" "text", "osu_username" "text", "discord_id" bigint, "challenge_id" "text", "challenge_table" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."reset_seasonal_points"() RETURNS "void"
    LANGUAGE "plpgsql"
    AS $$begin
  update discord_osu
    set 
      seasonal_points = 0
      where true;
end;$$;


ALTER FUNCTION "public"."reset_seasonal_points"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."sync_rivals"() RETURNS "void"
    LANGUAGE "plpgsql"
    AS $$BEGIN 
  UPDATE challenged s
  SET current_pp = u.current_pp, osu_username = u.osu_username
  FROM discord_osu u
  WHERE s.discord_username = u.discord_username;

  UPDATE challenger s
  SET current_pp = u.current_pp, osu_username = u.osu_username
  FROM discord_osu u
  WHERE s.discord_username = u.discord_username;

  UPDATE rivals s
  SET challenger_final_pp = u.current_pp, challenger = u.osu_username
  FROM challenger u
  WHERE s.challenge_id = u.challenge_id;

  UPDATE rivals s
  SET challenged_final_pp = u.current_pp, challenged = u.osu_username
  FROM challenged u
  WHERE s.challenge_id = u.challenge_id;
  RETURN;
END;$$;


ALTER FUNCTION "public"."sync_rivals"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."sync_table_pp"("tbl_name" "text") RETURNS "void"
    LANGUAGE "plpgsql"
    AS $$
BEGIN 
  EXECUTE format(
    'UPDATE %I s
     SET current_pp = u.current_pp, osu_username = u.osu_username, global_rank = u.global_rank, ii = u.ii
     FROM discord_osu u
     WHERE s.discord_username = u.discord_username;',
    tbl_name
  );
END;
$$;


ALTER FUNCTION "public"."sync_table_pp"("tbl_name" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_init_pp"("tbl_name" "text") RETURNS "void"
    LANGUAGE "plpgsql"
    AS $$
BEGIN 
  EXECUTE format(
    'UPDATE %I s
     SET initial_pp = u.current_pp, osu_username = u.osu_username, global_rank = u.global_rank
     FROM discord_osu u
     WHERE s.discord_username = u.discord_username;',
    tbl_name
  );
END;
$$;


ALTER FUNCTION "public"."update_init_pp"("tbl_name" "text") OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."seasons" (
    "id" integer NOT NULL,
    "status" "text",
    "season" integer
);


ALTER TABLE "public"."seasons" OWNER TO "postgres";


ALTER TABLE "public"."seasons" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."Seasons_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);



CREATE TABLE IF NOT EXISTS "public"."bronze" (
    "discord_username" "text",
    "osu_username" "text",
    "initial_pp" smallint,
    "current_pp" smallint,
    "pp_change" integer GENERATED ALWAYS AS (("current_pp" - "initial_pp")) STORED,
    "global_rank" integer,
    "id" integer NOT NULL,
    "percentage_change" numeric GENERATED ALWAYS AS ("round"((((("current_pp" - "initial_pp"))::numeric * 100.0) / ("initial_pp")::numeric), 2)) STORED,
    "ii" real,
    "discord_id" bigint
);


ALTER TABLE "public"."bronze" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."bronze_1" (
    "discord_username" "text",
    "osu_username" "text",
    "initial_pp" smallint,
    "current_pp" smallint,
    "pp_change" integer,
    "global_rank" integer,
    "id" integer,
    "percentage_change" numeric,
    "ii" numeric(10,2)
);


ALTER TABLE "public"."bronze_1" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."bronze_2" (
    "discord_username" "text",
    "osu_username" "text",
    "initial_pp" smallint,
    "current_pp" smallint,
    "pp_change" integer,
    "global_rank" integer,
    "id" integer,
    "percentage_change" numeric,
    "ii" numeric(10,2)
);


ALTER TABLE "public"."bronze_2" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."bronze_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."bronze_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."bronze_id_seq" OWNED BY "public"."bronze"."id";



CREATE TABLE IF NOT EXISTS "public"."challenged" (
    "id" integer NOT NULL,
    "discord_username" "text" NOT NULL,
    "osu_username" "text" NOT NULL,
    "challenge_id" integer NOT NULL,
    "initial_pp" integer,
    "current_pp" smallint,
    "discord_id" bigint
);


ALTER TABLE "public"."challenged" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."challenged_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."challenged_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."challenged_id_seq" OWNED BY "public"."challenged"."id";



CREATE TABLE IF NOT EXISTS "public"."challenger" (
    "id" integer NOT NULL,
    "discord_username" "text" NOT NULL,
    "osu_username" "text" NOT NULL,
    "challenge_id" integer NOT NULL,
    "initial_pp" integer,
    "current_pp" integer,
    "discord_id" bigint
);


ALTER TABLE "public"."challenger" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."challenger_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."challenger_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."challenger_id_seq" OWNED BY "public"."challenger"."id";



CREATE TABLE IF NOT EXISTS "public"."diamond" (
    "discord_username" "text",
    "osu_username" "text",
    "initial_pp" smallint,
    "current_pp" smallint,
    "pp_change" integer GENERATED ALWAYS AS (("current_pp" - "initial_pp")) STORED,
    "global_rank" integer,
    "id" integer NOT NULL,
    "percentage_change" numeric GENERATED ALWAYS AS ("round"((((("current_pp" - "initial_pp"))::numeric * 100.0) / ("initial_pp")::numeric), 2)) STORED,
    "ii" real,
    "discord_id" bigint
);


ALTER TABLE "public"."diamond" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."diamond_1" (
    "discord_username" "text",
    "osu_username" "text",
    "initial_pp" smallint,
    "current_pp" smallint,
    "pp_change" integer,
    "global_rank" integer,
    "id" integer,
    "percentage_change" numeric,
    "ii" numeric(10,2)
);


ALTER TABLE "public"."diamond_1" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."diamond_2" (
    "discord_username" "text",
    "osu_username" "text",
    "initial_pp" smallint,
    "current_pp" smallint,
    "pp_change" integer,
    "global_rank" integer,
    "id" integer,
    "percentage_change" numeric,
    "ii" numeric(10,2)
);


ALTER TABLE "public"."diamond_2" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."diamond_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."diamond_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."diamond_id_seq" OWNED BY "public"."diamond"."id";



CREATE TABLE IF NOT EXISTS "public"."elite" (
    "discord_username" "text",
    "osu_username" "text",
    "initial_pp" smallint,
    "current_pp" smallint,
    "pp_change" integer GENERATED ALWAYS AS (("current_pp" - "initial_pp")) STORED,
    "global_rank" integer,
    "id" integer NOT NULL,
    "percentage_change" numeric GENERATED ALWAYS AS ("round"((((("current_pp" - "initial_pp"))::numeric * 100.0) / ("initial_pp")::numeric), 2)) STORED,
    "ii" real,
    "discord_id" bigint
);


ALTER TABLE "public"."elite" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."elite_1" (
    "discord_username" "text",
    "osu_username" "text",
    "initial_pp" smallint,
    "current_pp" smallint,
    "pp_change" integer,
    "global_rank" integer,
    "id" integer,
    "percentage_change" numeric,
    "ii" numeric(10,2)
);


ALTER TABLE "public"."elite_1" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."elite_2" (
    "discord_username" "text",
    "osu_username" "text",
    "initial_pp" smallint,
    "current_pp" smallint,
    "pp_change" integer,
    "global_rank" integer,
    "id" integer,
    "percentage_change" numeric,
    "ii" numeric(10,2)
);


ALTER TABLE "public"."elite_2" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."elite_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."elite_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."elite_id_seq" OWNED BY "public"."elite"."id";



CREATE TABLE IF NOT EXISTS "public"."gold" (
    "discord_username" "text",
    "osu_username" "text",
    "initial_pp" smallint,
    "current_pp" smallint,
    "global_rank" integer,
    "id" integer NOT NULL,
    "pp_change" integer GENERATED ALWAYS AS (("current_pp" - "initial_pp")) STORED,
    "percentage_change" numeric GENERATED ALWAYS AS ("round"((((("current_pp" - "initial_pp"))::numeric * 100.0) / ("initial_pp")::numeric), 2)) STORED,
    "ii" real,
    "discord_id" bigint
);


ALTER TABLE "public"."gold" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."gold_1" (
    "discord_username" "text",
    "osu_username" "text",
    "initial_pp" smallint,
    "current_pp" smallint,
    "global_rank" integer,
    "id" integer,
    "pp_change" integer,
    "percentage_change" numeric,
    "ii" numeric(10,2)
);


ALTER TABLE "public"."gold_1" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."gold_2" (
    "discord_username" "text",
    "osu_username" "text",
    "initial_pp" smallint,
    "current_pp" smallint,
    "global_rank" integer,
    "id" integer,
    "pp_change" integer,
    "percentage_change" numeric,
    "ii" numeric(10,2)
);


ALTER TABLE "public"."gold_2" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."gold_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."gold_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."gold_id_seq" OWNED BY "public"."gold"."id";



CREATE TABLE IF NOT EXISTS "public"."historical_points" (
    "id" bigint NOT NULL,
    "discord_username" "text" NOT NULL,
    "osu_username" "text",
    "discord_id" bigint
);


ALTER TABLE "public"."historical_points" OWNER TO "postgres";


ALTER TABLE "public"."historical_points" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."historical_point_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);



CREATE TABLE IF NOT EXISTS "public"."master" (
    "discord_username" "text",
    "osu_username" "text",
    "initial_pp" integer,
    "current_pp" smallint,
    "pp_change" integer GENERATED ALWAYS AS (("current_pp" - "initial_pp")) STORED,
    "global_rank" integer,
    "id" integer NOT NULL,
    "percentage_change" numeric GENERATED ALWAYS AS ("round"((((("current_pp" - "initial_pp"))::numeric * 100.0) / ("initial_pp")::numeric), 2)) STORED,
    "ii" real,
    "discord_id" bigint
);


ALTER TABLE "public"."master" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."master_1" (
    "discord_username" "text",
    "osu_username" "text",
    "initial_pp" integer,
    "current_pp" smallint,
    "pp_change" integer,
    "global_rank" integer,
    "id" integer,
    "percentage_change" numeric,
    "ii" numeric(10,2)
);


ALTER TABLE "public"."master_1" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."master_2" (
    "discord_username" "text",
    "osu_username" "text",
    "initial_pp" integer,
    "current_pp" smallint,
    "pp_change" integer,
    "global_rank" integer,
    "id" integer,
    "percentage_change" numeric,
    "ii" numeric(10,2)
);


ALTER TABLE "public"."master_2" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."master_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."master_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."master_id_seq" OWNED BY "public"."master"."id";



CREATE TABLE IF NOT EXISTS "public"."mesg_id" (
    "id" smallint NOT NULL,
    "msg_id" bigint,
    "challenge_id" smallint
);


ALTER TABLE "public"."mesg_id" OWNER TO "postgres";


ALTER TABLE "public"."mesg_id" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."mesg_id_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);



CREATE TABLE IF NOT EXISTS "public"."miscellaneous" (
    "id" bigint NOT NULL,
    "variable" "text" NOT NULL,
    "status" boolean
);


ALTER TABLE "public"."miscellaneous" OWNER TO "postgres";


ALTER TABLE "public"."miscellaneous" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."miscellaneous_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);



CREATE TABLE IF NOT EXISTS "public"."novice" (
    "discord_username" "text",
    "osu_username" "text",
    "initial_pp" smallint,
    "current_pp" smallint,
    "pp_change" integer GENERATED ALWAYS AS (("current_pp" - "initial_pp")) STORED,
    "global_rank" integer,
    "id" integer NOT NULL,
    "percentage_change" numeric GENERATED ALWAYS AS ("round"((((("current_pp" - "initial_pp"))::numeric * 100.0) / ("initial_pp")::numeric), 2)) STORED,
    "ii" real,
    "discord_id" bigint
);


ALTER TABLE "public"."novice" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."novice_2" (
    "discord_username" "text",
    "osu_username" "text",
    "initial_pp" smallint,
    "current_pp" smallint,
    "pp_change" integer,
    "global_rank" integer,
    "id" integer,
    "percentage_change" numeric,
    "ii" numeric(10,2)
);


ALTER TABLE "public"."novice_2" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."platinum" (
    "discord_username" "text",
    "osu_username" "text",
    "initial_pp" smallint,
    "current_pp" smallint,
    "pp_change" integer GENERATED ALWAYS AS (("current_pp" - "initial_pp")) STORED,
    "global_rank" integer,
    "id" integer NOT NULL,
    "percentage_change" numeric GENERATED ALWAYS AS ("round"((((("current_pp" - "initial_pp"))::numeric * 100.0) / ("initial_pp")::numeric), 2)) STORED,
    "ii" real,
    "discord_id" bigint
);


ALTER TABLE "public"."platinum" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."platinum_1" (
    "discord_username" "text",
    "osu_username" "text",
    "initial_pp" smallint,
    "current_pp" smallint,
    "pp_change" integer,
    "global_rank" integer,
    "id" integer,
    "percentage_change" numeric,
    "ii" numeric(10,2)
);


ALTER TABLE "public"."platinum_1" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."platinum_2" (
    "discord_username" "text",
    "osu_username" "text",
    "initial_pp" smallint,
    "current_pp" smallint,
    "pp_change" integer,
    "global_rank" integer,
    "id" integer,
    "percentage_change" numeric,
    "ii" numeric(10,2)
);


ALTER TABLE "public"."platinum_2" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."platinum_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."platinum_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."platinum_id_seq" OWNED BY "public"."platinum"."id";



CREATE TABLE IF NOT EXISTS "public"."ranker_1" (
    "discord_username" "text",
    "osu_username" "text",
    "initial_pp" smallint,
    "current_pp" smallint,
    "pp_change" integer,
    "global_rank" integer,
    "id" integer,
    "percentage_change" numeric,
    "ii" numeric(10,2)
);


ALTER TABLE "public"."ranker_1" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."ranker_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."ranker_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."ranker_id_seq" OWNED BY "public"."novice"."id";



CREATE TABLE IF NOT EXISTS "public"."rivals" (
    "challenge_id" smallint NOT NULL,
    "league" "text",
    "challenger" "text",
    "challenged" "text",
    "challenger_initial_pp" smallint,
    "challenger_final_pp" smallint,
    "challenged_initial_pp" smallint,
    "challenged_final_pp" smallint,
    "issued_at" timestamp with time zone DEFAULT "now"(),
    "challenge_status" "text",
    "for_pp" smallint,
    "challenged_stats" numeric GENERATED ALWAYS AS (("challenged_final_pp" - "challenged_initial_pp")) STORED,
    "challenger_stats" numeric GENERATED ALWAYS AS (("challenger_final_pp" - "challenger_initial_pp")) STORED,
    "winner" "text",
    "accepted_at" timestamp with time zone,
    "ended_at" timestamp with time zone
);


ALTER TABLE "public"."rivals" OWNER TO "postgres";


ALTER TABLE "public"."rivals" ALTER COLUMN "challenge_id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."rivals_challenge_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);



CREATE TABLE IF NOT EXISTS "public"."silver" (
    "discord_username" "text",
    "osu_username" "text",
    "initial_pp" smallint,
    "current_pp" integer,
    "pp_change" integer GENERATED ALWAYS AS (("current_pp" - "initial_pp")) STORED,
    "global_rank" integer,
    "id" integer NOT NULL,
    "percentage_change" numeric GENERATED ALWAYS AS ("round"((((("current_pp" - "initial_pp"))::numeric * 100.0) / ("initial_pp")::numeric), 2)) STORED,
    "ii" real,
    "discord_id" bigint
);


ALTER TABLE "public"."silver" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."silver_1" (
    "discord_username" "text",
    "osu_username" "text",
    "initial_pp" smallint,
    "current_pp" integer,
    "pp_change" integer,
    "global_rank" integer,
    "id" integer,
    "percentage_change" numeric,
    "ii" numeric(10,2)
);


ALTER TABLE "public"."silver_1" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."silver_2" (
    "discord_username" "text",
    "osu_username" "text",
    "initial_pp" smallint,
    "current_pp" integer,
    "pp_change" integer,
    "global_rank" integer,
    "id" integer,
    "percentage_change" numeric,
    "ii" numeric(10,2)
);


ALTER TABLE "public"."silver_2" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."silver_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."silver_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."silver_id_seq" OWNED BY "public"."silver"."id";



ALTER TABLE ONLY "public"."bronze" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."bronze_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."challenged" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."challenged_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."challenger" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."challenger_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."diamond" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."diamond_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."elite" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."elite_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."gold" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."gold_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."master" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."master_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."novice" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."ranker_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."platinum" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."platinum_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."silver" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."silver_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."seasons"
    ADD CONSTRAINT "Seasons_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."discord_osu"
    ADD CONSTRAINT "_discord_osu_osu_id_key" UNIQUE ("osu_id");



ALTER TABLE ONLY "public"."bronze"
    ADD CONSTRAINT "bronze_discord_username_key" UNIQUE ("discord_username");



ALTER TABLE ONLY "public"."bronze"
    ADD CONSTRAINT "bronze_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."challenged"
    ADD CONSTRAINT "challenged_challenge_id_key" UNIQUE ("challenge_id");



ALTER TABLE ONLY "public"."challenged"
    ADD CONSTRAINT "challenged_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."challenger"
    ADD CONSTRAINT "challenger_challenge_id_key" UNIQUE ("challenge_id");



ALTER TABLE ONLY "public"."challenger"
    ADD CONSTRAINT "challenger_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."diamond"
    ADD CONSTRAINT "diamond_discord_username_key" UNIQUE ("discord_username");



ALTER TABLE ONLY "public"."diamond"
    ADD CONSTRAINT "diamond_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."discord_osu"
    ADD CONSTRAINT "discord_osu_discord_id_key" UNIQUE ("discord_id");



ALTER TABLE ONLY "public"."discord_osu"
    ADD CONSTRAINT "discord_osu_discord_username_key" UNIQUE ("discord_username");



ALTER TABLE ONLY "public"."discord_osu"
    ADD CONSTRAINT "discord_osu_pkey" PRIMARY KEY ("discord_username");



ALTER TABLE ONLY "public"."elite"
    ADD CONSTRAINT "elite_discord_username_key" UNIQUE ("discord_username");



ALTER TABLE ONLY "public"."elite"
    ADD CONSTRAINT "elite_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."gold"
    ADD CONSTRAINT "gold_discord_username_key" UNIQUE ("discord_username");



ALTER TABLE ONLY "public"."gold"
    ADD CONSTRAINT "gold_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."historical_points"
    ADD CONSTRAINT "historical_point_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."historical_points"
    ADD CONSTRAINT "historical_points_osu_username_key" UNIQUE ("osu_username");



ALTER TABLE ONLY "public"."master"
    ADD CONSTRAINT "master_discord_username_key" UNIQUE ("discord_username");



ALTER TABLE ONLY "public"."master"
    ADD CONSTRAINT "master_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."mesg_id"
    ADD CONSTRAINT "mesg_id_id_key" UNIQUE ("id");



ALTER TABLE ONLY "public"."mesg_id"
    ADD CONSTRAINT "mesg_id_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."miscellaneous"
    ADD CONSTRAINT "miscellaneous_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."novice"
    ADD CONSTRAINT "novice_discord_username_key" UNIQUE ("discord_username");



ALTER TABLE ONLY "public"."platinum"
    ADD CONSTRAINT "platinum_discord_username_key" UNIQUE ("discord_username");



ALTER TABLE ONLY "public"."platinum"
    ADD CONSTRAINT "platinum_id_key" UNIQUE ("id");



ALTER TABLE ONLY "public"."platinum"
    ADD CONSTRAINT "platinum_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."novice"
    ADD CONSTRAINT "ranker_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."rivals"
    ADD CONSTRAINT "rivals_id_key" UNIQUE ("challenge_id");



ALTER TABLE ONLY "public"."rivals"
    ADD CONSTRAINT "rivals_pkey" PRIMARY KEY ("challenge_id");



ALTER TABLE ONLY "public"."silver"
    ADD CONSTRAINT "silver_discord_username_key" UNIQUE ("discord_username");



ALTER TABLE ONLY "public"."silver"
    ADD CONSTRAINT "silver_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."challenged"
    ADD CONSTRAINT "challenged_challenge_id_fkey" FOREIGN KEY ("challenge_id") REFERENCES "public"."rivals"("challenge_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."challenged"
    ADD CONSTRAINT "challenged_discord_username_fkey" FOREIGN KEY ("discord_username") REFERENCES "public"."discord_osu"("discord_username") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."challenger"
    ADD CONSTRAINT "challenger_challenge_id_fkey" FOREIGN KEY ("challenge_id") REFERENCES "public"."rivals"("challenge_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."challenger"
    ADD CONSTRAINT "challenger_discord_username_fkey" FOREIGN KEY ("discord_username") REFERENCES "public"."discord_osu"("discord_username") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."bronze"
    ADD CONSTRAINT "fk_bronze_discord" FOREIGN KEY ("discord_id") REFERENCES "public"."discord_osu"("discord_id");



ALTER TABLE ONLY "public"."challenged"
    ADD CONSTRAINT "fk_challenged_discord" FOREIGN KEY ("discord_id") REFERENCES "public"."discord_osu"("discord_id");



ALTER TABLE ONLY "public"."challenger"
    ADD CONSTRAINT "fk_challenger_discord" FOREIGN KEY ("discord_id") REFERENCES "public"."discord_osu"("discord_id");



ALTER TABLE ONLY "public"."diamond"
    ADD CONSTRAINT "fk_diamond_discord" FOREIGN KEY ("discord_id") REFERENCES "public"."discord_osu"("discord_id");



ALTER TABLE ONLY "public"."bronze"
    ADD CONSTRAINT "fk_discord_username" FOREIGN KEY ("discord_username") REFERENCES "public"."discord_osu"("discord_username") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."diamond"
    ADD CONSTRAINT "fk_discord_username" FOREIGN KEY ("discord_username") REFERENCES "public"."discord_osu"("discord_username") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."elite"
    ADD CONSTRAINT "fk_discord_username" FOREIGN KEY ("discord_username") REFERENCES "public"."discord_osu"("discord_username") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."gold"
    ADD CONSTRAINT "fk_discord_username" FOREIGN KEY ("discord_username") REFERENCES "public"."discord_osu"("discord_username") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."master"
    ADD CONSTRAINT "fk_discord_username" FOREIGN KEY ("discord_username") REFERENCES "public"."discord_osu"("discord_username") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."novice"
    ADD CONSTRAINT "fk_discord_username" FOREIGN KEY ("discord_username") REFERENCES "public"."discord_osu"("discord_username") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."platinum"
    ADD CONSTRAINT "fk_discord_username" FOREIGN KEY ("discord_username") REFERENCES "public"."discord_osu"("discord_username") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."silver"
    ADD CONSTRAINT "fk_discord_username" FOREIGN KEY ("discord_username") REFERENCES "public"."discord_osu"("discord_username") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."elite"
    ADD CONSTRAINT "fk_elite_discord" FOREIGN KEY ("discord_id") REFERENCES "public"."discord_osu"("discord_id");



ALTER TABLE ONLY "public"."gold"
    ADD CONSTRAINT "fk_gold_discord" FOREIGN KEY ("discord_id") REFERENCES "public"."discord_osu"("discord_id");



ALTER TABLE ONLY "public"."historical_points"
    ADD CONSTRAINT "fk_historical_points_discord" FOREIGN KEY ("discord_id") REFERENCES "public"."discord_osu"("discord_id");



ALTER TABLE ONLY "public"."master"
    ADD CONSTRAINT "fk_master_discord" FOREIGN KEY ("discord_id") REFERENCES "public"."discord_osu"("discord_id");



ALTER TABLE ONLY "public"."novice"
    ADD CONSTRAINT "fk_novice_discord" FOREIGN KEY ("discord_id") REFERENCES "public"."discord_osu"("discord_id");



ALTER TABLE ONLY "public"."platinum"
    ADD CONSTRAINT "fk_platinum_discord" FOREIGN KEY ("discord_id") REFERENCES "public"."discord_osu"("discord_id");



ALTER TABLE ONLY "public"."silver"
    ADD CONSTRAINT "fk_silver_discord" FOREIGN KEY ("discord_id") REFERENCES "public"."discord_osu"("discord_id");



ALTER TABLE ONLY "public"."historical_points"
    ADD CONSTRAINT "historical_points_discord_username_fkey" FOREIGN KEY ("discord_username") REFERENCES "public"."discord_osu"("discord_username") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."mesg_id"
    ADD CONSTRAINT "mesg_id_challenge_id_fkey" FOREIGN KEY ("challenge_id") REFERENCES "public"."rivals"("challenge_id") ON DELETE CASCADE;



ALTER TABLE "public"."bronze" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."challenged" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."challenger" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."diamond" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."discord_osu" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."elite" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."gold" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."historical_points" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."master" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."mesg_id" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."miscellaneous" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."novice" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."platinum" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."rivals" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."seasons" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."silver" ENABLE ROW LEVEL SECURITY;




ALTER PUBLICATION "supabase_realtime" OWNER TO "postgres";


GRANT USAGE ON SCHEMA "public" TO "postgres";
GRANT USAGE ON SCHEMA "public" TO "anon";
GRANT USAGE ON SCHEMA "public" TO "authenticated";
GRANT USAGE ON SCHEMA "public" TO "service_role";
GRANT USAGE ON SCHEMA "public" TO "arirret25";

























































































































































GRANT ALL ON FUNCTION "public"."accept_challenge"("p_challenge_id" integer, OUT "out_challenger_id" bigint, OUT "out_challenged_id" bigint, OUT "out_for_pp" numeric) TO "anon";
GRANT ALL ON FUNCTION "public"."accept_challenge"("p_challenge_id" integer, OUT "out_challenger_id" bigint, OUT "out_challenged_id" bigint, OUT "out_for_pp" numeric) TO "authenticated";
GRANT ALL ON FUNCTION "public"."accept_challenge"("p_challenge_id" integer, OUT "out_challenger_id" bigint, OUT "out_challenged_id" bigint, OUT "out_for_pp" numeric) TO "service_role";



GRANT ALL ON FUNCTION "public"."add_points"("player" "text", "given_points" integer, OUT "new_points" integer, OUT "new_seasonal_points" integer) TO "anon";
GRANT ALL ON FUNCTION "public"."add_points"("player" "text", "given_points" integer, OUT "new_points" integer, OUT "new_seasonal_points" integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."add_points"("player" "text", "given_points" integer, OUT "new_points" integer, OUT "new_seasonal_points" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."award_seasonal_points"("league_table_name" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."award_seasonal_points"("league_table_name" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."award_seasonal_points"("league_table_name" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."award_weekly_winner"("league_table_name" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."award_weekly_winner"("league_table_name" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."award_weekly_winner"("league_table_name" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."backup_historical_points"("column_name" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."backup_historical_points"("column_name" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."backup_historical_points"("column_name" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."decline_challenge"("p_challenge_id" integer, OUT "out_challenger_id" bigint, OUT "out_challenged_id" bigint, OUT "out_for_pp" numeric) TO "anon";
GRANT ALL ON FUNCTION "public"."decline_challenge"("p_challenge_id" integer, OUT "out_challenger_id" bigint, OUT "out_challenged_id" bigint, OUT "out_for_pp" numeric) TO "authenticated";
GRANT ALL ON FUNCTION "public"."decline_challenge"("p_challenge_id" integer, OUT "out_challenger_id" bigint, OUT "out_challenged_id" bigint, OUT "out_for_pp" numeric) TO "service_role";



GRANT ALL ON FUNCTION "public"."duplicate_table"("source_table" "text", "new_table_name" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."duplicate_table"("source_table" "text", "new_table_name" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."duplicate_table"("source_table" "text", "new_table_name" "text") TO "service_role";



GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."discord_osu" TO "anon";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."discord_osu" TO "authenticated";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."discord_osu" TO "service_role";
GRANT SELECT ON TABLE "public"."discord_osu" TO "arirret25";



GRANT ALL ON FUNCTION "public"."get_mismatched_rows"() TO "anon";
GRANT ALL ON FUNCTION "public"."get_mismatched_rows"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_mismatched_rows"() TO "service_role";



GRANT ALL ON FUNCTION "public"."log_rivals"("challenger_uname" "text", "challenged_uname" "text", "for_pp" integer, "league" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."log_rivals"("challenger_uname" "text", "challenged_uname" "text", "for_pp" integer, "league" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."log_rivals"("challenger_uname" "text", "challenged_uname" "text", "for_pp" integer, "league" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."log_to_challenge_table"("discord_username" "text", "osu_username" "text", "discord_id" bigint, "challenge_id" "text", "challenge_table" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."log_to_challenge_table"("discord_username" "text", "osu_username" "text", "discord_id" bigint, "challenge_id" "text", "challenge_table" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."log_to_challenge_table"("discord_username" "text", "osu_username" "text", "discord_id" bigint, "challenge_id" "text", "challenge_table" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."reset_seasonal_points"() TO "anon";
GRANT ALL ON FUNCTION "public"."reset_seasonal_points"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."reset_seasonal_points"() TO "service_role";



GRANT ALL ON FUNCTION "public"."sync_rivals"() TO "anon";
GRANT ALL ON FUNCTION "public"."sync_rivals"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."sync_rivals"() TO "service_role";



GRANT ALL ON FUNCTION "public"."sync_table_pp"("tbl_name" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."sync_table_pp"("tbl_name" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sync_table_pp"("tbl_name" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."update_init_pp"("tbl_name" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."update_init_pp"("tbl_name" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_init_pp"("tbl_name" "text") TO "service_role";


















GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."seasons" TO "anon";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."seasons" TO "authenticated";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."seasons" TO "service_role";
GRANT SELECT ON TABLE "public"."seasons" TO "arirret25";



GRANT ALL ON SEQUENCE "public"."Seasons_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."Seasons_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."Seasons_id_seq" TO "service_role";



GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."bronze" TO "anon";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."bronze" TO "authenticated";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."bronze" TO "service_role";
GRANT SELECT ON TABLE "public"."bronze" TO "arirret25";



GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."bronze_1" TO "anon";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."bronze_1" TO "authenticated";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."bronze_1" TO "service_role";
GRANT SELECT ON TABLE "public"."bronze_1" TO "arirret25";



GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."bronze_2" TO "anon";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."bronze_2" TO "authenticated";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."bronze_2" TO "service_role";
GRANT SELECT ON TABLE "public"."bronze_2" TO "arirret25";



GRANT ALL ON SEQUENCE "public"."bronze_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."bronze_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."bronze_id_seq" TO "service_role";



GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."challenged" TO "anon";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."challenged" TO "authenticated";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."challenged" TO "service_role";
GRANT SELECT ON TABLE "public"."challenged" TO "arirret25";



GRANT ALL ON SEQUENCE "public"."challenged_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."challenged_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."challenged_id_seq" TO "service_role";



GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."challenger" TO "anon";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."challenger" TO "authenticated";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."challenger" TO "service_role";
GRANT SELECT ON TABLE "public"."challenger" TO "arirret25";



GRANT ALL ON SEQUENCE "public"."challenger_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."challenger_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."challenger_id_seq" TO "service_role";



GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."diamond" TO "anon";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."diamond" TO "authenticated";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."diamond" TO "service_role";
GRANT SELECT ON TABLE "public"."diamond" TO "arirret25";



GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."diamond_1" TO "anon";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."diamond_1" TO "authenticated";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."diamond_1" TO "service_role";
GRANT SELECT ON TABLE "public"."diamond_1" TO "arirret25";



GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."diamond_2" TO "anon";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."diamond_2" TO "authenticated";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."diamond_2" TO "service_role";
GRANT SELECT ON TABLE "public"."diamond_2" TO "arirret25";



GRANT ALL ON SEQUENCE "public"."diamond_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."diamond_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."diamond_id_seq" TO "service_role";



GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."elite" TO "anon";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."elite" TO "authenticated";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."elite" TO "service_role";
GRANT SELECT ON TABLE "public"."elite" TO "arirret25";



GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."elite_1" TO "anon";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."elite_1" TO "authenticated";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."elite_1" TO "service_role";
GRANT SELECT ON TABLE "public"."elite_1" TO "arirret25";



GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."elite_2" TO "anon";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."elite_2" TO "authenticated";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."elite_2" TO "service_role";
GRANT SELECT ON TABLE "public"."elite_2" TO "arirret25";



GRANT ALL ON SEQUENCE "public"."elite_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."elite_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."elite_id_seq" TO "service_role";



GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."gold" TO "anon";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."gold" TO "authenticated";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."gold" TO "service_role";
GRANT SELECT ON TABLE "public"."gold" TO "arirret25";



GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."gold_1" TO "anon";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."gold_1" TO "authenticated";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."gold_1" TO "service_role";
GRANT SELECT ON TABLE "public"."gold_1" TO "arirret25";



GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."gold_2" TO "anon";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."gold_2" TO "authenticated";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."gold_2" TO "service_role";
GRANT SELECT ON TABLE "public"."gold_2" TO "arirret25";



GRANT ALL ON SEQUENCE "public"."gold_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."gold_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."gold_id_seq" TO "service_role";



GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."historical_points" TO "anon";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."historical_points" TO "authenticated";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."historical_points" TO "service_role";
GRANT SELECT ON TABLE "public"."historical_points" TO "arirret25";



GRANT ALL ON SEQUENCE "public"."historical_point_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."historical_point_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."historical_point_id_seq" TO "service_role";



GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."master" TO "anon";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."master" TO "authenticated";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."master" TO "service_role";
GRANT SELECT ON TABLE "public"."master" TO "arirret25";



GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."master_1" TO "anon";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."master_1" TO "authenticated";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."master_1" TO "service_role";
GRANT SELECT ON TABLE "public"."master_1" TO "arirret25";



GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."master_2" TO "anon";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."master_2" TO "authenticated";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."master_2" TO "service_role";
GRANT SELECT ON TABLE "public"."master_2" TO "arirret25";



GRANT ALL ON SEQUENCE "public"."master_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."master_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."master_id_seq" TO "service_role";



GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."mesg_id" TO "anon";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."mesg_id" TO "authenticated";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."mesg_id" TO "service_role";
GRANT SELECT ON TABLE "public"."mesg_id" TO "arirret25";



GRANT ALL ON SEQUENCE "public"."mesg_id_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."mesg_id_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."mesg_id_id_seq" TO "service_role";



GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."miscellaneous" TO "anon";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."miscellaneous" TO "authenticated";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."miscellaneous" TO "service_role";
GRANT SELECT ON TABLE "public"."miscellaneous" TO "arirret25";



GRANT ALL ON SEQUENCE "public"."miscellaneous_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."miscellaneous_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."miscellaneous_id_seq" TO "service_role";



GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."novice" TO "anon";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."novice" TO "authenticated";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."novice" TO "service_role";
GRANT SELECT ON TABLE "public"."novice" TO "arirret25";



GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."novice_2" TO "anon";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."novice_2" TO "authenticated";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."novice_2" TO "service_role";
GRANT SELECT ON TABLE "public"."novice_2" TO "arirret25";



GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."platinum" TO "anon";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."platinum" TO "authenticated";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."platinum" TO "service_role";
GRANT SELECT ON TABLE "public"."platinum" TO "arirret25";



GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."platinum_1" TO "anon";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."platinum_1" TO "authenticated";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."platinum_1" TO "service_role";
GRANT SELECT ON TABLE "public"."platinum_1" TO "arirret25";



GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."platinum_2" TO "anon";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."platinum_2" TO "authenticated";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."platinum_2" TO "service_role";
GRANT SELECT ON TABLE "public"."platinum_2" TO "arirret25";



GRANT ALL ON SEQUENCE "public"."platinum_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."platinum_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."platinum_id_seq" TO "service_role";



GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."ranker_1" TO "anon";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."ranker_1" TO "authenticated";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."ranker_1" TO "service_role";
GRANT SELECT ON TABLE "public"."ranker_1" TO "arirret25";



GRANT ALL ON SEQUENCE "public"."ranker_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."ranker_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."ranker_id_seq" TO "service_role";



GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."rivals" TO "anon";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."rivals" TO "authenticated";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."rivals" TO "service_role";
GRANT SELECT ON TABLE "public"."rivals" TO "arirret25";



GRANT ALL ON SEQUENCE "public"."rivals_challenge_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."rivals_challenge_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."rivals_challenge_id_seq" TO "service_role";



GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."silver" TO "anon";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."silver" TO "authenticated";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."silver" TO "service_role";
GRANT SELECT ON TABLE "public"."silver" TO "arirret25";



GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."silver_1" TO "anon";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."silver_1" TO "authenticated";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."silver_1" TO "service_role";
GRANT SELECT ON TABLE "public"."silver_1" TO "arirret25";



GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."silver_2" TO "anon";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."silver_2" TO "authenticated";
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE "public"."silver_2" TO "service_role";
GRANT SELECT ON TABLE "public"."silver_2" TO "arirret25";



GRANT ALL ON SEQUENCE "public"."silver_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."silver_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."silver_id_seq" TO "service_role";









ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLES TO "service_role";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT SELECT ON TABLES TO "arirret25";































