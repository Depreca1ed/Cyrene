-- These tables are for this category and this category alone.
CREATE TABLE IF NOT EXISTS Aeon (
    aeon_path TEXT NOT NULL PRIMARY KEY,
    aeon_name TEXT,
    alt_name TEXT,
    perk JSONB
);

CREATE TABLE IF NOT EXISTS Profiles (
    user_id BIGINT PRIMARY KEY,
    balance INTEGER NOT NULL DEFAULT 0,
    aeon_path TEXT NOT NULL references Aeon (aeon_path),
    element INTEGER NOT NULL DEFAULT 0,
    playable_char TEXT
);

CREATE TABLE IF NOT EXISTS Themes (
    name TEXT NOT NULL PRIMARY KEY,
    description TEXT,
    disabled BOOLEAN NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS Characters (
    char_name TEXT PRIMARY KEY,
    aeon_path TEXT references Aeon(aeon_path),
    theme TEXT NOT NULL references Themes (name),
    perk JSONB
);

CREATE TABLE IF NOT EXISTS Cards (
    id SERIAL PRIMARY KEY,
    card_name TEXT NOT NULL,
    rarity INTEGER NOT NULL,
    flag INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS CardCharactersRelation (
    id INTEGER NOT NULL references Cards (id),
    character TEXT NOT NULL references Characters(char_name)
);

CREATE TABLE IF NOT EXISTS CardInventory (
    user_id BIGINT NOT NULL,
    card_id INTEGER NOT NULL references Cards (id),
    quantity INTEGER DEFAULT 1,
    PRIMARY KEY (user_id, card_id)
);