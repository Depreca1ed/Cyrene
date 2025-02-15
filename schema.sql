BEGIN;

DO $$ BEGIN
        CREATE TYPE BlacklistTypes AS ENUM('guild', 'user');
EXCEPTION
        WHEN duplicate_object THEN null;
END $$;

CREATE TABLE IF NOT EXISTS Blacklists (
    snowflake BIGINT NOT NULL PRIMARY KEY,
    reason TEXT NOT NULL,
    lasts_until TIMESTAMP,
    blacklist_type BlacklistTypes NOT NULL
);

CREATE TABLE IF NOT EXISTS Prefixes (
    guild BIGINT NOT NULL,
    prefix TEXT NOT NULL,
    PRIMARY KEY (guild, prefix)
);

CREATE TABLE IF NOT EXISTS Waifus (
    id BIGINT PRIMARY KEY,
    smashes INTEGER NOT NULL DEFAULT 0,
    passes INTEGER NOT NULL DEFAULT 0,
    nsfw BOOLEAN NOT NUll
);

CREATE TABLE IF NOT EXISTS WaifuFavourites (
    id BIGINT references Waifus (id),
    user_id BIGINT NOT NULL,
    nsfw BOOLEAN NOT NULL,
    tm TIMESTAMP NOT NULL,
    PRIMARY KEY (id, user_id)
);

CREATE TABLE IF NOT EXISTS Errors (
    id SERIAL PRIMARY KEY,
    command TEXT NOT NULL,
    user_id BIGINT NOT NULL,
    guild BIGINT,
    error TEXT NOT NULL,
    full_error TEXT NOT NULL,
    message_url TEXT NOT NULL,
    occured_when TIMESTAMP NOT NULL,
    fixed BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS ErrorReminders (
    id BIGINT references Errors (id),
    user_id BIGINT NOT NULL,
    PRIMARY KEY (id, user_id)
);

CREATE TABLE IF NOT EXISTS CommandStats (
    usage_count INTEGER NOT NULL,
    command_name TEXT NOT NULL,
    user_id BIGINT NOT NULL,
    channel_id BIGINT DEFAULT 0,
    guild_id BIGINT DEFAULT 0,
    PRIMARY KEY (command_name, user_id, channel_id, guild_id)
);

COMMIT;
