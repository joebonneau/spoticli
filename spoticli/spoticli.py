import random
import os

import spotipy as sp
from spotipy.oauth2 import SpotifyOAuth
import click
from click.termui import style
from tabulate import tabulate
from pprint import pprint

from spoticli.util import convert_duration, get_current_playback


SPOTIFY_USER_ID = os.environ.get("SPOTIFY_USER_ID")
SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.environ.get("SPOTIFY_REDIRECT_URI")

states = [
    "user-modify-playback-state",
    "user-read-playback-state",
    "user-library-read",
    "playlist-read-private",
    "playlist-read-collaborative",
    "playlist-modify-public",
    "playlist-modify-private",
    "user-read-recently-played",
]

STATE_STR = " ".join(states)


@click.group()
@click.pass_context
def main(
    ctx,
    scope: str = STATE_STR,
    client_id: str = SPOTIFY_CLIENT_ID,
    client_secret: str = SPOTIFY_CLIENT_SECRET,
    redirect_uri: str = SPOTIFY_REDIRECT_URI,
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

        ctx.obj = auth
    except:
        click.secho(
            "API authorization failed! Did you remember to set the environment variables?",
            fg="red",
        )


@main.command("prsa")
@click.pass_obj
def play_random_saved_album(ctx):

    # Only 50 albums can be retrieved at a time, so make as many requests as necessary to retrieve
    # all in library.
    sp_auth = ctx
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
            tracks_res = sp_auth.album_tracks(
                saved_albums[rand_i]["album_uri"], limit=50
            )
            tracks = tracks_res["items"]
            for i in range(len(tracks)):
                sp_auth.add_to_queue(tracks_res["items"][i]["uri"])
            break
        else:
            sp_auth.start_playback(context_uri=saved_albums[rand_i]["album_uri"])
            break


@main.command("actp")
@click.pass_obj
def add_current_track_to_playlists(ctx):

    sp_auth = ctx

    try:
        playback = get_current_playback(display=True)

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
                indices_int = list(map(int, indices.split(",")))

                for index in indices_int:
                    sp_auth.user_playlist_add_tracks(
                        user=SPOTIFY_USER_ID,
                        playlist_id=playlist_dict["playlist_ids"][index],
                        tracks=[playback["track_uri"]],
                    )

                click.secho(
                    f"The track was successfully added to all specified playlists!"
                )
                break
            except ValueError:
                click.secho(f"Invalid input! Try again.", fg="red")
            # except:
            #     click.secho(
            #         f"There was an issue adding the track to all specified playlists."
            #     )
    except TypeError:
        click.secho("Nothing is currently playing!", fg="red")


@main.command("prev")
@click.pass_obj
def previous_track(ctx):
    sp_auth = ctx
    sp_auth.previous_track()

    get_current_playback(sp_auth=sp_auth, display=True)


@main.command("next")
@click.pass_obj
def next_track(ctx):
    sp_auth = ctx
    sp_auth.next_track()

    get_current_playback(sp_auth=sp_auth, display=True)


@main.command("pause")
@click.pass_obj
def pause_playback(ctx):
    sp_auth = ctx
    sp_auth.pause_playback()

    click.secho("Playback paused.")


@main.command("play")
def start_playback(ctx):
    sp_auth = ctx
    sp_auth.start_playback()

    click.secho("Playback resumed.")
    get_current_playback(sp_auth=sp_auth, display=True)


@main.command("vol")
@click.option("-u/-d", "--up/--down", required=True)
@click.pass_obj
def volume(ctx, up):

    sp_auth = ctx
    playback_info = get_current_playback(sp_auth=sp_auth, display=False)

    if up:
        previous_volume = playback_info["volume"]
        new_volume = int(round(previous_volume + 10, 0))
    else:
        previous_volume = playback_info["volume"]
        new_volume = int(round(previous_volume - 10, 0))

    if new_volume > 100:
        new_volume = 100
    elif new_volume < 0:
        new_volume = 0

    sp_auth.volume(new_volume)

    click.secho(f"Current volume: {new_volume}")


@main.command("np")
@click.option("-v", "--verbose", is_flag=True)
@click.pass_obj
def now_playing(ctx, verbose):

    sp_auth = ctx
    playback = get_current_playback(sp_auth=sp_auth, display=True)

    if verbose:
        audio_features = sp_auth.audio_features(playback["track_uri"])
        click.secho(style("Estimates:", underline=True))
        click.echo(f"BPM: {audio_features[0]['tempo']}")
        click.echo(f"Time signature: 4/{audio_features[0]['time_signature']}")


@main.command("shuffle")
@click.option("-on/-off", default=True)
@click.pass_obj
def toggle_shuffle(ctx, on):

    sp_auth = ctx

    if on:
        sp_auth.shuffle(state=True)
        click.echo(f"Shuffle toggled {style('on', fg='green')}.")

    else:
        sp_auth.shuffle(state=False)
        click.echo(f"Shuffle toggled {style('off', fg='red')}.")


@main.command("rp")
@click.pass_obj
def recently_played(ctx):

    sp_auth = ctx
    recent_playback = sp_auth.current_user_recently_played(limit=25)

    # click.echo(f"{pprint(recent_playback['items'][0]['track'])}")


# TODO: recently_played, smart searching
