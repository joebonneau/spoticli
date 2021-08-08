import random
import os

import spotipy as sp
import click
from click.termui import style
from tabulate import tabulate

from spoticli.util import convert_duration, connect, get_current_playback


SPOTIFY_USER_ID = os.environ.get("SPOTIFY_USER_ID")

USER_MODIFY_PLAYBACK_STATE = "user-modify-playback-state"

states = [
    "user-modify-playback-state",
    "user-library-read",
    "playlist-read-private",
    "playlist-read-collaborative",
    "playlist-modify-public",
    "playlist-modify-private",
]

STATE_STR = " ".join(states)


@click.group()
def main():
    pass
    # TODO: Figure out how to check whether a valid token exists and connect if not


@main.command()
def play_random_saved_album():

    # Only 50 albums can be retrieved at a time, so make as many requests as necessary to retrieve
    # all in library.
    sp_auth = connect(scope="user-library-read user-modify-playback-state")

    click.secho("This might take a few seconds...", fg="yellow")
    saved_albums = []
    offset = 0
    while True:
        albums_res = sp_auth.current_user_saved_albums(limit=50, offset=offset)
        albums = albums_res["items"]
        for i in range(len(albums)):
            artists = []
            for j in range(len(albums_res["items"][i]["album"]["artists"])):
                artists.append(albums_res["items"][i]["album"]["artists"][j]["name"])

            saved_albums.append(
                {
                    "album_uri": albums_res["items"][i]["album"]["uri"],
                    "artists": ", ".join(artists),
                    "album": albums_res["items"][i]["album"]["name"],
                }
            )
        if len(albums) < 50:
            break
        else:
            offset += 50

    # Pick a random index that corresponds to an album URI
    rand_i = random.randint(0, len(saved_albums))

    while True:
        album = saved_albums[rand_i].get("album")
        artists = saved_albums[rand_i].get("artists")
        click.echo(
            f"Selected album: {style(album, fg='blue')} by {style(artists, fg='green')}."
        )
        new_album = click.prompt("Select a different random album? (y/n)")
        if new_album.lower() not in ["y", "n"]:
            click.secho("Invalid input!", fg="red")
        elif new_album.lower() == "y":
            # Pick a random index that corresponds to an album URI
            rand_i = random.randint(0, len(saved_albums))
        elif new_album.lower() == "n":
            break

    while True:
        queue = click.prompt("Play album now (p) or add to queue (q)?")
        if queue.lower() not in ["p", "q"]:
            click.secho("Invalid input!", fg="red")
        elif queue.lower() == "q":
            tracks_res = sp_auth.album_tracks(
                saved_albums[rand_i]["album_uri"], limit=50
            )
            tracks = tracks_res["items"]
            for i in range(len(tracks)):
                sp_auth.add_to_queue(tracks_res["items"][i]["uri"])
            break
        else:
            sp_auth.start_playback(context_uri=saved_albums[rand_i]["album_uri"])
            break


@main.command()
def add_current_track_to_playlists():

    sp_auth = connect(
        scope="user-read-playback-state playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private"
    )

    try:
        playback = get_current_playback(display=True)

        playlist_res = sp_auth.current_user_playlists(limit=20)
        positions = []
        playlist_names = []
        playlist_ids = []
        for i in range(len(playlist_res["items"])):
            positions.append(i)
            playlist_names.append(playlist_res["items"][i]["name"])
            playlist_ids.append(playlist_res["items"][i]["uri"])

        playlist_dict = {
            "index": positions,
            "playlist_names": playlist_names,
            "playlist_ids": playlist_ids,
        }
        display_dict = {"index": positions, "playlist_names": playlist_names}
        click.echo(tabulate(display_dict, headers="keys", tablefmt="github"))

        while True:
            indices = click.prompt(
                "Enter the indices of the playlists to add the track to separated by commas."
            )

            try:
                indices_int = list(map(int, indices.split(",")))

                for index in indices_int:
                    sp_auth.user_playlist_add_tracks(
                        user=SPOTIFY_USER_ID,
                        playlist_id=playlist_dict["playlist_ids"][index],
                        tracks=[playback["track_uri"]],
                    )

                click.secho(
                    f"The track was successfully added to all specified playlists!"
                )
                break
            except ValueError:
                click.secho(f"Invalid input! Try again.", fg="red")
            # except:
            #     click.secho(
            #         f"There was an issue adding the track to all specified playlists."
            #     )
    except TypeError:
        click.secho("Nothing is currently playing!", fg="red")


@main.command("prev")
def previous_track():
    sp_auth = connect(scope=USER_MODIFY_PLAYBACK_STATE)
    sp_auth.previous_track()

    get_current_playback(display=True)


@main.command("next")
def next_track():
    sp_auth = connect(scope=USER_MODIFY_PLAYBACK_STATE)
    sp_auth.next_track()

    get_current_playback(display=True)


@main.command("pause")
def pause_playback():
    sp_auth = connect(scope=USER_MODIFY_PLAYBACK_STATE)
    sp_auth.pause_playback()

    click.secho("Playback paused.")


@main.command("play")
def start_playback():
    sp_auth = connect(scope=USER_MODIFY_PLAYBACK_STATE)
    sp_auth.start_playback()

    click.secho("Playback resumed.")
    get_current_playback(display=True)


@main.command("vol")
@click.option("-u/-d", "--up/--down", required=True)
def volume(up):

    sp_auth = connect(scope=USER_MODIFY_PLAYBACK_STATE)
    playback_info = get_current_playback(display=False)

    if up:
        previous_volume = playback_info["volume"]
        new_volume = int(round(previous_volume + 10, 0))
    else:
        previous_volume = playback_info["volume"]
        new_volume = int(round(previous_volume - 10, 0))

    if new_volume > 100:
        new_volume = 100
    elif new_volume < 0:
        new_volume = 0

    sp_auth.volume(new_volume)

    click.secho(f"Current volume: {new_volume}")


@main.command("np")
# @click.option("-v", "--verbose")
def now_playing():

    get_current_playback(display=True)

    # TODO: add verbose option to display audio features


@main.command("shuffle")
@click.option("-on/-off", default=True)
def toggle_shuffle(on):

    sp_auth = connect(scope=USER_MODIFY_PLAYBACK_STATE)

    if on:
        sp_auth.shuffle(state=True)
        click.echo(f"Shuffle toggled {style('on', fg='green')}.")

    else:
        sp_auth.shuffle(state=False)
        click.echo(f"Shuffle toggled {style('off', fg='red')}.")


# TODO: add currently_playing (with more info),
# TODO: recently_played, smart searching, shuffle
