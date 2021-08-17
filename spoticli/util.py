from typing import Dict, Any
import re
from datetime import datetime
import time

import spotipy as sp
import click
from click.termui import style
from tqdm import tqdm


def add_playlist_to_queue(sp_auth, uri: str) -> None:
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
            sp_auth.add_to_queue(item["track"]["uri"])
        if len(playlists_res) < 100:
            break

        offset += 100

    click.secho("All playlist tracks added successfully!", fg="green")


def add_album_to_queue(sp_auth: sp.Spotify, uri: str) -> None:
    """
    Adds all tracks of an album to the queue.
    """

    while True:
        tracks_res = sp_auth.album_tracks(uri, limit=50, offset=0)
        for track in tqdm(tracks_res["items"]):
            sp_auth.add_to_queue(track["uri"])
        if len(tracks_res) < 50:
            break

    click.secho("Album successfully added to queue!", fg="green")


def get_artist_names(res: Dict[str, Any]) -> str:
    """
    Retrieves all artist names for a given input to the "album" key of a response.
    """

    artists = []
    for artist in res["artists"]:
        artists.append(artist["name"])
    artists_str = ", ".join(artists)

    return artists_str


def get_current_playback(sp_auth: sp.Spotify, display: bool) -> dict:
    """
    Retrieves current playback information, parses the json response, and optionally displays
    information about the current playback.
    """

    try:
        current_playback = sp_auth.current_playback()
        playback_items = current_playback["item"]
        playback = {}

        artists_str = get_artist_names(playback_items["album"])

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
    except TypeError:
        click.secho("Nothing is currently playing!", fg="red")


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
        raise ValueError("Invalid format. Proper format is MM:SS.")
    else:
        return total_ms


def convert_datetime(datetime_str: str) -> int:
    """
    Converts a string representation of a datetime (YYYYMMDD HH:MM) to milliseconds.
    """

    datetime_pattern = "%Y%m%d %H:%M"
    datetime_obj = datetime.strptime(datetime_str, datetime_pattern)
    unix_timestamp = time.mktime(datetime_obj.timetuple()) * 1000

    return int(unix_timestamp)


def truncate(name: str, length: int = 50) -> str:
    """
    Truncates a string and adds an elipsis if it exceeds the specified length. Otherwise, return the unmodified string.
    """
    if len(name) > length:
        name = name[0:length] + "..."

    return name
