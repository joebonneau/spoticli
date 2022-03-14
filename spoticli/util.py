import re
import time
from datetime import datetime
from time import sleep
from typing import Any, Iterable, Optional

import click
from click.termui import style
from click.types import Choice
from spotipy.client import Spotify
from tabulate import tabulate
from tqdm import tqdm

Y_N_CHOICE_CASE_INSENSITIVE = Choice(("y", "n"), case_sensitive=False)


def get_index(choices):
    idx_str = click.prompt(
        "Enter the index",
        type=choices,
        show_choices=False,
    )
    return int(idx_str)


def play_or_queue(create_playlist=False):
    choices = ("p", "q", "cp") if create_playlist else ("p", "q")
    return click.prompt(
        "Play now or add to queue?",
        type=Choice(choices, case_sensitive=False),
        show_choices=True,
    )


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
