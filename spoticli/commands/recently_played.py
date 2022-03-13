from typing import Any

import click
from click import Choice, IntRange
from spotipy.client import Spotify

from spoticli.types import CommaSeparatedIndexRange
from spoticli.util import (
    add_album_to_queue,
    display_table,
    get_index,
    play_or_queue,
    wait_display_playback,
)


def recently_played(sp_auth: Spotify, after: str, limit: int, device: str, user: str):
    """
    Displays information about recently played tracks.
    """
    recent_playback = sp_auth.current_user_recently_played(limit=limit, after=after)

    positions, recent_playback, track_uris = _parse_recent_playback(recent_playback)

    task = play_or_queue(create_playlist=True)
    if task == "cp":
        _create_playlist_from_recent_playback(sp_auth, user, positions, track_uris)
    else:
        index = get_index(IntRange(min=0, max=len(positions) - 1))
        item_type = click.prompt(
            "Track or associated album?",
            type=Choice(("t", "a"), case_sensitive=False),
            show_choices=True,
        )
        handler = RP_FUNC_DICT[task]
        handler(sp_auth, device, recent_playback, index, item_type)


def _handle_queue(sp_auth, device, recent_dict, index, item_type):
    if item_type == "t":
        sp_auth.add_to_queue(recent_dict["track_uri"][index], device_id=device)
        click.secho("Track successfully added to the queue.", fg="green")
    else:
        add_album_to_queue(sp_auth, recent_dict["album_uri"][index])


def _handle_play(sp_auth, device, recent_dict, index, item_type):
    if item_type == "t":
        sp_auth.start_playback(uris=[recent_dict["track_uri"][index]], device_id=device)
    else:
        sp_auth.start_playback(
            context_uri=recent_dict["album_uri"][index],
            device_id=device,
        )
    wait_display_playback(sp_auth)


RP_FUNC_DICT = {"q": _handle_queue, "p": _handle_play}


def _create_playlist_from_recent_playback(sp_auth, user, positions, track_uris):

    indices = click.prompt(
        "Enter the indices of the tracks to add to the playlist separated by commas",
        type=CommaSeparatedIndexRange([str(i) for i in positions]),
        show_choices=False,
    )
    playlist_name = click.prompt("Enter the playlist name")

    sp_auth.user_playlist_create(user=user, name=playlist_name)
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


def _parse_recent_playback(
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
