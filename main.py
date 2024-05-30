from time import sleep

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from pprint import pprint
import sys
import argparse
import logging

scope = "user-top-read,user-read-playback-state,user-modify-playback-state,playlist-modify-private,playlist-modify-public,user-read-recently-played,user-library-read,user-library-modify"
ranges = ["short_term", "medium_term", "long_term"]

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))
# results = sp.current_user_top_tracks(time_range='long_term', limit=1)
# sp.playlist_add_items("5qrpGq0FT0SZAtjt0aIMNl", ten_top)
# ten_top = [song["id"] for song in results["items"]]

username = "dfd0430"
# playlists = sp.user_playlists(username)
# for playlist in playlists['items']:
#   print(playlist['name'])
skiplist = []
preliminary_skiplist=[]
addlist = []
put_on= []
def get_recently_played_names():
    recentlyplayed = sp.current_user_recently_played(limit=5)
    recentlyplayed_names = [songs["track"]["name"] for songs in recentlyplayed["items"]]
    return recentlyplayed_names


def get_queue_names():
    current_queue = sp.queue()
    if current_queue is None:
        current_queue = []

    current_queue_names = [songs["name"] for songs in current_queue["queue"]]
    return current_queue_names


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

def add_preliminary_skip(song_name):
    preliminary_skiplist.append(song_name)
def check_skip(
    old_queue_names,
    current_queue_names,
    current_song_name,
    last_song_name,
    old_recently_played_names,
    current_recently_played_names,

):
    if current_song_name == last_song_name:
        x = 1
    else:
        if check_same_queue(old_queue_names, current_queue_names) and song_from_queue(
            old_queue_names, current_song_name
        ):
            i = 0
            while old_queue_names[i] != current_song_name:
                add_skip(old_queue_names[i])
                i += 1
            if last_song_name not in current_recently_played_names and last_song_name!="":
                add_preliminary_skip(last_song_name)

        else:
            if last_song_name not in current_recently_played_names and last_song_name!="":
                add_preliminary_skip(last_song_name)

def check_in_queue(old_queue_names, current_queue_names):

    if check_same_queue(old_queue_names, current_queue_names):
        for i in range(len(current_queue_names)):
            if current_queue_names[i] not in old_queue_names and current_queue_names[i] not in addlist and i<10:
                addlist.append(current_queue_names[i])
def check(current_recently_played_names,most_recent_song):

  for songs in preliminary_skiplist:
      if songs in current_recently_played_names[:5]:
          preliminary_skiplist.remove(songs)
      elif most_recent_song!=current_recently_played_names[0] and most_recent_song not in preliminary_skiplist:
          skiplist.append(preliminary_skiplist[0])
          preliminary_skiplist.remove(songs)

  return current_recently_played_names[0]


def check_put_on(old_queue_names, current_queue_names,current_song_name):
    if not check_same_queue(old_queue_names, current_queue_names) and current_song_name not in old_queue_names and current_song_name not in put_on:
        put_on.append(current_song_name)


old_queue_names=[]
last_song_name=""
old_recently_played_names=[]
count=0
most_recent_song=""
while True:
    current_queue_names=get_queue_names()
    current_song_name=sp.current_playback()["item"]["name"]
    current_recently_played_names=get_recently_played_names()

    check_skip(
        old_queue_names,
        current_queue_names,
        current_song_name,
        last_song_name,
        old_recently_played_names,
        current_recently_played_names,

    )
    # print("current[0]:")
    # print(current_recently_played_names[0])
    print("skiplist:")
    print(skiplist)
    # print("preliminary skiplist:")
    # print(preliminary_skiplist)
    # print("current song "+current_song_name)
    print("current")
    print(current_queue_names)
    print("old")
    print(old_queue_names)
    print("addlist:")
    print(addlist)
    print("put on:")
    print(put_on)

    print(count)
    count+=1
    check_put_on(old_queue_names, current_queue_names, current_song_name)
    check_in_queue(old_queue_names, current_queue_names)
    old_queue_names=current_queue_names
    last_song_name=current_song_name
    old_recently_played_names=current_recently_played_names

    x=check(current_recently_played_names,most_recent_song)
    most_recent_song=x
    sleep(5)