from typing import Iterable
import os

import spotipy as sp
import click
from click.termui import style

# SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
# SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")
# SPOTIFY_REDIRECT_URI = os.environ.get("SPOTIFY_REDIRECT_URI")

# USER_READ_PLAYBACK_STATE = "user-read-playback-state"


def get_current_playback(sp_auth: sp.Spotify, display: bool) -> dict:
    """
    Retrieves current playback information, parses the json response, and optionally displays
    information about the current playback.
    """

    current_playback = sp_auth.current_playback()
    playback_items = current_playback["item"]
    playback = {}

    artists = []
    for _, artist in enumerate(playback_items["artists"]):
        artists.append(artist["name"])
    artists_str = ", ".join(artists)

    playback["artists"] = artists_str
    playback["track_name"] = playback_items["name"]
    playback["track_uri"] = playback_items["uri"]
    playback["album_name"] = playback_items["album"]["name"]
    playback["album_type"] = playback_items["album"]["type"]
    playback["album_uri"] = playback_items["album"]["uri"]
    playback["release_date"] = playback_items["album"]["release_date"]
    playback["duration"] = convert_ms(playback_items["duration_ms"])
    playback["volume"] = current_playback["device"]["volume_percent"]
    playback["shuffle_state"] = current_playback["shuffle_state"]

    if display:
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

    return playback


def convert_ms(duration_ms: int) -> str:
    """
    Converts milliseconds to a string representation of a timestamp (MM:SS).
    """

    minutes, seconds = divmod(duration_ms / 1000, 60)
    rounded_seconds = int(round(seconds, 0))

    if rounded_seconds - 10 < 0:
        rounded_seconds = "0" + str(rounded_seconds)

    duration = f"{int(minutes)}:{rounded_seconds}"

    return duration


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

    if (len(seconds) > 2 or len(seconds) < 2) or (
        minutes_in_ms < 0 or seconds_in_ms < 0
    ):
        raise ValueError
    else:
        return total_ms
