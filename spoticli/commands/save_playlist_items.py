from typing import Any, Tuple

import click
from spotipy.client import Spotify

from spoticli.types import CommaSeparatedIndices
from spoticli.util import (
    Y_N_CHOICE_CASE_INSENSITIVE,
    display_table,
    get_artist_names,
    truncate,
)

FIELDS = (
    "items(track(album(album_type,artists(name),name,total_tracks,uri,release_date)))"
)


def save_playlist_items(sp_auth: Spotify, url: str) -> None:

    click.secho("Retrieving all albums and EPs from the playlist...", fg="magenta")
    unsaved_items, uris = _parse_playlist_items(sp_auth, url)
    display_table(unsaved_items)
    _handle_prompts(sp_auth, uris)
    click.secho("Albums successfully added to user library!", fg="green")


def _handle_prompts(sp_auth: Spotify, uris: list[str]) -> None:
    add_all_albums = click.prompt(
        "Add all albums to user library?",
        type=Y_N_CHOICE_CASE_INSENSITIVE,
        show_choices=True,
    )
    if add_all_albums == "y":
        sp_auth.current_user_saved_albums_add(albums=uris)
    else:
        album_selection = click.prompt(
            "Enter the indices of albums to add (separated by a comma)",
            type=CommaSeparatedIndices([str(i) for i in range(len(uris))]),
            show_choices=False,
        )
        album_sublist = [uris[i] for i in album_selection]
        sp_auth.current_user_saved_albums_add(albums=album_sublist)


def _parse_playlist_items(
    sp_auth: Spotify, url: str
) -> Tuple[list[dict[str, Any]], list[str]]:
    playlist_items = sp_auth.playlist_items(playlist_id=url, fields=FIELDS)
    uris = []
    album_items = []
    for item in playlist_items["items"]:
        item_album = item["track"]["album"]
        if any(
            (
                all(
                    (
                        item_album["total_tracks"] > 1,
                        item_album["album_type"] == "single",
                    )
                ),
                item_album["album_type"] == "album",
            )
        ):
            album_items.append(item_album)
            uris.append(item_album["uri"])
    is_item_saved = sp_auth.current_user_saved_albums_contains(albums=uris)
    items_with_status = list(zip(album_items, is_item_saved))
    uris_with_status = list(zip(uris, is_item_saved))
    unsaved_uris = [uri for uri, status in uris_with_status if not status]
    unsaved_items = [item for item, status in items_with_status if not status]
    indices_items = list(enumerate(unsaved_items))

    return [
        {
            "index": idx,
            "artists": truncate(get_artist_names(item), 40),
            "album": truncate(item["name"], 40),
            "album_type": "EP" if item["album_type"] == "single" else "album",
            "total_tracks": item["total_tracks"],
            "release_date": item["release_date"],
        }
        for idx, item in indices_items
    ], unsaved_uris
