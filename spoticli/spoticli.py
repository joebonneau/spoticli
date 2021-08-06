import random

import spotipy as sp
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
import click


@click.command()
@click.option("--clientid", "-ci", required=True, type=str, envvar="SPOTIFY_CLIENT_ID")
@click.option(
    "--clientsecret", "-cs", required=True, type=str, envvar="SPOTIFY_CLIENT_SECRET"
)
@click.option(
    "--redirecturl", "-rd", required=True, type=str, envvar="SPOTIFY_REDIRECT_URI"
)
@click.pass_context
def connect(ctx, client_id, client_secret, redirect_uri):
    ctx.obj = sp.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            open_browser=False,
        )
    )


@click.command()
@click.pass_obj
def play_random_saved_album(sp_auth, queue):

    # Only 50 albums can be retrieved at a time, so make as many requests as necessary to retrieve
    # all in library.
    saved_albums = []
    offset = 0
    while True:
        albums_res = sp_auth.current_user_saved_albums(limit=50, offset=offset)
        albums = albums_res["items"]
        for i in range(len(albums)):
            saved_albums.append(
                (
                    albums_res["items"][i]["album"]["artists"],
                    albums_res["items"][i]["album"]["uri"],
                )
            )
        if len(albums) < 50:
            break
        else:
            offset += 50

    # Pick a random index that corresponds to an album URI
    rand_i = random.randint(0, len(saved_albums))
    selected_album_artist, selected_album = saved_albums[rand_i]

    # If the queue flag was specified, add all tracks from the album to the queue.
    # Otherwise, play the album.
    click.echo(f"Selected album: {selected_album} by {selected_album_artist}.")

    while True:
        new_album = click.prompt("Select a different random album? (y/n)")
        if new_album.lower() not in ["y", "n"]:
            click.secho("Invalid input!", fg="red")
        elif new_album.lower() == "y":
            # Pick a random index that corresponds to an album URI
            rand_i = random.randint(0, len(saved_albums))
            selected_album_artist, selected_album = saved_albums[rand_i]
        elif new_album.lower() == "n":
            break

    while True:
        queue = click.prompt("Play album now (p) or add to queue (q)?")
        if queue.lower() not in ["p", "q"]:
            click.secho("Invalid input!", fg="red")
        elif queue.lower() == "q":
            tracks_res = sp_auth.album_tracks(selected_album, limit=50)
            tracks = tracks_res["items"]

            for i in range(len(tracks)):
                sp_auth.add_to_queue(tracks_res["items"][i]["uri"])

            break
        else:
            sp_auth.start_playback(selected_album)
            break
