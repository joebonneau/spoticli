import re
import time
from configparser import ConfigParser
from datetime import datetime
from os import mkdir
from pathlib import Path
from time import sleep
from typing import Any, Iterable, Optional

import click
from appdirs import user_config_dir
from click import IntRange
from click.termui import style
from click.types import Choice
from spotipy.client import Spotify
from tabulate import tabulate
from tqdm import tqdm

from spoticli.exceptions import InvalidURL, NoDevicesFound
from spoticli.types import SpotifyCredential

Y_N_CHOICE_CASE_INSENSITIVE = Choice(("y", "n"), case_sensitive=False)


def get_index(choices):
    idx_str = click.prompt(
        "Enter the index",
        type=choices,  # type: ignore
        show_choices=False,
    )
    return int(idx_str)


def play_or_queue(create_playlist=False):
    choices = ("p", "q")
    if create_playlist:
        choices = choices.add("cp")
    return click.prompt(
        "Play now or add to queue?",
        type=Choice(choices, case_sensitive=False),
        show_choices=True,
    )


def add_playlist_to_queue(sp_auth, uri: str, device: Optional[str] = None) -> None:
    """
    Adds all tracks from a playlist to the queue.
    """

    offset = 0
    click.secho("Adding playlist tracks to queue...", fg="magenta")
    while True:
        playlists_res = sp_auth.playlist_items(
            uri, limit=100, fields="items.track.uri", offset=offset
        )
        for item in tqdm(playlists_res["items"]):
            sp_auth.add_to_queue(item["track"]["uri"], device_id=device)
        if len(playlists_res) < 100:
            break

        offset += 100

    click.secho("All playlist tracks added successfully!", fg="green")


def add_album_to_queue(
    sp_auth: Spotify, uri: str, device: Optional[str] = None
) -> None:
    """
    Adds all tracks of an album to the queue.
    """

    while True:
        tracks_res = sp_auth.album_tracks(uri, limit=50, offset=0)
        for track in tqdm(tracks_res["items"]):
            sp_auth.add_to_queue(track["uri"], device_id=device)
        if len(tracks_res) < 50:
            break

    click.secho("Album successfully added to the queue.", fg="green")


def get_artist_names(res: dict[str, Any]) -> str:
    """
    Retrieves all artist names for a given input to the "album" key of a response.
    """

    artists = [artist["name"] for artist in res["artists"]]
    return ", ".join(artists)


def get_current_playback(res: dict[str, Any], display: bool) -> dict:
    """
    Retrieves current playback information, parses the json response, and optionally displays
    information about the current playback.
    """

    playback = {}

    try:
        playback_items = res["item"]
        playback_album = playback_items["album"]

        playback = {
            "artists": get_artist_names(playback_album),
            "track_name": playback_items["name"],
            "track_uri": playback_items["uri"],
            "track_url": playback_items["external_urls"].get("spotify"),
            "album_name": playback_album["name"],
            "album_type": playback_album["album_type"],
            "album_uri": playback_album["uri"],
            "album_url": playback_album["external_urls"].get("spotify"),
            "release_date": playback_album["release_date"],
            "duration": convert_ms(playback_items["duration_ms"]),
            "volume": res["device"]["volume_percent"],
            "shuffle_state": res["shuffle_state"],
            "resuming_disallowed": res["actions"]["disallows"].get("resuming"),
            "pausing_disallowed": res["actions"]["disallows"].get("pausing"),
            "skip_prev_disallowed": res["actions"]["disallows"].get("skipping_prev"),
        }

        if display:
            _display_current_feedback(playback)
    except TypeError:
        click.secho("Nothing is currently playing!", fg="red")

    return playback


def _display_current_feedback(playback):
    track_name = style(playback["track_name"], fg="magenta")
    artists_name = style(playback["artists"], fg="green")
    album_name = style(playback["album_name"], fg="blue")
    album_type = playback["album_type"]

    click.secho(
        f"Now playing: {track_name} by {artists_name} from the {album_type} {album_name}"
    )
    click.echo(
        f"Duration: {playback['duration']}, Released: {playback['release_date']}"
    )


def search_parse(res: dict[str, Any], k: str) -> tuple[list[dict[str, Any]], list[str]]:

    items = res[k]["items"]
    uris = []
    results = []
    for i, item in enumerate(items):
        if k == "albums":
            artists = get_artist_names(item)
            name = item["name"]
            uris.append(item["uri"])
            results.append(
                {
                    "index": i,
                    "artist(s)": truncate(artists),
                    "album title": name,
                    "release date": item["release_date"],
                }
            )
        elif k == "artists":
            results.append({"index": i, "artist": truncate(item["name"])})
            uris.append(item["uri"])
        elif k == "playlists":
            desc = item["description"]
            uris.append(item["uri"])
            results.append(
                {
                    "index": i,
                    "name": truncate(item["name"]),
                    "creator": item["owner"]["display_name"],
                    "description": truncate(desc),
                    "tracks": item["tracks"]["total"],
                }
            )
        elif k == "tracks":
            artists = get_artist_names(item)
            name = item["name"]
            uris.append(item["uri"])
            results.append(
                {
                    "index": i,
                    "name": name,
                    "duration": convert_ms(item["duration_ms"]),
                    "artist(s)": truncate(artists),
                    "album title": item["album"]["name"],
                    "release date": item["album"]["release_date"],
                }
            )

    return results, uris


def search_proceed(
    sp_auth: Spotify,
    type_: str,
    results: list[dict[str, Any]],
    uris: list[str],
    device: Optional[str] = None,
) -> None:

    index = get_index(IntRange(min=0, max=len(results) - 1))
    if type_ != "artist":
        action = play_or_queue()
        if action == "p":
            sp_auth.start_playback(uris=[uris[index]], device_id=device)
            wait_display_playback(sp_auth, sleep_time=0.5)
        elif type_ == "album":
            add_album_to_queue(sp_auth, uris[index], device=device)
        elif type_ == "playlist":
            confirmation = click.prompt(
                f"Are you sure you want to add all {results[index]['tracks']} tracks?",
                type=Y_N_CHOICE_CASE_INSENSITIVE,
                show_choices=True,
            )
            if confirmation == "y":
                add_playlist_to_queue(sp_auth, uris[index], device=device)
            else:
                click.secho("Operation aborted.", fg="red")
        elif type_ == "track":
            sp_auth.add_to_queue(uris[index], device_id=device)
            click.secho("Track added to queue successfully!", fg="green")
    else:
        album_or_track = click.prompt(
            "View artist albums or most popular tracks?",
            type=Choice(("a", "t"), case_sensitive=False),
            show_choices=True,
        )
        if album_or_track == "a":
            artist_albums_res = sp_auth.artist_albums(
                uris[index], album_type="album,single"
            )
            uris, choices = parse_artist_albums(artist_albums_res)
        else:
            artist_tracks_res = sp_auth.artist_top_tracks(uris[index])
            uris, choices = parse_artist_top_tracks(artist_tracks_res)

        index = int(
            click.prompt(
                "Enter the index",
                type=choices,
                show_choices=False,
            )
        )
        p_or_q = click.prompt(
            "Play now or add to queue?",
            type=Choice(("p", "q"), case_sensitive=False),
            show_choices=True,
        )
        if p_or_q == "p":
            play_content(
                sp_auth=sp_auth,
                uri=uris[index],
                album_or_track=album_or_track,
                device_id=device,
            )
            wait_display_playback(sp_auth, sleep_time=0.5)
        else:
            if album_or_track == "a":
                add_album_to_queue(sp_auth, uris[index], device=device)
            else:
                sp_auth.add_to_queue(uris[index], device_id=device)
                click.secho("Successfully added to queue!", fg="green")


def play_content(
    sp_auth: Spotify,
    uri: str,
    album_or_track: str,
    device_id: str = None,
):
    if album_or_track == "t":
        sp_auth.start_playback(uris=[uri], device_id=device_id)
    elif album_or_track == "a":
        sp_auth.start_playback(context_uri=uri, device_id=device_id)


def display_table(data: Iterable[Iterable]) -> None:
    click.echo(tabulate(data, headers="keys", tablefmt="github"))


def wait_display_playback(sp_auth: Spotify, sleep_time=0.2):
    # wait to ensure that the API returns new data
    sleep(sleep_time)
    current_playback = sp_auth.current_playback()
    get_current_playback(res=current_playback, display=True)


def get_auth_and_device(ctx, device):
    sp_auth = ctx["sp_auth"]

    if not device:
        device = ctx["device_id"]
    return device, sp_auth


def convert_ms(duration_ms: int) -> str:
    """
    Converts milliseconds to a string representation of a timestamp (MM:SS).
    """

    minutes, seconds = divmod(duration_ms / 1000, 60)
    rounded_seconds = int(round(seconds, 0))
    seconds_str = str(rounded_seconds)
    if len(seconds_str) < 2:
        seconds_str = seconds_str.zfill(2)

    return f"{int(minutes)}:{seconds_str}"


def convert_timestamp(timestamp: str) -> int:
    """
    Converts a timestamp (MM:SS) to milliseconds.
    """

    timestamp_list = timestamp.split(":")
    minutes = timestamp_list[0]
    seconds = timestamp_list[1]
    minutes_in_ms = int(minutes) * 60 * 1000
    seconds_in_ms = int(seconds) * 1000
    total_ms = minutes_in_ms + seconds_in_ms

    if any((len(seconds) > 2, len(seconds) < 2, minutes_in_ms < 0, seconds_in_ms < 0)):
        raise ValueError("Invalid format. Proper format is MM:SS.")

    return total_ms


def convert_datetime(datetime_str: str) -> int:
    """
    Converts a string representation of a datetime (YYYYMMDD HH:MM) to milliseconds
    """

    datetime_pattern = "%Y%m%d %H:%M"
    datetime_obj = datetime.strptime(datetime_str, datetime_pattern)
    unix_timestamp = time.mktime(datetime_obj.timetuple()) * 1000

    return int(unix_timestamp)


def truncate(name: str, length: int = 50) -> str:
    """
    Truncates a string and adds an elipsis if it exceeds the specified length.
    Otherwise, return the unmodified string.
    """
    if len(name) > length:
        name = f"{name[:length]}..."
    return name


def check_url_format(url: str) -> str:
    """
    Performs a simple URL validation check. Definitely won't catch all errors, but will
    eliminate most.
    """

    pattern = r"open.spotify.com/[a-z]{5,8}/\w{22}"

    match = re.search(pattern, url)
    if not match:
        raise InvalidURL("Invalid URL was provided.")

    return f"https://{match.group()}"


def parse_recent_playback(
    res: dict[str, Any]
) -> tuple[list[int], dict[str, list], list[str]]:
    """
    Parses the response returned by Spotify.current_user_recently_played and displays a
    table of information.
    """

    positions = []
    track_names = []
    track_uris = []
    album_names = []
    album_uris = []
    album_types = []
    timestamps = []
    playback_items = res["items"]
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
    display_dict = {
        k: recent_dict[k]
        for k in (
            "index",
            "track_name",
            "album_type",
            "album_name",
            "timestamp",
        )
    }

    display_table(display_dict)

    return positions, recent_dict, track_uris


def parse_artist_top_tracks(res: dict[str, Any]) -> tuple[list[str], IntRange]:
    """
    Parses the response returned by Spotify.artist_top_tracks and displays a table of information.
    """

    tracks = []
    uris = []
    for i, track in enumerate(res["tracks"]):
        tracks.append(
            {
                "index": i,
                "name": track["name"],
                "artists": get_artist_names(track["album"]),
                "popularity": track["popularity"],
            }
        )
        uris.append(track["uri"])
    display_table(tracks)
    choices = IntRange(min=0, max=len(tracks) - 1)

    return uris, choices


def parse_artist_albums(res: dict[str, Any]) -> tuple[list[str], IntRange]:
    """
    Parses the response returned by Spotify.artist_albums and displays a table of information.
    """

    albums = []
    uris = []
    for i, item in enumerate(res["items"]):
        album_type = item["album_type"]
        artists = truncate(get_artist_names(item))
        album_name = item["name"]
        release_date = item["release_date"]
        total_tracks = item["total_tracks"]
        uris.append(item["uri"])
        albums.append(
            {
                "index": i,
                "artist(s)": artists,
                "album name": album_name,
                "album type": album_type,
                "tracks": total_tracks,
                "release date": release_date,
            }
        )

    display_table(albums)
    choices = IntRange(min=0, max=len(albums) - 1)

    return uris, choices


def generate_config():

    config_dir = Path(user_config_dir()) / "spoticli"
    config_file = config_dir / "spoticli.ini"
    config = ConfigParser()

    if not config_dir.exists():
        mkdir(config_dir)

    proceed = "y"
    if config_file.exists():
        proceed = click.prompt(
            "A config file already exists. Do you want to overwrite its contents?",
            type=Y_N_CHOICE_CASE_INSENSITIVE,
            show_choices=True,
        )

    if proceed == "y":
        _accept_config_input(config, config_file)
    else:
        click.secho("Configuration creation canceled.")


def _accept_config_input(config, config_file):
    client_id = click.prompt(
        "Provide the Spotify client ID from the developer dashboard",
        type=SpotifyCredential(),
    )
    client_secret = click.prompt(
        "Provide the Spotify client secret from the developer dashboard",
        type=SpotifyCredential(),
    )
    redirect_uri = click.prompt(
        "Provide the redirect URI you specified in the Spotify app"
    )
    user_id = click.prompt("Provide the Spotify user ID")

    config["auth"] = {
        "SPOTIFY_CLIENT_ID": client_id,
        "SPOTIFY_CLIENT_SECRET": client_secret,
        "SPOTIFY_USER_ID": user_id,
        "SPOTIFY_REDIRECT_URI": redirect_uri,
    }

    with open(config_file, "w") as cfg:
        config.write(cfg)

    click.secho("Config file created successfully!", fg="green")


def check_devices(res: dict[str, list[dict[str, Any]]]) -> Optional[str]:

    active_device = False
    device_options: list[dict[str, Any]] = []
    for i, device in enumerate(res["devices"]):
        device_options.append(
            {
                "index": i,
                "name": device["name"],
                "type": device["type"],
                "id": device["id"],
            }
        )

        if device["is_active"]:
            active_device = True

    if not device_options:
        raise NoDevicesFound(
            "No devices were found. Verify the Spotify client is open on a device."
        )

    if not active_device:
        if len(device_options) == 1:
            device_to_activate = 0
        else:
            display_table(device_options)

            device_to_activate = click.prompt(
                "Enter the index of the device to activate",
                type=IntRange(min=0, max=len(device_options) - 1),
                show_choices=False,
            )

        return device_options[int(device_to_activate)]["id"]
    return None
