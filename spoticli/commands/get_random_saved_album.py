import random

import click
from click import style
from spotipy.client import Spotify

from spoticli.lib.util import (
    Y_N_CHOICE_CASE_INSENSITIVE,
    add_album_to_queue,
    get_artist_names,
    play_or_queue,
    truncate,
    wait_display_playback,
)


def get_random_saved_album(sp_auth: Spotify, device: str):
    """
    Fetches all albums in user library and selects one randomly.
    """

    saved_albums = _get_saved_albums(sp_auth)

    # Pick a random index that corresponds to an album URI
    initial_i = random.randint(0, len(saved_albums))
    selected_i = _select_album(saved_albums, initial_i)

    queue = play_or_queue()
    if queue == "q":
        add_album_to_queue(sp_auth, saved_albums[selected_i]["album_uri"])
    else:
        sp_auth.start_playback(
            context_uri=saved_albums[selected_i]["album_uri"], device_id=device
        )
        wait_display_playback(sp_auth)


def _select_album(saved_albums, rand_i):
    while True:
        album = saved_albums[rand_i]["album"]
        artists = truncate(saved_albums[rand_i]["artists"])
        click.echo(
            f"Selected album: {style(album, fg='blue')} by {style(artists, fg='green')}."
        )
        new_album = click.prompt(
            "Select this album?",
            type=Y_N_CHOICE_CASE_INSENSITIVE,
            show_choices=True,
        )
        if new_album == "n":
            # Pick a random index that corresponds to an album URI
            rand_i = random.randint(0, len(saved_albums))
        else:
            break
    return rand_i


def _get_saved_albums(sp_auth):
    saved_albums = []
    offset = 0
    # Only 50 albums can be retrieved at a time, so make as many requests as
    # necessary to retrieve all in library.
    while True:
        albums_res = sp_auth.current_user_saved_albums(limit=50, offset=offset)
        if offset == 0:
            click.secho(
                "Retrieving saved albums. This may take a few moments...",
                fg="magenta",
            )
        albums = albums_res["items"]
        saved_albums.extend(
            {
                "album_uri": album["album"]["uri"],
                "artists": get_artist_names(album["album"]),
                "album": album["album"]["name"],
            }
            for album in albums
        )
        if len(albums) < 50:
            break
        else:
            offset += 50
    return saved_albums
