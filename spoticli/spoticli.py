import json
import os
import random
from configparser import ConfigParser
from configparser import Error as ConfigError
from pathlib import Path
from time import sleep
from typing import Any, Optional

import click
import spotipy as sp
from appdirs import user_config_dir
from click.termui import style
from click.types import Choice
from spotipy.cache_handler import MemoryCacheHandler
from spotipy.client import SpotifyException
from spotipy.oauth2 import SpotifyOAuth, SpotifyOauthError

import spoticli.commands as commands
from spoticli.types import CommaSeparatedIndexRange, CommaSeparatedIndices
from spoticli.util import (
    Y_N_CHOICE_CASE_INSENSITIVE,
    add_album_to_queue,
    check_devices,
    check_url_format,
    convert_datetime,
    convert_timestamp,
    display_table,
    generate_config,
    get_artist_names,
    get_auth_and_device,
    get_current_playback,
    get_index,
    parse_recent_playback,
    play_or_queue,
    truncate,
    wait_display_playback,
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
    "user-library-modify",
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
    scope: Optional[str] = STATE_STR,
    client_id: Optional[str] = SPOTIFY_CLIENT_ID,
    client_secret: Optional[str] = SPOTIFY_CLIENT_SECRET,
    redirect_uri: Optional[str] = SPOTIFY_REDIRECT_URI,
):

    sp_auth = None
    config_dir = Path(user_config_dir("spoticli", "joebonneau"))
    config_file = config_dir / "spoticli.ini"

    try:
        if ctx.invoked_subcommand != "cfg":
            if CACHED_TOKEN_INFO:
                token_info = json.loads(CACHED_TOKEN_INFO)
                sp_auth = sp.Spotify(
                    auth_manager=SpotifyOAuth(
                        scope=scope,
                        client_id=client_id,
                        client_secret=client_secret,
                        redirect_uri=redirect_uri,
                        cache_handler=MemoryCacheHandler(token_info=token_info),
                    )
                )
            elif config_file.exists():
                config = ConfigParser()
                config.read(config_file)

                auth = config["auth"]
                client_id = auth["spotify_client_id"]
                client_secret = auth["spotify_client_secret"]
                redirect_uri = auth["spotify_redirect_uri"]
                user = auth["spotify_user_id"]

                sp_auth = sp.Spotify(
                    auth_manager=SpotifyOAuth(
                        scope=scope,
                        client_id=client_id,
                        client_secret=client_secret,
                        redirect_uri=redirect_uri,
                    )
                )
            else:
                sp_auth = sp.Spotify(
                    auth_manager=SpotifyOAuth(
                        scope=scope,
                        client_id=client_id,
                        client_secret=client_secret,
                        redirect_uri=redirect_uri,
                    )
                )

            devices_res = sp_auth.devices()
            device_id = check_devices(devices_res)
            if device_id:
                sp_auth.transfer_playback(device_id=device_id, force_play=True)
                sleep(0.2)

            ctx.obj = {"sp_auth": sp_auth, "device_id": device_id, "user": user}

    except (SpotifyException, SpotifyOauthError) as e:
        # Spotipy uses SPOTIPY in its environment variables which might be confusing for user.
        message = str(e).replace("SPOTIPY", "SPOTIFY")
        click.secho(
            f"API authorization failed! {message}",
            fg="red",
        )
        raise
    except (KeyError, ConfigError):
        click.secho(
            "Config file exists but is set up improperly. Try recreating the config file.",
            fg="red",
        )
        raise


@main.command("cfg")
def cfg():
    """
    Generates a configuration file for Spotify credentials.
    """
    generate_config()


@main.command("prev")
@click.option("--device", envvar="SPOTIFY_DEVICE_ID")
@click.pass_obj
def previous_track(ctx: dict[str, Any], device: Optional[str]):
    """
    Skips playback to the track played previous to the current track.
    """
    device, sp_auth = get_auth_and_device(ctx, device)

    try:
        playback_res = sp_auth.current_playback()
        playback = get_current_playback(playback_res, display=False)
        if playback.get("skip_prev_disallowed"):
            click.echo("No previous tracks are available to skip to.")
        else:
            sp_auth.previous_track(device_id=device)
            # delay to prevent fetching current playback before it updates on server side.
            wait_display_playback(sp_auth)
    except AttributeError:
        # AttributeError is thrown if authorization was unsuccessful, so show that error instead.
        pass
    except SpotifyException as e:
        click.secho(str(e), fg="red")


@main.command("next")
@click.option("--device", envvar="SPOTIFY_DEVICE_ID")
@click.pass_obj
def next_track(ctx: dict[str, Any], device: Optional[str]):
    """
    Skips playback to the next track in the queue
    """
    device, sp_auth = get_auth_and_device(ctx, device)

    try:
        sp_auth.next_track(device_id=device)
        # delay to prevent fetching current playback before it updates on server side.
        wait_display_playback(sp_auth)
    except AttributeError:
        # AttributeError is thrown if authorization was unsuccessful, so show that error instead.
        pass
    except SpotifyException as e:
        click.secho(str(e), fg="red")


@main.command("pause")
@click.option("--device", envvar="SPOTIFY_DEVICE_ID")
@click.pass_obj
def pause_playback(ctx: dict[str, Any], device: Optional[str]):
    """
    Pauses playback.
    """
    device, sp_auth = get_auth_and_device(ctx, device)

    try:
        current_playback = sp_auth.current_playback()
        playback = get_current_playback(current_playback, display=False)
        if playback.get("pausing_disallowed"):
            click.echo("No current playback to pause.")
        else:
            sp_auth.pause_playback(device_id=device)
            click.echo("Playback paused.")
    except AttributeError:
        # AttributeError is thrown if authorization was unsuccessful, so show that error instead.
        pass
    except SpotifyException as e:
        click.secho(str(e), fg="red")


@main.command("play")
@click.option("--device", envvar="SPOTIFY_DEVICE_ID")
@click.argument("url", required=False)
@click.pass_obj
def start_playback(ctx: dict[str, Any], device: Optional[str], url: Optional[str]):
    """
    Resumes playback on the active track.
    """
    device, sp_auth = get_auth_and_device(ctx, device)

    try:
        if url:
            valid_url = check_url_format(url)
            if "track" in url:
                sp_auth.start_playback(device_id=device, uris=[valid_url])
            else:
                sp_auth.start_playback(device_id=device, context_uri=valid_url)
        else:
            current_playback = sp_auth.current_playback()
            playback = get_current_playback(current_playback, display=False)
        if not playback.get("resuming_disallowed"):
            sp_auth.start_playback(device_id=device)
            click.secho("Playback resumed.")
        wait_display_playback(sp_auth)
    except TypeError:
        # the get_current_playback function will have already displayed the error message
        pass
    except ValueError:
        click.secho("Invalid URL was provided.", fg="red")
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
@click.option("--user", envvar="SPOTIFY_USER_ID")
@click.argument("name", required=True)
@click.pass_obj
def create_playlist(
    ctx: dict[str, Any], pub: bool, c: bool, d: str, name: str, user: str
):
    """
    Creates a new playlist.
    """

    _, sp_auth = get_auth_and_device(ctx, device=None)

    if all((pub, c)):
        click.secho(style("Collaborative playlists can only be private.", fg="red"))
    else:
        try:
            sp_auth.user_playlist_create(
                user=ctx["user"],
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
def seek(ctx: dict[str, Any], timestamp: str, device: str):
    """
    Seeks the track to the timestamp specified.

    Timestamp format is MM:SS
    """

    device, sp_auth = get_auth_and_device(ctx, device)

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
def increase_volume(ctx: dict[str, Any], amount: int, device: str):
    """
    Increases volume by the increment specified (defaults to 10%).
    """

    device, sp_auth = get_auth_and_device(ctx, device)

    try:
        current_playback = sp_auth.current_playback()

        playback = get_current_playback(res=current_playback, display=False)
        if volume := playback.get("volume"):
            previous_volume = volume

        new_volume = int(round(previous_volume + amount, 0))
        new_volume = min(new_volume, 100)
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
def decrease_volume(ctx: dict[str, Any], amount: int, device: str):
    """
    Decreases volume by the increment specified (defaults to 10%).
    """

    device, sp_auth = get_auth_and_device(ctx, device)

    try:
        current_playback = sp_auth.current_playback()
        playback = get_current_playback(res=current_playback, display=False)
        if volume := playback.get("volume"):
            previous_volume = volume

            new_volume = int(round(previous_volume - amount, 0))
            new_volume = max(new_volume, 0)
            sp_auth.volume(new_volume, device_id=device)
            click.secho(f"New volume: {new_volume}")
    except AttributeError:
        # AttributeError is thrown if authorization was unsuccessful, so show that error instead.
        pass
    except SpotifyException as e:
        click.secho(str(e), fg="red")


@main.command("now")
@click.option("-v", "--verbose", is_flag=True, help="displays additional info")
@click.option("-u", "--url", default="t", help="displays current playback url")
@click.pass_obj
def now_playing(ctx: dict[str, Any], verbose: bool, url: str):
    """
    Displays info about the current playback.
    """

    _, sp_auth = get_auth_and_device(ctx, device=None)

    try:
        current_playback = sp_auth.current_playback()
        playback = get_current_playback(res=current_playback, display=True)
        track_uri = playback.get("track_uri")
        if track_uri and verbose:
            audio_features = sp_auth.audio_features(track_uri)
            click.echo(f"BPM: {audio_features[0]['tempo']}")
            click.echo(f"Time signature: 4/{audio_features[0]['time_signature']}")
            if url == "t":
                click.echo(f"Track URL: {style(playback['track_url'], fg='magenta')}")
            elif url == "a":
                click.echo(f"Album URL: {style(playback['album_url'], fg='blue')}")
    except AttributeError:
        # AttributeError is thrown if authorization was unsuccessful, so show that error instead.
        pass
    except SpotifyException as e:
        click.secho(str(e), fg="red")


@main.command("shuffle")
@click.option("--device", envvar="SPOTIFY_DEVICE_ID")
@click.option("-on/-off", required=True, is_flag=True)
@click.pass_obj
def toggle_shuffle(ctx: dict[str, Any], on: bool, device: str):
    """
    Toggles shuffling on or off.
    """

    device, sp_auth = get_auth_and_device(ctx, device)

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
def get_random_saved_album(ctx: dict[str, Any], device: str):
    """
    Fetches all albums in user library and selects one randomly.
    """
    device, sp_auth = get_auth_and_device(ctx, device)

    try:
        saved_albums: list[dict] = []
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

        # Pick a random index that corresponds to an album URI
        rand_i = random.randint(0, len(saved_albums))

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

        queue = play_or_queue()
        if queue == "q":
            add_album_to_queue(sp_auth, saved_albums[rand_i]["album_uri"])
        else:
            sp_auth.start_playback(
                context_uri=saved_albums[rand_i]["album_uri"], device_id=device
            )
            wait_display_playback(sp_auth)
    except AttributeError:
        # AttributeError is thrown if authorization was unsuccessful, so show that error instead.
        pass
    except SpotifyException as e:
        click.secho(str(e), fg="red")


@main.command("actp")
@click.pass_obj
def add_current_track_to_playlists(ctx: dict[str, Any]):
    """
    Adds the current track in playback to one or more playlist(s).
    """

    _, sp_auth = get_auth_and_device(ctx, device=None)

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
        display_table(display_dict)

        indices = click.prompt(
            "Enter the indices of the playlists to add the track to separated by commas",
            type=CommaSeparatedIndices([str(i) for i in positions]),
            show_choices=False,
        )
        track_uri = playback.get("track_uri")
        if track_uri:
            for index in indices:
                items = [track_uri]
                sp_auth.playlist_add_items(
                    playlist_id=playlist_dict["playlist_ids"][index],
                    items=items,
                )
            track_name = style(playback["track_name"], fg="magenta")
            rest_of_the_msg = style(
                "was successfully added to all specified playlists!", fg="green"
            )
            click.echo(f"{track_name} {rest_of_the_msg}")

    except AttributeError:
        # AttributeError is thrown if authorization was unsuccessful, so show that error instead.
        pass
    except SpotifyException as e:
        click.secho(str(e), fg="red")


@main.command("recent")
@click.option("-a", "--after", default=None, help="YYYYMMDD MM:SS")
@click.option("-l", "--limit", default=25, help="Entries to return (max 50)")
@click.option("--device", envvar="SPOTIFY_DEVICE_ID")
@click.option("--user", envvar="SPOTIFY_USER_ID")
@click.pass_obj
def recently_played(
    ctx: dict[str, Any], after: str, limit: int, device: str, user: str
):
    """
    Displays information about recently played tracks.
    """

    device, sp_auth = get_auth_and_device(ctx, device)

    try:
        if after:
            recent_playback = sp_auth.current_user_recently_played(
                limit=limit, after=convert_datetime(after)
            )
        else:
            recent_playback = sp_auth.current_user_recently_played(limit=limit)

        positions, recent_dict, track_uris = parse_recent_playback(recent_playback)

        task = play_or_queue(create_playlist=True)
        if task == "cp":
            indices = click.prompt(
                "Enter the indices of the tracks to add to the playlist separated by commas",
                type=CommaSeparatedIndexRange([str(i) for i in positions]),
                show_choices=False,
            )
            playlist_name = click.prompt("Enter the playlist name")

            sp_auth.user_playlist_create(user=ctx["user"], name=playlist_name)
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
        elif task in ("p", "q"):
            index = get_index([str(i) for i in positions])
            item_type = click.prompt(
                "Track or associated album?",
                type=Choice(("t", "a"), case_sensitive=False),
                show_choices=True,
            )
            if task == "q" and item_type == "t":
                sp_auth.add_to_queue(recent_dict["track_uri"][index], device_id=device)
                click.secho("Track successfully added to the queue.", fg="green")
            elif task == "q" and item_type == "a":
                add_album_to_queue(sp_auth, recent_dict["album_uri"][index])

            elif task == "p" and item_type == "t":
                sp_auth.start_playback(
                    uris=[recent_dict["track_uri"][index]], device_id=device
                )
            elif task == "p" and item_type == "a":
                sp_auth.start_playback(
                    context_uri=recent_dict["album_uri"][index],
                    device_id=device,
                )
            wait_display_playback(sp_auth)
    except ValueError:
        click.secho("Invalid format. Proper format is 'YYYYMMDD MM:SS", fg="red")
    except AttributeError:
        # AttributeError is thrown if authorization was unsuccessful, so show that error instead.
        pass
    except SpotifyException as e:
        click.secho(str(e), fg="red")


@main.command("search")
@click.option("--device", default=None, envvar="SPOTIFY_DEVICE_ID")
@click.option(
    "-t",
    "type_",
    type=click.Choice(("album", "artist", "playlist", "track")),
    required=True,
)
@click.argument("query", required=True)
@click.pass_obj
def search(ctx: dict[str, Any], query: str, type_: str, device: str):
    """
    Queries Spotify's databases.
    """
    device, sp_auth = get_auth_and_device(ctx, device)
    commands.search(sp_auth=sp_auth, query=query, type_=type_, device=device)


@main.command("atq")
@click.option("--device", envvar="SPOTIFY_DEVICE_ID")
@click.argument("url", required=True)
@click.pass_obj
def add_to_queue(ctx: dict[str, Any], url: str, device: str):
    """
    Adds a track or album to the queue from a Spotify URL.
    """

    device, sp_auth = get_auth_and_device(ctx, device)

    try:
        valid_url = check_url_format(url)
        if "album" in url:
            add_album_to_queue(sp_auth, valid_url, device)
        else:
            sp_auth.add_to_queue(valid_url, device)
            click.secho("Track successfully added to queue.", fg="green")
    except ValueError:
        click.secho("An invalid URL was provided.", fg="red")
    except AttributeError:
        pass
    except SpotifyException as e:
        click.secho(str(e), fg="red")


@main.command("spa")
@click.argument("url", required=True)
@click.pass_obj
def save_playlist_albums(
    ctx: dict[str, Any],
    url: str,
):
    """
    Retrieves all albums from a given playlist and allows the user to add them to their
    library.
    """
    check_url_format(url)
    _, sp_auth = get_auth_and_device(ctx, device=None)
    commands.save_playlist_items(sp_auth, url)
