import time
from datetime import datetime
from time import sleep
from typing import Any

import click
from click.termui import style
from click.types import Choice
from spotipy.client import Spotify
from tabulate import tabulate
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


def add_album_to_queue(sp_auth: Spotify, uri: str) -> None:
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


def get_artist_names(res: dict[str, Any]) -> str:
    """
    Retrieves all artist names for a given input to the "album" key of a response.
    """

    artists = []
    for artist in res["artists"]:
        artists.append(artist["name"])
    artists_str = ", ".join(artists)

    return artists_str


def get_current_playback(res: dict[str, Any], display: bool) -> dict:
    """
    Retrieves current playback information, parses the json response, and optionally displays
    information about the current playback.
    """

    try:
        playback_items = res["item"]
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
        playback["volume"] = res["device"]["volume_percent"]
        playback["shuffle_state"] = res["shuffle_state"]

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
    except TypeError:
        click.secho("Nothing is currently playing!", fg="red")

    return playback


def search_parse(res: dict[str, Any], k: str) -> tuple[list[dict[str, Any]], list[str]]:

    items = res[k]["items"]
    uris = []
    results = []
    if k == "albums":
        for i, item in enumerate(items):
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
        results = []
        for i, item in enumerate(items):
            results.append({"index": i, "artist": item["name"]})
            uris.append(item["uri"])
    elif k == "playlists":
        results = []
        for i, item in enumerate(items):
            desc = item["description"]
            uris.append(item["uri"])
            results.append(
                {
                    "index": i,
                    "name": item["name"],
                    "creator": item["owner"]["display_name"],
                    "description": truncate(desc),
                    "tracks": item["tracks"]["total"],
                }
            )
    elif k == "tracks":
        results = []
        uris = []
        for i, item in enumerate(items):
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
    sp_auth: Spotify, type_: str, results: list[dict[str, Any]], uris: list[str]
) -> None:

    click.secho(tabulate(results, headers="keys", tablefmt="github"))
    proceed = click.prompt(
        "Do you want to proceed with one of these items?",
        type=Choice(("y", "n"), case_sensitive=False),
        show_choices=True,
    )
    if proceed == "y":
        choices = (str(num) for num in range(len(results)))
        index = click.prompt(
            "Enter the index",
            type=Choice(choices),  # type: ignore
            show_choices=False,
        )
        index = int(index)

        if type_ != "artist":
            action = click.prompt(
                "Play now or add to queue?",
                type=Choice(("p", "q"), case_sensitive=False),
                show_choices=True,
            )
            if action == "p":
                sp_auth.start_playback(uris=[uris[index]])
                sleep(0.5)
                get_current_playback(sp_auth, display=True)
            else:
                if type_ == "album":
                    add_album_to_queue(sp_auth, uris[index])
                elif type_ == "playlist":
                    confirmation = click.prompt(
                        f"Are you sure you want to add all {results[index]['tracks']} tracks?",
                        type=Choice(("y", "n"), case_sensitive=False),
                        show_choices=True,
                    )
                    if confirmation == "y":
                        add_playlist_to_queue(sp_auth, uris[index])
                    else:
                        click.secho("Operation aborted.", fg="red")
                elif type_ == "track":
                    sp_auth.add_to_queue(uris[index])
                    click.secho("Track added to queue successfully!", fg="green")
        elif type_ == "artist":
            album_or_track = click.prompt(
                "View artist albums or most popular tracks?",
                type=Choice(("a", "t"), case_sensitive=False),
                show_choices=True,
            )
            if album_or_track == "a":
                artist_albums_res = sp_auth.artist_albums(
                    uris[index], album_type="album,single"
                )
                albums = []
                uris = []
                for i, item in enumerate(artist_albums_res["items"]):
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

                click.echo(tabulate(albums, headers="keys", tablefmt="github"))
            else:
                artist_tracks_res = sp_auth.artist_top_tracks(uris[index])
                top_tracks = []
                uris = []
                for i, track in enumerate(artist_tracks_res["tracks"]):
                    top_tracks.append(
                        {
                            "index": i,
                            "name": track["name"],
                            "artists": get_artist_names(track["album"]),
                            "popularity": track["popularity"],
                        }
                    )
                    uris.append(track["uri"])
                click.echo(tabulate(top_tracks, headers="keys", tablefmt="github"))

            further_action = click.prompt(
                "Do you want to take further action?",
                type=Choice(("y", "n"), case_sensitive=False),
                show_choices=True,
            )
            if further_action == "y":
                choices = (str(num) for num in range(len(top_tracks)))
                index = click.prompt(
                    "Enter the index",
                    type=Choice(choices),  # type: ignore
                    show_choices=False,
                )
                index = int(index)
                play_or_queue = click.prompt(
                    "Play now or add to queue?",
                    type=Choice(("p", "q"), case_sensitive=False),
                    show_choices=True,
                )
                if play_or_queue == "p":
                    sp_auth.start_playback(uris=[uris[index]])
                    sleep(0.5)
                    get_current_playback(sp_auth, display=True)
                else:
                    if album_or_track == "a":
                        add_album_to_queue(sp_auth, uris[index])
                    else:
                        sp_auth.add_to_queue(uris[index])

                    click.secho("Successfully added to queue!", fg="green")


def convert_ms(duration_ms: int) -> str:
    """
    Converts milliseconds to a string representation of a timestamp (MM:SS).
    """

    minutes, seconds = divmod(duration_ms / 1000, 60)
    rounded_seconds = int(round(seconds, 0))

    if rounded_seconds - 10 < 0:
        rounded_seconds = "0" + str(rounded_seconds)  # type: ignore

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
