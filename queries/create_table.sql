CREATE TABLE
    if not exists tracks
(
    song_id TEXT PRIMARY KEY,
    times_skipped INTEGER,
    times_added INTEGER,
    times_put_on INTEGER,
    name_song TEXT
)