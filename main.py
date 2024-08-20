from time import sleep
from dotenv import load_dotenv
import sqlite3
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from pprint import pprint

# import sys
# import argparse
# import logging

# load enviromental variables
load_dotenv()

# spotify authentication
scope = "user-top-read,user-read-playback-state,user-modify-playback-state,playlist-modify-private,playlist-modify-public,user-read-recently-played,user-library-read,user-library-modify"
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))
username = "dfd0430"

# sqlite initialization
conn = sqlite3.connect("spotify.db")
c = conn.cursor()
c.execute(
    """CREATE TABLE if not exists tracks (
            id TEXT PRIMARY KEY,
            times_skipped INTEGER,
            times_added INTEGER,
            times_puton INTEGER
        )"""
)
conn.commit()


def lists_to_database(skiplist, addlist, put_on):
    for id in skiplist:

        song_to_database_skip(id)

    for id in addlist:
        song_to_database_add(id)
    for id in put_on:
        song_to_database_put(id)


def check_id_exists(id):

    c.execute(f"SELECT EXISTS(SELECT 1 FROM tracks WHERE id = ?)", (id,))
    exists = c.fetchone()[0]
    return exists


def song_to_database_skip(id):
    if check_id_exists(id):
        c.execute(f"SELECT times_skipped FROM tracks WHERE id = ?", (id,))
        row = c.fetchone()
        i = row[0] + 1

        c.execute(
            """UPDATE tracks SET times_skipped = :times_skipped
                            WHERE id = :id""",
            {"id": id, "times_skipped": i},
        )
    else:

        c.execute(
            """   INSERT INTO tracks VALUES (:id,:times_skipped,:times_added,:times_puton)""",
            {"id": id, "times_skipped": 1, "times_added": 0, "times_puton": 0},
        )


def song_to_database_add(id):
    if check_id_exists(id):
        c.execute(f"SELECT times_added FROM tracks WHERE id = ?", (id,))
        row = c.fetchone()
        i = row[0] + 1
        with conn:
            c.execute(
                """UPDATE tracks SET times_added = :times_added
                                WHERE id = :id""",
                {"id": id, "times_added": i},
            )
    else:
        with conn:
            c.execute(
                """   INSERT INTO tracks VALUES (:id,:times_skipped,:times_added,:times_puton)""",
                {"id": id, "times_skipped": 0, "times_added": 1, "times_puton": 0},
            )


def song_to_database_put(id):
    if check_id_exists(id):
        c.execute(f"SELECT times_puton FROM tracks WHERE id = ?", (id,))
        row = c.fetchone()
        i = row[0] + 1
        with conn:
            c.execute(
                """UPDATE tracks SET times_puton = :times_puton
                                WHERE id = :id""",
                {"id": id, "times_puton": i},
            )
    else:
        with conn:
            c.execute(
                """   INSERT INTO tracks VALUES (:song,:times_skipped,:times_added,:times_puton)""",
                {"song": id, "times_skipped": 0, "times_added": 0, "times_puton": 1},
            )


def get_recently_played_ids():
    recentlyplayed = sp.current_user_recently_played(limit=5)
    recentlyplayed_id = [songs["track"]["id"] for songs in recentlyplayed["items"]]
    return recentlyplayed_id


def get_queue_ids():
    current_queue = sp.queue()
    if current_queue is None:
        current_queue = []

    current_queue_ids = [songs["id"] for songs in current_queue["queue"]]
    return current_queue_ids[:20]


def check_same_queue(old_queue_ids, current_queue_ids):
    amount_of_same_songs = 0
    for old_queue_id in old_queue_ids:
        if old_queue_id in current_queue_ids:
            amount_of_same_songs += 1
    if amount_of_same_songs > 9:
        return True
    else:
        return False


def song_from_queue(old_queue_ids, current_song_id):
    if current_song_id in old_queue_ids:
        return True
    else:
        return False


def add_skip(song_id):
    skiplist.append(song_id)


def remove_skip(song_id):
    if song_id in skiplist:
        skiplist.remove(song_id)


def add_preliminary_skip(song_id):
    if song_id not in preliminary_skiplist:
        preliminary_skiplist.append(song_id)


def remove_preliminary_skip(song_id):
    if song_id in preliminary_skiplist:
        preliminary_skiplist.remove(song_id)


def convert_to_skiplist():
    for song_id in preliminary_skiplist:
        skiplist.append(song_id)
        preliminary_skiplist.remove(song_id)


def resuming():
    try:
        if sp.current_playback()["actions"]["disallows"]["skipping_prev"]:
            return False
    except Exception:
        pass
    return True


def clear_preliminary_skiplist():
    for song_id in preliminary_skiplist:
        remove_preliminary_skip(song_id)


def check_album():

    for album_name in sp.queue()["queue"]:
        if album_name != None:
            return False
        if (
            album_name["album"]["name"]
            != sp.current_playback()["item"]["album"]["name"]
        ):
            return False
    return True


def check_skip(
    current_song_progress,
    current_song_id,
    song_duration,
    song_changed,
):

    if not check_album():
        if song_changed:
            convert_to_skiplist()
            if song_from_queue(old_queue_ids, current_song_id) and resuming():
                i = 0
                while old_queue_ids[i] != current_song_id:
                    add_skip(old_queue_ids[i])
                    i += 1
        if current_song_progress > (song_duration * 0.7):
            remove_preliminary_skip(current_song_id)
        else:
            add_preliminary_skip(current_song_id)


def check_in_queue(old_queue_ids, current_queue_ids):

    if check_same_queue(old_queue_ids, current_queue_ids):
        for i in range(len(current_queue_ids)):
            if current_queue_ids[i] not in old_queue_ids and i < 10:
                addlist.append(current_queue_ids[i])


def get_timestamp_current():
    return sp.current_playback()["timestamp"]


def get_finished():
    return (
        sp.current_playback()["timestamp"]
        + sp.current_playback()["item"]["duration_ms"]
    )


def check_put_on(old_queue_ids, current_queue_ids, current_song_id):
    if (
        not check_same_queue(old_queue_ids, current_queue_ids)
        and current_song_id not in old_queue_ids
        and song_changed
    ):
        put_on.append(current_song_id)


def clear_playlist(playlist_id):
    results = sp.playlist_tracks(playlist_id)
    tracks = results["items"]
    if len(tracks) > 0:
        sp.playlist_remove_all_occurrences_of_items(
            playlist_id, [track["track"]["id"] for track in tracks]
        )


skiplist = []
preliminary_skiplist = []
addlist = []
put_on = []

old_queue_ids = []
song_before = ""
last_song_name = ""
old_recently_played_names = []
count = 0
song_changed = False

# with conn:
#     c.execute(f"SELECT * FROM tracks")
#     rows = c.fetchall()
# for row in rows:
#     print(row)  # Each row is a tuple containing column values
#     pprint(sp.tracks([row[0]])["tracks"][0]["name"])
while True:
    if sp.current_playback() == None:
        sleep(5)
    else:
        # get info current state
        current_queue_ids = get_queue_ids()
        current_song_id = sp.current_playback()["item"]["id"]
        current_recently_playes_id = get_recently_played_ids()

        if last_song_name != current_song_id:
            song_changed = True
        else:
            song_changed = False

        # check for skips and such
        check_skip(
            sp.current_playback()["progress_ms"],
            current_song_id,
            sp.current_playback()["item"]["duration_ms"],
            song_changed,
        )
        # if song_before == "":
        #     song_before = current_song_id
        # elif song_changed:
        #     song_before =last_song_name

        check_put_on(old_queue_ids, current_queue_ids, current_song_id)
        check_in_queue(old_queue_ids, current_queue_ids)

        old_queue_ids = current_queue_ids
        last_song_name = current_song_id
        old_recently_played_names = current_recently_playes_id

        # print("skiplist")
        # print(skiplist)
        # print("addlist:")
        # print(addlist)
        # print("put on:")
        # print(put_on)
        # print("-----------------------------------------------")

        if len(skiplist) + len(addlist) + len(put_on) > 10:
            lists_to_database(skiplist, addlist, put_on)
            skiplist = []
            addlist = []
            put_on = []

        # with conn:
        #     c.execute(f"SELECT * FROM tracks")
        #     rows = c.fetchall()
        # for row in rows:
        #     print(row)  # Each row is a tuple containing column values
        #     # pprint(sp.tracks([row[0]])["tracks"][0]["name"])

        sleep(5)
#
