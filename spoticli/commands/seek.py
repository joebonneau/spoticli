import click
from spotipy.client import Spotify


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


def seek(sp_auth: Spotify, timestamp: str, device: str):
    """
    Seeks the track to the timestamp specified.

    Timestamp format is MM:SS
    """

    try:
        timestamp_in_ms = convert_timestamp(timestamp)
    except ValueError as e:
        click.secho(str(e), fg="red")

    sp_auth.seek_track(timestamp_in_ms, device_id=device)
