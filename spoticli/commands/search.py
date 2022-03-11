from typing import Any, Optional

import click
from click import Choice, IntRange
from spotipy.client import Spotify, SpotifyException

from spoticli.util import (
    Y_N_CHOICE_CASE_INSENSITIVE,
    add_album_to_queue,
    add_playlist_to_queue,
    convert_ms,
    display_table,
    get_artist_names,
    get_index,
    parse_artist_albums,
    parse_artist_top_tracks,
    play_content,
    play_or_queue,
    truncate,
    wait_display_playback,
)


def parse_album_search(res: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:

    items = res["albums"]["items"]
    uris = []
    results = []
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

    return results, uris


def album_search_process(
    sp_auth: Spotify,
    results: list[dict[str, Any]],
    uris: list[str],
    device: Optional[str] = None,
) -> None:

    index = get_index(IntRange(min=0, max=len(results) - 1))
    action = play_or_queue()
    if action == "p":
        sp_auth.start_playback(uris=[uris[index]], device_id=device)
        wait_display_playback(sp_auth, sleep_time=0.5)
    else:
        add_album_to_queue(sp_auth, uris[index], device=device)
        click.secho("Successfully added to queue!", fg="green")


def parse_artist_search(res: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    items = res["artists"]["items"]
    uris = []
    results = []
    for i, item in enumerate(items):
        results.append({"index": i, "artist": truncate(item["name"])})
        uris.append(item["uri"])

    return results, uris


def artist_search_process(
    sp_auth: Spotify,
    results: list[dict[str, Any]],
    uris: list[str],
    device: Optional[str] = None,
) -> None:
    index = get_index(IntRange(min=0, max=len(results) - 1))
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

    index = get_index(choices)
    p_or_q = play_or_queue()
    if p_or_q == "p":
        play_content(
            sp_auth=sp_auth,
            uri=uris[index],
            album_or_track=album_or_track,
            device_id=device,
        )
        wait_display_playback(sp_auth, sleep_time=0.5)
    elif album_or_track == "a":
        add_album_to_queue(sp_auth, uris[index], device=device)
    else:
        sp_auth.add_to_queue(uris[index], device_id=device)
        click.secho("Successfully added to queue!", fg="green")


def parse_playlist_search(
    res: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[str]]:
    items = res["playlists"]["items"]
    uris = []
    results = []
    for i, item in enumerate(items):
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

    return results, uris


def playlist_search_process(
    sp_auth: Spotify,
    results: list[dict[str, Any]],
    uris: list[str],
    device: Optional[str] = None,
) -> None:
    index = get_index(IntRange(min=0, max=len(results) - 1))
    action = play_or_queue()
    if action == "p":
        sp_auth.start_playback(uris=[uris[index]], device_id=device)
        wait_display_playback(sp_auth, sleep_time=0.5)
    confirmation = click.prompt(
        f"Are you sure you want to add all {results[index]['tracks']} tracks?",
        type=Y_N_CHOICE_CASE_INSENSITIVE,
        show_choices=True,
    )
    if confirmation == "y":
        add_playlist_to_queue(sp_auth, uris[index], device=device)
    else:
        click.secho("Operation aborted.", fg="red")


def parse_track_search(res: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    items = res["tracks"]["items"]
    uris = []
    results = []
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


def track_search_process(
    sp_auth: Spotify,
    results: list[dict[str, Any]],
    uris: list[str],
    device: Optional[str] = None,
) -> None:
    index = get_index(IntRange(min=0, max=len(results) - 1))
    action = play_or_queue()
    if action == "p":
        sp_auth.start_playback(uris=[uris[index]], device_id=device)
        wait_display_playback(sp_auth, sleep_time=0.5)
    else:
        sp_auth.add_to_queue(uris[index], device_id=device)
        click.secho("Track added to queue successfully!", fg="green")


SEARCH_FUNC_DICT = {
    "album": (parse_album_search, album_search_process),
    "artist": (parse_artist_search, artist_search_process),
    "playlist": (parse_playlist_search, playlist_search_process),
    "track": (parse_track_search, track_search_process),
}


def search(sp_auth: Spotify, query: str, type_: str, device: str):
    """
    Queries Spotify's databases.
    """
    try:
        search_res = sp_auth.search(q=query, limit=10, type=type_)
    except SpotifyException as e:
        click.secho(str(e), fg="red")
    except AttributeError:
        pass
    parse_func, process_func = SEARCH_FUNC_DICT[type_]
    results, uris = parse_func(search_res)
    display_table(results)
    process_func(sp_auth, results, uris, device=device)
