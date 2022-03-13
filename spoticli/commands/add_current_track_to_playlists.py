from typing import Any, Tuple

import click
from click import style
from spotipy.client import Spotify

from spoticli.types import CommaSeparatedIndices
from spoticli.util import display_table, get_current_playback


def add_current_track_to_playlists(sp_auth: Spotify):
    """
    Adds the current track in playback to one or more playlist(s).
    """

    current_playback = sp_auth.current_playback()
    playback = get_current_playback(res=current_playback, display=True)
    playlist_res = sp_auth.current_user_playlists(limit=20)
    positions, playlist_names, playlist_dict = _parse_user_playlists(playlist_res)
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
            sp_auth.playlist_add_items(
                playlist_id=playlist_dict["playlist_ids"][index],
                items=[track_uri],
            )
        track_name = style(playback["track_name"], fg="magenta")
        rest_of_the_msg = style(
            "was successfully added to all specified playlists!", fg="green"
        )
        click.echo(f"{track_name} {rest_of_the_msg}")


def _parse_user_playlists(
    playlist_res: list[dict[str, Any]],
) -> Tuple[list[int], list[str], dict[str, Any]]:

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

    return positions, playlist_names, playlist_dict
