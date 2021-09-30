import json
import os
import random
from configparser import ConfigParser
from pathlib import Path
from time import sleep
from typing import Optional

import click
import spotipy as sp
from appdirs import user_config_dir
from click.termui import style
from click.types import Choice
from spotipy.cache_handler import MemoryCacheHandler
from spotipy.client import SpotifyException
from spotipy.oauth2 import SpotifyOAuth, SpotifyOauthError
from tabulate import tabulate

from spoticli.types import CommaSeparatedIndexRange, CommaSeparatedIndices
from spoticli.util import (
    add_album_to_queue,
    check_url_format,
    convert_datetime,
    convert_timestamp,
    generate_config,
    get_artist_names,
    get_current_playback,
    parse_recent_playback,
    search_parse,
    search_proceed,
    truncate,
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


@click.group(invoke_without_command=True)
@click.option("-c", "--config", is_flag=True)
@click.pass_context
def main(
    ctx,
    config,
    scope: Optional[str] = STATE_STR,
    client_id: Optional[str] = SPOTIFY_CLIENT_ID,
    client_secret: Optional[str] = SPOTIFY_CLIENT_SECRET,
    redirect_uri: Optional[str] = SPOTIFY_REDIRECT_URI,
):
    config_dir = Path(user_config_dir("spoticli", "joebonneau"))
    config_file = config_dir / "spoticli.ini"
    sp_auth = None

    try:
        if config:
            generate_config()
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

            client_id = config["auth"]["SPOTIFY_CLIENT_ID"]
            client_secret = config["auth"]["SPOTIFY_CLIENT_SECRET"]
            redirect_uri = config["auth"]["SPOTIFY_REDIRECT_URI"]

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

        ctx.obj = sp_auth
    except KeyError:
        click.secho(
            "Config file exists but is set up improperly. Try recreating the config file.",
            fg="red",
        )
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
        playback_res = sp_auth.current_playback()
        playback = get_current_playback(playback_res, display=False)
        if playback["skip_prev_disallowed"]:
            click.echo("No previous tracks are available to skip to.")
        else:
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
    Skips playback to the next track in the queue
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
        current_playback = sp_auth.current_playback()
        playback = get_current_playback(current_playback, display=False)
        if playback["pausing_disallowed"]:
            click.echo("No current playback to pause.")
        else:
            sp_auth.pause_playback(device_id=device)
            click.secho("Playback paused.")
    except AttributeError:
        # AttributeError is thrown if authorization was unsuccessful, so show that error instead.
        pass
    except SpotifyException as e:
        click.secho(str(e), fg="red")


@main.command("play")
@click.option("--device", envvar="SPOTIFY_DEVICE_ID")
@click.argument("url", required=False)
@click.pass_obj
def start_playback(ctx, device, url):
    """
    Resumes playback on the active track.
    """
    sp_auth = ctx

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
            if playback["resuming_disallowed"]:
                click.secho("Playback is already active.")
            else:
                sp_auth.start_playback(device_id=device)
                click.secho("Playback resumed.")

        sleep(0.5)
        current_playback = sp_auth.current_playback()
        get_current_playback(res=current_playback, display=True)
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
            config_dir = Path(user_config_dir("spoticli", "joebonneau"))
            config_file = config_dir / "spoticli.ini"

            if config_file.exists():
                config = ConfigParser()
                config.read(config_file)
                SPOTIFY_USER_ID = config["auth"]["SPOTIFY_USER_ID"]

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

    Timestamp format is MM:SS
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
@click.option("-u", "--url", default="t", help="displays current playback url")
@click.pass_obj
def now_playing(ctx, verbose, url):
    """
    Displays info about the current playback.
    """

    sp_auth = ctx

    try:
        current_playback = sp_auth.current_playback()
        playback = get_current_playback(res=current_playback, display=True)

        if verbose:
            audio_features = sp_auth.audio_features(playback["track_uri"])
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
            artists = truncate(saved_albums[rand_i]["artists"])
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

        queue = click.prompt(
            "Play album now or add to queue?",
            type=Choice(("p", "q"), case_sensitive=False),
            show_choices=True,
        )
        if queue == "q":
            add_album_to_queue(sp_auth, saved_albums[rand_i]["album_uri"])
        else:
            sp_auth.start_playback(
                context_uri=saved_albums[rand_i]["album_uri"], device_id=device
            )
            sleep(0.5)
            current_playback = sp_auth.current_playback()
            get_current_playback(res=current_playback, display=True)
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
            "Enter the indices of the playlists to add the track to separated by commas",
            type=CommaSeparatedIndices([str(i) for i in positions]),
            show_choices=False,
        )

        for index in indices:
            sp_auth.playlist_add_items(
                playlist_id=playlist_dict["playlist_ids"][index],
                items=[playback["track_uri"]],
            )

        click.echo(
            f"{style(playback['track_name'], fg='magenta')} {style('was successfully added to all specified playlists!', fg='green')}"
        )

    except AttributeError:
        # AttributeError is thrown if authorization was unsuccessful, so show that error instead.
        pass
    except SpotifyException as e:
        click.secho(str(e), fg="red")


@main.command("recent")
@click.option("--device", envvar="SPOTIFY_DEVICE_ID")
@click.option("-a", "--after", default=None, help="YYYYMMDD MM:SS")
@click.option("-l", "--limit", default=25, help="Entries to return (max 50)")
@click.pass_obj
def recently_played(ctx, after, limit, device):
    """
    Displays information about recently played tracks.
    """

    sp_auth = ctx

    try:
        if after:
            recent_playback = sp_auth.current_user_recently_played(
                limit=limit, after=convert_datetime(after)
            )
        else:
            recent_playback = sp_auth.current_user_recently_played(limit=limit)

        positions, recent_dict, track_uris = parse_recent_playback(recent_playback)

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

            config_dir = Path(user_config_dir("spoticli", "joebonneau"))
            config_file = config_dir / "spoticli.ini"

            if config_file.exists():
                config = ConfigParser()
                config.read(config_file)
                SPOTIFY_USER_ID = config["auth"]["SPOTIFY_USER_ID"]

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
        elif task in ("p", "q"):
            index = int(
                click.prompt(
                    "Enter the index of interest",
                    type=Choice([str(i) for i in positions]),
                    show_choices=False,
                )
            )
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
@click.option("--device", default=None, envvar="SPOTIFY_DEVICE_ID")
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
        search_res = sp_auth.search(q=term, limit=10, type=type_)
        results, uris = search_parse(search_res, k)
        search_proceed(sp_auth, type_, results, uris, device=device)
    except AttributeError:
        pass
    except SpotifyException as e:
        click.secho(str(e), fg="red")


@main.command("atq")
@click.option("--device", envvar="SPOTIFY_DEVICE_ID")
@click.argument("url", required=True)
@click.pass_obj
def add_to_queue(ctx, url, device):
    """
    Adds a track or album to the queue from a Spotify URL.
    """

    sp_auth = ctx

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
# @click.option("-c", "--content", default="all")
@click.pass_obj
def save_playlist_albums(
    ctx,
    url,
):
    """
    Retrieves all albums from a given playlist and allows the user to add them to their library.
    """

    sp_auth = ctx

    fields = "items(track(album(album_type,artists(name),name,total_tracks,uri,release_date)))"

    try:
        check_url_format(url)
        click.secho("Retrieving all albums and EPs from the playlist...", fg="magenta")
        playlist_items = sp_auth.playlist_items(playlist_id=url, fields=fields)
        album_items = []
        album_uris = []
        index = 0
        for item in playlist_items["items"]:
            item_album = item["track"]["album"]
            if item_album["total_tracks"] > 1 and item_album["album_type"] == "single":
                is_album_saved = sp_auth.current_user_saved_albums_contains(
                    albums=[item_album["uri"]]
                )
                if not is_album_saved[0]:
                    album_items.append(
                        {
                            "index": index,
                            "artists": truncate(get_artist_names(item_album), 40),
                            "album": truncate(item_album["name"], 40),
                            "album_type": "EP",
                            "total_tracks": item_album["total_tracks"],
                            "release_date": item_album["release_date"],
                        }
                    )
                    album_uris.append(item_album["uri"])
                    index += 1
            elif item_album["album_type"] == "album":
                is_album_saved = sp_auth.current_user_saved_albums_contains(
                    albums=[item_album["uri"]]
                )
                if not is_album_saved[0]:
                    album_items.append(
                        {
                            "index": index,
                            "artists": truncate(get_artist_names(item_album), 40),
                            "album": truncate(item_album["name"], 40),
                            "album_type": item_album["album_type"],
                            "total_tracks": item_album["total_tracks"],
                            "release_date": item_album["release_date"],
                        }
                    )
                    album_uris.append(item_album["uri"])
                    index += 1
        click.echo(tabulate(album_items, headers="keys", tablefmt="github"))
        add_all_albums = click.prompt(
            "Add all albums to user library?",
            type=Choice(("y", "n")),
            show_choices=True,
        )

        if add_all_albums == "y":
            sp_auth.current_user_saved_albums_add(albums=album_uris)
        else:
            album_selection = click.prompt(
                "Enter the indices of albums to add (separated by a comma)",
                type=CommaSeparatedIndices([str(i) for i in range(len(album_uris))]),
                show_choices=False,
            )

            album_sublist = [album_uris[i] for i in album_selection]
            sp_auth.current_user_saved_albums_add(albums=album_sublist)

        click.secho("Albums successfully added to user library!", fg="green")
    except ValueError:
        click.secho("An invalid URL was provided.", fg="red")
    except AttributeError:
        pass
    except SpotifyException as e:
        click.secho(str(e), fg="red")
