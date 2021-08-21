import json
import os
import random
from time import sleep
from typing import Optional

import click
import spotipy as sp
from click.termui import style
from click.types import Choice
from spotipy.cache_handler import MemoryCacheHandler
from spotipy.client import SpotifyException
from spotipy.oauth2 import SpotifyOAuth, SpotifyOauthError
from tabulate import tabulate

from spoticli.types import CommaSeparatedIndexRange, CommaSeparatedIndices
from spoticli.util import (
    add_album_to_queue,
    convert_datetime,
    convert_timestamp,
    get_artist_names,
    get_current_playback,
    search_parse,
    search_proceed,
)

SPOTIFY_USER_ID = os.environ.get("SPOTIFY_USER_ID")
SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.environ.get("SPOTIFY_REDIRECT_URI")
SPOTIFY_DEVICE_ID = os.environ.get("SPOTIFY_DEVICE_ID")
CACHED_TOKEN_INFO = os.environ.get("CACHED_TOKEN_INFO")

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

device_error_message = " Try pressing play on the device that you want to control."


@click.group()
@click.pass_context
def main(
    ctx,
    scope: Optional[str] = STATE_STR,
    client_id: Optional[str] = SPOTIFY_CLIENT_ID,
    client_secret: Optional[str] = SPOTIFY_CLIENT_SECRET,
    redirect_uri: Optional[str] = SPOTIFY_REDIRECT_URI,
):

    try:
        if CACHED_TOKEN_INFO:
            token_info = json.loads(CACHED_TOKEN_INFO)
            auth = sp.Spotify(
                auth_manager=SpotifyOAuth(
                    scope=scope,
                    client_id=client_id,
                    client_secret=client_secret,
                    redirect_uri=redirect_uri,
                    cache_handler=MemoryCacheHandler(token_info=token_info),
                )
            )
        else:
            if CACHED_TOKEN_INFO:
                auth = sp.Spotify(
                    auth_manager=SpotifyOAuth(
                        scope=scope,
                        client_id=client_id,
                        client_secret=client_secret,
                        redirect_uri=redirect_uri,
                    )
                )

        ctx.obj = auth
    except (SpotifyException, SpotifyOauthError) as e:
        # Spotipy uses SPOTIPY in its environment variables which might be confusing for user.
        message = str(e).replace("SPOTIPY", "SPOTIFY")
        click.secho(
            f"API authorization failed!\nError: {message}",
            fg="red",
        )


@main.command("prev")
@click.option("--device", envvar="SPOTIFY_DEVICE_ID")
@click.pass_obj
def previous_track(ctx, device):
    """
    Skips playback to the track played previous to the current track.
    """
    sp_auth = ctx

    try:
        sp_auth.previous_track(device_id=device)
        # delay to prevent fetching current playback before it updates on server side.
        sleep(0.1)
        current_playback = sp_auth.current_playback()
        get_current_playback(res=current_playback, display=True)
    except AttributeError:
        # AttributeError is thrown if authorization was unsuccessful, so show that error instead.
        pass
    except SpotifyException as e:
        click.secho(str(e), fg="red")


@main.command("next")
@click.option("--device", envvar="SPOTIFY_DEVICE_ID")
@click.pass_obj
def next_track(ctx, device):
    """
    Skips playback to the next track in the queue.
    """
    sp_auth = ctx

    try:
        sp_auth.next_track(device_id=device)
        # delay to prevent fetching current playback before it updates on server side.
        sleep(0.1)
        current_playback = sp_auth.current_playback()
        get_current_playback(res=current_playback, display=True)
    except AttributeError:
        # AttributeError is thrown if authorization was unsuccessful, so show that error instead.
        pass
    except SpotifyException as e:
        click.secho(str(e), fg="red")


@main.command("pause")
@click.option("--device", envvar="SPOTIFY_DEVICE_ID")
@click.pass_obj
def pause_playback(ctx, device):
    """
    Pauses playback.
    """
    sp_auth = ctx

    try:
        sp_auth.pause_playback(device_id=device)

        click.secho("Playback paused.")
    except AttributeError:
        # AttributeError is thrown if authorization was unsuccessful, so show that error instead.
        pass
    except SpotifyException as e:
        click.secho(str(e), fg="red")


@main.command("play")
@click.option("--device", envvar="SPOTIFY_DEVICE_ID")
@click.pass_obj
def start_playback(ctx, device):
    """
    Resumes playback on the active track.
    """
    sp_auth = ctx

    try:
        sp_auth.start_playback(device_id=device)

        click.secho("Playback resumed.")
        current_playback = sp_auth.current_playback()
        get_current_playback(res=current_playback, display=True)
    except AttributeError:
        # AttributeError is thrown if authorization was unsuccessful, so show that error instead.
        pass
    except SpotifyException as e:
        click.secho(str(e), fg="red")


@main.command("cp")
@click.option("-pub/-pri", default=True, help="public or private")
@click.option(
    "-c/-i",
    default=False,
    help="collaborative or non-collaborative",
)
@click.option("-d", type=str, default="", help="playlist description")
@click.argument("name", required=True)
@click.pass_obj
def create_playlist(ctx, pub, c, d, name):
    """
    Creates a new playlist.
    """

    sp_auth = ctx

    if all((pub, c)):
        click.secho(style("Collaborative playlists can only be private.", fg="red"))
    else:
        try:
            sp_auth.user_playlist_create(
                user=SPOTIFY_USER_ID,
                name=name,
                public=pub,
                collaborative=c,
                description=d,
            )

            click.secho(style(f"Playlist '{name}' created successfully!", fg="green"))
        except AttributeError:
            # AttributeError is thrown if authorization was unsuccessful, so show that error instead.
            pass
        except SpotifyException as e:
            click.secho(str(e), fg="red")


@main.command("seek")
@click.option("--device", envvar="SPOTIFY_DEVICE_ID")
@click.argument("timestamp", required=True)
@click.pass_obj
def seek(ctx, timestamp, device):
    """
    Seeks the track to the timestamp specified.

    TIMESTAMP format is MM:SS
    """

    sp_auth = ctx

    try:
        timestamp_in_ms = convert_timestamp(timestamp)
        sp_auth.seek_track(timestamp_in_ms, device_id=device)
    except AttributeError:
        # AttributeError is thrown if authorization was unsuccessful, so show that error instead.
        pass
    except SpotifyException as e:
        click.secho(str(e), fg="red")
    except ValueError:
        click.secho(
            style("Incorrect format: must be in minutes:seconds format", fg="red")
        )


@main.command("volup")
@click.option("--device", envvar="SPOTIFY_DEVICE_ID")
@click.argument("amount", default=10)
@click.pass_obj
def increase_volume(ctx, amount, device):
    """
    Increases volume by the increment specified (defaults to 10%).
    """

    sp_auth = ctx

    try:
        current_playback = sp_auth.current_playback()
        playback_info = get_current_playback(res=current_playback, display=False)
        previous_volume = playback_info["volume"]

        new_volume = int(round(previous_volume + amount, 0))
        if new_volume > 100:
            new_volume = 100

        sp_auth.volume(new_volume, device_id=device)
        click.secho(f"New volume: {new_volume}")
    except AttributeError:
        # AttributeError is thrown if authorization was unsuccessful, so show that error instead.
        pass
    except SpotifyException as e:
        click.secho(str(e), fg="red")


@main.command("voldown")
@click.option("--device", envvar="SPOTIFY_DEVICE_ID")
@click.argument("amount", default=10)
@click.pass_obj
def decrease_volume(ctx, amount, device):
    """
    Decreases volume by the increment specified (defaults to 10%).
    """

    sp_auth = ctx

    try:
        current_playback = sp_auth.current_playback()
        playback_info = get_current_playback(res=current_playback, display=False)
        previous_volume = playback_info["volume"]

        new_volume = int(round(previous_volume - amount, 0))
        if new_volume < 0:
            new_volume = 0

        sp_auth.volume(new_volume, device_id=device)
        click.secho(f"New volume: {new_volume}")
    except AttributeError:
        # AttributeError is thrown if authorization was unsuccessful, so show that error instead.
        pass
    except SpotifyException as e:
        click.secho(str(e), fg="red")


@main.command("now")
@click.option("-v", "--verbose", is_flag=True, help="displays additional info")
@click.pass_obj
def now_playing(ctx, verbose):
    """
    Displays info about the current playback.
    """

    sp_auth = ctx

    try:
        current_playback = sp_auth.current_playback()
        playback = get_current_playback(res=current_playback, display=True)

        if verbose:
            audio_features = sp_auth.audio_features(playback["track_uri"])
            click.secho(style("Estimates:", underline=True))
            click.echo(f"BPM: {audio_features[0]['tempo']}")
            click.echo(f"Time signature: 4/{audio_features[0]['time_signature']}")
    except AttributeError:
        # AttributeError is thrown if authorization was unsuccessful, so show that error instead.
        pass
    except SpotifyException as e:
        click.secho(str(e), fg="red")


@main.command("shuffle")
@click.option("--device", envvar="SPOTIFY_DEVICE_ID")
@click.option("-on/-off", required=True, is_flag=True)
@click.pass_obj
def toggle_shuffle(ctx, on, device):
    """
    Toggles shuffling on or off.
    """

    sp_auth = ctx

    try:
        if on:
            sp_auth.shuffle(state=True, device_id=device)
            click.echo(f"Shuffle toggled {style('on', fg='green')}.")

        else:
            sp_auth.shuffle(state=False, device_id=device)
            click.echo(f"Shuffle toggled {style('off', fg='red')}.")
    except AttributeError:
        # AttributeError is thrown if authorization was unsuccessful, so show that error instead.
        pass
    except SpotifyException as e:
        click.secho(str(e), fg="red")


@main.command("rsa")
@click.option("--device", envvar="SPOTIFY_DEVICE_ID")
@click.pass_obj
def get_random_saved_album(ctx, device):
    """
    Fetches all albums in user library and selects one randomly.
    """

    # Only 50 albums can be retrieved at a time, so make as many requests as necessary to retrieve
    # all in library.
    sp_auth = ctx

    try:
        saved_albums = []
        offset = 0
        while True:
            albums_res = sp_auth.current_user_saved_albums(limit=50, offset=offset)
            if offset == 0:
                click.secho(
                    "Retrieving saved albums. This may take a few moments...",
                    fg="magenta",
                )
            albums = albums_res["items"]
            for album in albums:
                saved_albums.append(
                    {
                        "album_uri": album["album"]["uri"],
                        "artists": get_artist_names(album["album"]),
                        "album": album["album"]["name"],
                    }
                )
            if len(albums) < 50:
                break
            else:
                offset += 50

        # Pick a random index that corresponds to an album URI
        rand_i = random.randint(0, len(saved_albums))

        while True:
            album = saved_albums[rand_i]["album"]
            artists = saved_albums[rand_i]["artists"]
            click.echo(
                f"Selected album: {style(album, fg='blue')} by {style(artists, fg='green')}."
            )
            new_album = click.prompt(
                "Select this album?",
                type=Choice(("y", "n"), case_sensitive=False),
                show_choices=True,
            )
            if new_album == "n":
                # Pick a random index that corresponds to an album URI
                rand_i = random.randint(0, len(saved_albums))
            else:
                break

        while True:
            queue = click.prompt(
                "Play album now or add to queue?",
                type=Choice(("p", "q"), case_sensitive=False),
                show_choices=True,
            )
            if queue == "q":
                add_album_to_queue(sp_auth, saved_albums[rand_i]["album_uri"])
                break
            else:
                sp_auth.start_playback(
                    context_uri=saved_albums[rand_i]["album_uri"], device_id=device
                )
                sleep(0.5)
                current_playback = sp_auth.current_playback()
                get_current_playback(res=current_playback, display=True)
                break
    except AttributeError:
        # AttributeError is thrown if authorization was unsuccessful, so show that error instead.
        pass
    except SpotifyException as e:
        click.secho(str(e), fg="red")


@main.command("actp")
@click.pass_obj
def add_current_track_to_playlists(ctx):
    """
    Adds the current track in playback to one or more playlist(s).
    """

    sp_auth = ctx

    try:
        current_playback = sp_auth.current_playback()
        playback = get_current_playback(res=current_playback, display=True)

        playlist_res = sp_auth.current_user_playlists(limit=20)
        positions = []
        playlist_names = []
        playlist_ids = []
        playlist_items = playlist_res["items"]
        for i, item in enumerate(playlist_items):
            positions.append(i)
            playlist_names.append(item["name"])
            playlist_ids.append(item["uri"])

        playlist_dict = {
            "index": positions,
            "playlist_names": playlist_names,
            "playlist_ids": playlist_ids,
        }
        display_dict = {"index": positions, "playlist_names": playlist_names}
        click.echo(tabulate(display_dict, headers="keys", tablefmt="github"))

        indices = click.prompt(
            "Enter the indices of the playlists to add the track to separated by commas.",
            type=CommaSeparatedIndices([str(i) for i in positions]),
            show_choices=False,
        )

        for index in indices:
            sp_auth.playlist_add_items(
                playlist_id=playlist_dict["playlist_ids"][index],
                items=[playback["track_uri"]],
            )

        click.secho(
            "The track was successfully added to all specified playlists!", fg="green"
        )
    # except TypeError:
    #     click.secho("Nothing is currently playing!", fg="red")
    except AttributeError:
        # AttributeError is thrown if authorization was unsuccessful, so show that error instead.
        pass
    except SpotifyException as e:
        click.secho(str(e), fg="red")


@main.command("recent")
@click.option("--device", envvar="SPOTIFY_DEVICE_ID")
@click.option("-a", "--after", default=None, help="YYYYMMDD MM:SS")
@click.pass_obj
def recently_played(ctx, after, device):
    """
    Displays information about recently played tracks.
    """

    sp_auth = ctx

    try:
        if after:
            recent_playback = sp_auth.current_user_recently_played(
                limit=25, after=convert_datetime(after)
            )
        else:
            recent_playback = sp_auth.current_user_recently_played(limit=25)

        positions = []
        track_names = []
        track_uris = []
        album_names = []
        album_uris = []
        album_types = []
        timestamps = []
        playback_items = recent_playback["items"]
        for i, item in enumerate(playback_items):
            positions.append(i)
            track_names.append(item["track"]["name"])
            track_uris.append(item["track"]["uri"])
            album_names.append(item["track"]["album"]["name"])
            album_uris.append(item["track"]["album"]["uri"])
            album_types.append(item["track"]["album"]["album_type"])
            timestamps.append(item["played_at"])

        recent_dict = {
            "index": positions,
            "track_name": track_names,
            "track_uri": track_uris,
            "album_name": album_names,
            "album_uri": album_uris,
            "album_type": album_types,
            "timestamp": timestamps,
        }
        display_dict = dict(
            (k, recent_dict[k])
            for k in ("index", "track_name", "album_type", "album_name", "timestamp")
        )
        click.echo(tabulate(display_dict, headers="keys", tablefmt="github"))

        action = click.prompt(
            "Take further action?",
            type=Choice(("y", "n"), case_sensitive=False),
            show_choices=True,
        )
        if action == "y":
            task = click.prompt(
                "Play now, add to queue, or create playlist?",
                type=Choice(("p", "q", "cp"), case_sensitive=False),
                show_choices=True,
            )
            if task == "cp":
                indices = click.prompt(
                    "Enter the indices of the tracks to add to the playlist separated by commas",
                    type=CommaSeparatedIndexRange([str(i) for i in positions]),
                    show_choices=False,
                )
                playlist_name = click.prompt("Enter the playlist name")
                sp_auth.user_playlist_create(user=SPOTIFY_USER_ID, name=playlist_name)
                playlist_res = sp_auth.current_user_playlists(limit=1)
                playlist_uri = playlist_res["items"][0]["uri"]
                sp_auth.playlist_add_items(
                    playlist_uri,
                    track_uris[indices[0] : indices[1] + 1],
                )
                click.secho(
                    f"Playlist '{playlist_name}' created successfully!",
                    fg="green",
                )
            else:
                index = click.prompt(
                    "Enter the index of interest",
                    type=Choice([str(i) for i in positions]),
                    show_choices=False,
                )
                index = int(index)
                item_type = click.prompt(
                    "Track or associated album?",
                    type=Choice(("t", "a"), case_sensitive=False),
                    show_choices=True,
                )
                if task == "q":
                    if item_type == "t":
                        sp_auth.add_to_queue(
                            recent_dict["track_uri"][i], device_id=device
                        )
                        click.secho(
                            "Track successfully added to the queue.", fg="green"
                        )
                    else:
                        add_album_to_queue(sp_auth, recent_dict["album_uri"][index])

                else:
                    if item_type == "t":
                        sp_auth.start_playback(
                            uris=[recent_dict["track_uri"][index]], device_id=device
                        )
                    else:
                        sp_auth.start_playback(
                            context_uri=recent_dict["album_uri"][index],
                            device_id=device,
                        )
                    sleep(0.5)
                    current_playback = sp_auth.current_playback()
                    get_current_playback(res=current_playback, display=True)
    except ValueError:
        click.secho("Invalid format. Proper format is 'YYYYMMDD MM:SS", fg="red")
    except AttributeError:
        # AttributeError is thrown if authorization was unsuccessful, so show that error instead.
        pass
    except SpotifyException as e:
        click.secho(str(e), fg="red")


@main.command("search")
@click.option("--device", envvar="SPOTIFY_DEVICE_ID")
@click.option(
    "-t",
    "type_",
    type=click.Choice(("album", "artist", "playlist", "track")),
    required=True,
)
@click.argument("term", required=True)
@click.pass_obj
def search(ctx, term, type_, device):
    """
    Queries Spotify's databases.
    """
    sp_auth = ctx

    k = type_ + "s"
    try:
        search_res = sp_auth.search(q=term, limit=10, type=type_, device=device)
        results, uris = search_parse(search_res, k)
        search_proceed(sp_auth, type_, results, uris)
    except AttributeError:
        pass
    except SpotifyException as e:
        click.secho(str(e), fg="red")
