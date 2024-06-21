from time import sleep

import sqlite3
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from pprint import pprint
import sys
import argparse
import logging
#spotify authentication
scope = "user-top-read,user-read-playback-state,user-modify-playback-state,playlist-modify-private,playlist-modify-public,user-read-recently-played,user-library-read,user-library-modify"
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))
username = "dfd0430"

#sqlite initialization
conn=sqlite3.connect(':memory:')
c = conn.cursor()
c.execute("""CREATE TABLE if not exists tracks (
            id TEXT PRIMARY KEY,
            times_skipped INTEGER,
            times_added INTEGER,
            times_puton INTEGER
        )""")
conn.commit()


def lists_to_database(skiplist,addlist,put_on):
    for song in skiplist:

        song_to_database_skip(song)

    for song in addlist:
        song_to_database_add(song)
    for song in put_on:
        song_to_database_put(song)

def check_id_exists(id):

    c.execute(f"SELECT EXISTS(SELECT 1 FROM tracks WHERE id = ?)", (id,))
    exists = c.fetchone()[0]
    return exists

def song_to_database_skip(id):
    if(check_id_exists(id)):
        c.execute(f"SELECT times_skipped FROM tracks WHERE id = ?", (id,))
        row = c.fetchone()
        print("this is the one:")
        print(row)
        i= row[0] + 1

        c.execute("""UPDATE tracks SET times_skipped = :times_skipped
                            WHERE id = :id""",
                      {'id':id,'times_skipped':i})
    else:

        c.execute("""   INSERT INTO tracks VALUES (:id,:times_skipped,:times_added,:times_puton)""",{"id":id,"times_skipped":1,"times_added":0,"times_puton":0})

def song_to_database_add(id):
    if (check_id_exists(id)):
        c.execute(f"SELECT times_added FROM tracks WHERE id = ?", (id,))
        row = c.fetchone()
        i = row[0] + 1
        with conn:
            c.execute("""UPDATE tracks SET times_added = :times_added
                                WHERE id = :id""",
                      {'id': id, 'times_added': i})
    else:
        with conn:
            c.execute("""   INSERT INTO tracks VALUES (:id,:times_skipped,:times_added,:times_puton)""",
                      {"id": id, "times_skipped": 0, "times_added": 1, "times_puton": 0})

def song_to_database_put(id):
    if (check_id_exists(id)):
        c.execute(f"SELECT times_puton FROM tracks WHERE id = ?", (id,))
        row = c.fetchone()
        i = row[0] + 1
        with conn:
            c.execute("""UPDATE tracks SET times_puton = :times_puton
                                WHERE id = :id""",
                      {'id': id, 'times_puton': i})
    else:
        with conn:
            c.execute("""   INSERT INTO tracks VALUES (:song,:times_skipped,:times_added,:times_puton)""",
                      {"song": id, "times_skipped": 0, "times_added": 0, "times_puton": 1})

def get_recently_played_names():
    recentlyplayed = sp.current_user_recently_played(limit=5)
    recentlyplayed_names = [songs["track"]["name"] for songs in recentlyplayed["items"]]
    return recentlyplayed_names


def get_queue_names():
    current_queue = sp.queue()
    if current_queue is None:
        current_queue = []

    current_queue_names = [songs["name"] for songs in current_queue["queue"]]
    return current_queue_names[:20]


def check_same_queue(old_queue_names, current_queue_names):
    amount_of_same_songs = 0
    for old_queue_name in old_queue_names:
        if old_queue_name in current_queue_names:
            amount_of_same_songs += 1
    if amount_of_same_songs > 9:
        return True
    else:
        return False


def song_from_queue(old_queue_names, current_song_name):
    if current_song_name in old_queue_names:
        return True
    else:
        return False


def add_skip(song_name):
    skiplist.append(song_name)


def remove_skip(song_name):
    if song_name in skiplist:
        skiplist.remove(song_name)


def add_preliminary_skip(song_name):
    if song_name not in preliminary_skiplist:
        preliminary_skiplist.append(song_name)


def remove_preliminary_skip(song_name):
    if song_name in preliminary_skiplist:
        preliminary_skiplist.remove(song_name)

def convert_to_skiplist():
    for song_name in preliminary_skiplist:
        skiplist.append(song_name)
        preliminary_skiplist.remove(song_name)

def resuming():
    try:
        if sp.current_playback()["actions"]["disallows"]["skipping_prev"]:
            return False
    except Exception:
        pass
    return True
def clear_preliminary_skiplist():
    for song_name in preliminary_skiplist:
        remove_preliminary_skip(song_name)

def check_album():

    for album_name in sp.queue()["queue"]:
        if album_name["album"]["name"]!=sp.current_playback()["item"]["album"]["name"]:
            return False
    return True




def check_skip(
        current_song_progress,
        current_song_name,
        song_duration,
        song_changed,


):

    if not check_album() :
        if song_changed:
            convert_to_skiplist()
            if song_from_queue(old_queue_names, current_song_name) and resuming():
                i=0
                while old_queue_names[i] != current_song_name:
                    add_skip(old_queue_names[i])
                    i+=1
        if current_song_progress > (song_duration * 0.7):
            remove_preliminary_skip(current_song_name)
        else:
            add_preliminary_skip(current_song_name)


def check_in_queue(old_queue_names, current_queue_names):

    if check_same_queue(old_queue_names, current_queue_names):
        for i in range(len(current_queue_names)):
            if current_queue_names[i] not in old_queue_names and i < 10:
                addlist.append(current_queue_names[i])




def get_timestamp_current():
    return sp.current_playback()["timestamp"]


def get_finished():
    return sp.current_playback()["timestamp"] + sp.current_playback()["item"]["duration_ms"]


def check_put_on(old_queue_names, current_queue_names, current_song_name):
    if not check_same_queue(old_queue_names,
                            current_queue_names) and current_song_name not in old_queue_names and song_changed:
        put_on.append(current_song_name)


skiplist = []
preliminary_skiplist = []
addlist = []
put_on = []

old_queue_names = []
song_before=""
last_song_name = ""
old_recently_played_names = []
count = 0
song_changed = False



while True:
    if(sp.current_playback()== None):
        sleep(5)
    else:
        #get info current state
        current_queue_names = get_queue_names()
        current_song_name = sp.current_playback()["item"]["name"]
        current_recently_played_names = get_recently_played_names()

        if last_song_name != current_song_name:
            song_changed = True
        else:
            song_changed = False

        #check for skips and such
        check_skip(
            sp.current_playback()["progress_ms"],
            current_song_name,
            sp.current_playback()["item"]["duration_ms"],
            song_changed,
        )
        # if song_before == "":
        #     song_before = current_song_name
        # elif song_changed:
        #     song_before =last_song_name

        check_put_on(old_queue_names, current_queue_names, current_song_name)
        check_in_queue(old_queue_names, current_queue_names)

        old_queue_names = current_queue_names
        last_song_name = current_song_name
        old_recently_played_names = current_recently_played_names

        print("skiplist")
        print(skiplist)
        print("addlist:")
        print(addlist)
        print("put on:")
        print(put_on)
        print("-----------------------------------------------")

        lists_to_database(skiplist, addlist, put_on)
        skiplist = []
        addlist = []
        put_on = []

        row = c.fetchall()
        print(row)
        with conn:
            c.execute(f"SELECT * FROM tracks")
            rows = c.fetchall()
        for row in rows:
                print(row)  # Each row is a tuple containing column values
        sleep(5)