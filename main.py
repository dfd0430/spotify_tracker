import spotipy
from spotipy.oauth2 import SpotifyOAuth
from pprint import pprint
import sys
import argparse
import logging

scope = 'user-top-read,user-read-playback-state,user-modify-playback-state,playlist-modify-private,playlist-modify-public'
ranges = ['short_term', 'medium_term', 'long_term']

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))

for sp_range in ['short_term', 'medium_term', 'long_term']:
    print("range:", sp_range)

    results = sp.current_user_top_artists(time_range=sp_range, limit=10)

    for i, item in enumerate(results['items']):
        print(i, item['name'])
    print()

results = sp.current_user_top_tracks(time_range='long_term', limit=10)


pprint(results["items"])

ten_top = [song["id"] for song in results["items"]]

liste = []
for song in results["items"]:
    liste.append(song["id"])

sp.playlist_add_items("5qrpGq0FT0SZAtjt0aIMNl", ten_top)

username ='dfd0430'
playlists = sp.user_playlists(username)
for playlist in playlists['items']:
    print(playlist['name'])


