-- Error tables
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

-- Miscellanious
CREATE TABLE IF NOT EXISTS Timers (
        id SERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        reserved_type INTEGER,
        expires TIMESTAMP WITH TIME ZONE NOT NULL,
        data JSONB
);

CREATE TABLE IF NOT EXISTS Blacklists (
        snowflake BIGINT NOT NULL PRIMARY KEY,
        reason TEXT NOT NULL,
        lasts_until TIMESTAMP,
        blacklist_type INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS Prefixes (
        guild BIGINT NOT NULL,
        prefix TEXT NOT NULL,
        PRIMARY KEY (guild, prefix)
);

CREATE TABLE IF NOT EXISTS Webhooks (
        LOG_TYPE TEXT NOT NULL PRIMARY KEY,
        LOG_ENDPOINT TEXT
);

-- Waifus
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

CREATE TABLE IF NOT EXISTS WaifuAPIEntries (
        file_url TEXT PRIMARY KEY,
        added_by BIGINT NOT NULL,
        nsfw BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS GachaPulledCards (
        channel_id BIGINT NOT NULL,
        message_id BIGINT NOT NULL,
        user_id BIGINT NOT NULL,
        card_id INTEGER NOT NULL,
        card_name TEXT NOT NULL,
        rarity INTEGER NOT NULL,
        pull_source INTEGER NOT NULL,
);

COMMIT;