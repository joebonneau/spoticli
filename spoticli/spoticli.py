import random
import os

import spotipy as sp
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
import click
from click import style


SCOPE = " user-read-playback-state"
SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.environ.get("SPOTIFY_REDIRECT_URI")


def connect(
    scope,
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=SPOTIFY_REDIRECT_URI,
):
    try:
        auth = sp.Spotify(
            auth_manager=SpotifyOAuth(
                scope=scope,
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
            )
        )
    except:
        click.secho(
            "API authorization failed! Did you set the environment variables?", fg="red"
        )

    return auth


@click.group()
def main():
    pass


# @main.command()
# @click.option(
#     "--clientid",
#     "-ci",
#     "client_id",
#     required=True,
#     type=str,
#     envvar="SPOTIFY_CLIENT_ID",
# )
# @click.option(
#     "--clientsecret",
#     "-cs",
#     "client_secret",
#     required=True,
#     type=str,
#     envvar="SPOTIFY_CLIENT_SECRET",
# )
# @click.option(
#     "--redirecturl",
#     "-rd",
#     "redirect_uri",
#     required=True,
#     type=str,
#     envvar="SPOTIFY_REDIRECT_URI",
# )
# def connect(ctx, client_id, client_secret, redirect_uri):
#     try:
#         ctx.obj = sp.Spotify(
#             auth_manager=SpotifyOAuth(
#                 client_id=client_id,
#                 client_secret=client_secret,
#                 redirect_uri=redirect_uri,
#                 open_browser=False,
#                 scope=SCOPE,
#             )
#         )
#         click.secho("API authorization successful!", fg="green")
#     except:
#         click.secho("API authorization failed!", fg="red")


@main.command()
def play_random_saved_album():

    # Only 50 albums can be retrieved at a time, so make as many requests as necessary to retrieve
    # all in library.
    sp_auth = connect(scope="user-library-read user-modify-playback-state")

    click.secho("This might take a few seconds...", fg="yellow")
    saved_albums = []
    offset = 0
    while True:
        albums_res = sp_auth.current_user_saved_albums(limit=50, offset=offset)
        albums = albums_res["items"]
        for i in range(len(albums)):
            artists = []
            for j in range(len(albums_res["items"][i]["album"]["artists"])):
                artists.append(albums_res["items"][i]["album"]["artists"][j]["name"])

            saved_albums.append(
                {
                    "album_uri": albums_res["items"][i]["album"]["uri"],
                    "artists": ", ".join(artists),
                    "album": albums_res["items"][i]["album"]["name"],
                }
            )
        if len(albums) < 50:
            break
        else:
            offset += 50

    # Pick a random index that corresponds to an album URI
    rand_i = random.randint(0, len(saved_albums))

    while True:
        album = saved_albums[rand_i].get("album")
        artists = saved_albums[rand_i].get("artists")
        click.echo(
            f"Selected album: {style(album, fg='blue')} by {style(artists, fg='green')}."
        )
        new_album = click.prompt("Select a different random album? (y/n)")
        if new_album.lower() not in ["y", "n"]:
            click.secho("Invalid input!", fg="red")
        elif new_album.lower() == "y":
            # Pick a random index that corresponds to an album URI
            rand_i = random.randint(0, len(saved_albums))
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
            sp_auth.start_playback(context_uri=saved_albums[rand_i].get("album_uri"))
            break


@main.command()
def add_current_track_to_playlists():

    sp_auth = connect()

    current_playback = sp_auth.current_playback()
    current_track = current_playback["item"]["uri"]
    current_artists = []
    for i in range(len(current_playback["item"]["artists"])):
        current_artists.append(current_playback["item"]["artists"][i]["name"])

    click.echo(
        f"The current track playing is {style(current_track, fg='blue')} by {style(', '.join(current_artists), fg='green')}"
    )
