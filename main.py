from time import sleep
import spotify_listener

listener = spotify_listener.SpotifyListener()
while True:

    listener.update_current_playback()
    if listener.current_playback is None:
        sleep(5)
    else:
        # get info current state
        listener.update_current_queue_ids()
        current_song_id = listener.current_playback["item"]["id"]
        listener.update_song_changed()

        # check for skips and such
        listener.check_skip()
        listener.check_put_on()
        listener.check_in_queue()

        # update current state
        listener.update_old_queue_ids()
        listener.update_last_song_id()

        # convert to database
        listener.write_to_database()
    sleep(5)
