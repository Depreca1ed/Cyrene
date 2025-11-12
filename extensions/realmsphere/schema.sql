-- These tables are for this category and this category alone.
CREATE TABLE IF NOT EXISTS Profiles (
    user_id BIGINT PRIMARY KEY,
    balance INTEGER NOT NULL DEFAULT 0,
    aeon_path INTEGER NOT NULL DEFAULT 0,
    element INTEGER NOT NULL DEFAULT 0,
    playable_char TEXT,
);

CREATE TABLE IF NOT EXISTS Aeon (
    aeon_name TEXT PRIMARY KEY,
    alt_name TEXT,
    aeon_path TEXT NOT NULL,
    perk JSONB,
);

CREATE TABLE IF NOT EXISTS Characters (
    char_name TEXT PRIMARY KEY,
    aeon_path TEXT references Aeon(aeon_path),
    theme TEXT NOT NULL references Themes (name),
    perk JSONB,
);

CREATE TABLE IF NOT EXISTS Cards (
    id SERIAL PRIMARY KEY,
    card_name TEXT NOT NULL,
    rarity INTEGER NOT NULL,
    playable_characters TEXT [] references Characters (char_name),
    flag INTEGER NOT NULL,
);