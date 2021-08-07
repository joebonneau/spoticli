import random
import os
import time

import spotipy as sp
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
import click
from click import style
from tabulate import tabulate


SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")
SPOTIFY_USER_ID = os.environ.get("SPOTIFY_USER_ID")
SPOTIFY_REDIRECT_URI = os.environ.get("SPOTIFY_REDIRECT_URI")


def convert_duration(duration_ms):

    minutes, seconds = divmod(duration_ms / 1000, 60)
    duration = f"{int(minutes)}:{int(round(seconds,0))}"

    return duration


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
            "API authorization failed! Did you remember to set the environment variables?",
            fg="red",
        )

    return auth


@click.group()
def main():
    pass


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

    sp_auth = connect(
        scope="user-read-playback-state playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private"
    )

    try:
        current_playback = sp_auth.current_playback()
    except TypeError:
        click.secho("Nothing is currently playing!", fg="red")

    current_track = current_playback["item"]["name"]
    current_track_uri = current_playback["item"]["uri"]
    current_artists = []
    for i in range(len(current_playback["item"]["artists"])):
        current_artists.append(current_playback["item"]["artists"][i]["name"])

    click.echo(
        f"The current track playing is {style(current_track, fg='blue')} by {style(', '.join(current_artists), fg='green')}"
    )
    duration = convert_duration(current_playback["item"]["duration_ms"])
    release_date = current_playback["item"]["album"]["release_date"]
    click.echo(f"Duration: {duration}, Released: {release_date}")

    playlist_res = sp_auth.current_user_playlists(limit=20)
    positions = []
    playlist_names = []
    playlist_ids = []
    for i in range(len(playlist_res["items"])):
        positions.append(i)
        playlist_names.append(playlist_res["items"][i]["name"])
        playlist_ids.append(playlist_res["items"][i]["uri"])

    playlist_dict = {
        "index": positions,
        "playlist_names": playlist_names,
        "playlist_ids": playlist_ids,
    }
    display_dict = {"index": positions, "playlist_names": playlist_names}
    click.echo(tabulate(display_dict, headers="keys", tablefmt="github"))

    while True:
        indices = click.prompt(
            "Enter the indices of the playlists to add the track to separated by commas."
        )

        try:
            indices_int = [int(index) for index in indices.split(",")]

            for index in indices_int:
                sp_auth.user_playlist_add_tracks(
                    user=SPOTIFY_USER_ID,
                    playlist_id=playlist_dict.get("playlist_ids")[index],
                    tracks=[current_track_uri],
                )

            click.secho(f"The track was successfully added to all specified playlists!")
            break
        except ValueError:
            click.secho(f"Invalid input! Try again.", fg="red")
        except:
            click.secho(
                f"There was an issue adding the track to all specified playlists."
            )
