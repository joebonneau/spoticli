from typing import Iterable, Dict, Any
import os

import spotipy as sp
import click
from click.termui import style


def add_playlist_to_queue(sp_auth, uri: str) -> None:

    offset = 0
    click.secho("Adding playlist tracks to queue...", fg="magenta")
    while True:
        playlists_res = sp_auth.playlist_items(
            uri, limit=100, fields="items.track.uri", offset=offset
        )
        for item in playlists_res["items"]:
            sp_auth.add_to_queue(item["track"]["uri"])
        if len(playlists_res) < 100:
            break

        offset += 100

    click.secho("All playlist tracks added successfully!", fg="green")


def add_album_to_queue(sp_auth: sp.Spotify, uri: str) -> None:

    while True:
        tracks_res = sp_auth.album_tracks(uri, limit=50, offset=0)
        tracks = tracks_res["items"]
        for track in tracks:
            sp_auth.add_to_queue(track["uri"])
        if len(tracks) < 50:
            break


def get_artist_names(res: Dict[str, Any]) -> str:

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

    current_playback = sp_auth.current_playback()
    playback_items = current_playback["item"]
    playback = {}

    artists_str = get_artist_names(playback_items)

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


def truncate(name: str, length: int) -> str:
    """
    Truncates a string and adds an elipsis if it exceeds the specified length. Otherwise, return the unmodified string.
    """
    if len(name) > length:
        name = name[0:length] + "..."

    return name
