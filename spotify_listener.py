import sqlite3

import spotipy
from dotenv import load_dotenv
from spotipy import SpotifyOAuth


class SpotifyListener:
    def __init__(self):
        self.skip_list = []
        self.add_list = []
        self.put_on = []
        self.preliminary_skip_list = []
        self.old_queue_ids = []
        self.current_queue_ids = []
        self.song_before = ""
        self.last_song_id = ""
        self.song_changed = False
        self.current_playback = ""

        conn = sqlite3.connect("spotify.db")
        self.cursor = conn.cursor()
        self.conn = conn

        with open("queries/create_table.sql") as query:
            self.cursor.execute(query.read())
        conn.commit()

        load_dotenv()

        scope = "user-top-read,user-read-playback-state,user-modify-playback-state,playlist-modify-private,playlist-modify-public,user-read-recently-played,user-library-read,user-library-modify"
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))
        username = "dfd0430"
        self.sp = sp

    def add_skip(self, song_id):
        self.skip_list.append(song_id)

    def add_preliminary_skip(self, song_id):
        if song_id not in self.preliminary_skip_list:
            self.preliminary_skip_list.append(song_id)

    def remove_preliminary_skip(self, song_id):
        if song_id in self.preliminary_skip_list:
            self.preliminary_skip_list.remove(song_id)

    def convert_to_skip_list(self):
        for song_id in self.preliminary_skip_list:

            self.skip_list.append(song_id)
            self.preliminary_skip_list.remove(song_id)

    def update_current_playback(self):
        self.current_playback = self.sp.current_playback()

    def check_id_exists(self, song_id):
        with open("queries/check_id_exists.sql") as query:
            self.cursor.execute(query.read(), (song_id,))

        return self.cursor.fetchone()[0]

    def song_to_database_skip(self, song_id):
        if self.check_id_exists(song_id):
            with open("queries/times_skipped_read.sql") as query:
                self.cursor.execute(query.read(), (song_id,))
            row = self.cursor.fetchone()
            i = row[0] + 1
            with self.conn:
                with open("queries/times_skipped_update.sql") as query:
                    self.cursor.execute(
                        query.read(),
                        {"song_id": song_id, "times_skipped": i},
                    )
        else:
            with self.conn:
                with open("queries/new_entry.sql") as query:
                    self.cursor.execute(
                        query.read(),
                        {
                            "song_id": song_id,
                            "times_skipped": 1,
                            "times_added": 0,
                            "times_put_on": 0,
                            "song_name": self.sp.track(song_id)["name"],
                        },
                    )

    def song_to_database_add(self, song_id):
        if self.check_id_exists(song_id):
            with open("queries/times_added_read.sql") as query:
                self.cursor.execute(query.read(), (song_id,))
            row = self.cursor.fetchone()
            i = row[0] + 1
            with self.conn:
                with open("queries/times_added_update.sql") as query:
                    self.cursor.execute(
                        query.read(),
                        {"song_id": song_id, "times_added": i},
                    )
        else:
            with self.conn:
                with open("queries/new_entry.sql") as query:
                    self.cursor.execute(
                        query.read(),
                        {
                            "song_id": song_id,
                            "times_skipped": 0,
                            "times_added": 1,
                            "times_put_on": 0,
                            "song_name": self.sp.track(song_id)["name"],
                        },
                    )

    def song_to_database_put(self, song_id):
        if self.check_id_exists(song_id):

            with open("queries/times_put_read.sql") as query:
                self.cursor.execute(query.read(), (song_id,))
            row = self.cursor.fetchone()
            i = row[0] + 1

            with self.conn:
                with open("queries/times_put_update.sql") as query:
                    self.cursor.execute(
                        query.read(),
                        {"song_id": song_id, "times_put_on": i},
                    )
        else:
            with self.conn:
                with open("queries/new_entry.sql") as query:
                    self.cursor.execute(
                        query.read(),
                        {
                            "song_id": song_id,
                            "times_skipped": 0,
                            "times_added": 0,
                            "times_put_on": 1,
                            "song_name": self.sp.track(song_id)["name"],
                        },
                    )

    def lists_to_database(self):
        for song_id in self.skip_list:
            self.song_to_database_skip(song_id)
        for song_id in self.add_list:
            self.song_to_database_add(song_id)
        for song_id in self.put_on:
            self.song_to_database_put(song_id)

    def get_recently_played_ids(self):
        recently_played = self.sp.current_user_recently_played(limit=5)
        recently_played_id = [
            songs["track"]["id"] for songs in recently_played["items"]
        ]
        return recently_played_id

    def update_current_queue_ids(self):
        current_queue = self.sp.queue()
        if current_queue is None:
            current_queue = []
        current_queue_ids = [songs["id"] for songs in current_queue["queue"]]

        self.current_queue_ids = current_queue_ids[:20]

    def update_old_queue_ids(self):
        self.old_queue_ids = self.current_queue_ids

    def update_last_song_id(self):
        self.last_song_id = self.current_playback["item"]["id"]

    # def update_old_recently_played_id(self):
    #     self.old_recently_played_id =

    def check_album(self, current_playback):

        for album_name in self.sp.queue()["queue"]:
            if album_name is not None:
                return False
            if album_name["album"]["name"] != current_playback["item"]["album"]["name"]:
                return False
        return True

    @staticmethod
    def check_same_queue(old_queue_ids, current_queue_ids):
        amount_of_same_songs = 0
        for old_queue_id in old_queue_ids:
            if old_queue_id in current_queue_ids:
                amount_of_same_songs += 1
        return amount_of_same_songs > 9

    @staticmethod
    def song_from_queue(old_queue_ids, current_song_id):
        return current_song_id in old_queue_ids

    def resuming(self):
        try:
            if self.sp.current_playback()["actions"]["disallows"]["skipping_prev"]:
                return False
        except Exception:
            pass
        return True

    def check_skip(self):

        current_song_id = self.current_playback["item"]["id"]
        current_song_progress = self.current_playback["progress_ms"]
        song_duration = self.current_playback["item"]["duration_ms"]
        if not self.check_album(self.current_playback):

            if self.song_changed:
                self.convert_to_skip_list()
                if (
                    self.song_from_queue(self.old_queue_ids, current_song_id)
                    and self.resuming()
                ):
                    i = 0
                    while self.old_queue_ids[i] != current_song_id:
                        self.add_skip(self.old_queue_ids[i])
                        i += 1

            if current_song_progress > (song_duration * 0.7):
                self.remove_preliminary_skip(current_song_id)
            else:
                self.add_preliminary_skip(current_song_id)

    def check_in_queue(self):

        if self.check_same_queue(self.old_queue_ids, self.current_queue_ids):
            for i in range(len(self.current_queue_ids)):
                if self.current_queue_ids[i] not in self.old_queue_ids and i < 10:
                    self.add_list.append(self.current_queue_ids[i])

    def check_put_on(self):
        current_song_id = self.current_playback["item"]["id"]
        if (
            not self.check_same_queue(self.old_queue_ids, self.current_queue_ids)
            and current_song_id not in self.old_queue_ids
            and self.song_changed
        ):
            self.put_on.append(current_song_id)

    def write_to_database(self):
        if (len(self.skip_list) + len(self.put_on) + len(self.add_list)) > 1:
            self.lists_to_database()
            self.skip_list = []
            self.add_list = []
            self.put_on = []

    # def test(self):
    #     with open("queries/test.sql") as query:
    #         self.cursor.execute(query.read())
    #         rows= self.cursor.fetchall()
    #     for row in rows:
    #         print(row)
    #
    # def test2(self):
    #     print(self.skip_list)
    #     # print(self.current_playback["item"]["name"])
    #     # print(self.preliminary_skip_list)
    #     # print(self.song_changed)
    #     # print(self.current_queue_ids)
    #     # print(self.old_queue_ids)

    def update_song_changed(self):
        self.song_changed = self.last_song_id != self.current_playback["item"]["id"]
