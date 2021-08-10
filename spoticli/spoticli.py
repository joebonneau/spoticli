import random
import os

import spotipy as sp
from spotipy.oauth2 import SpotifyOAuth
import click
from click.termui import style
from tabulate import tabulate
from pprint import pprint

from spoticli.util import convert_timestamp, get_current_playback


SPOTIFY_USER_ID = os.environ.get("SPOTIFY_USER_ID")
SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.environ.get("SPOTIFY_REDIRECT_URI")

states = [
    "user-modify-playback-state",
    "user-read-playback-state",
    "user-library-read",
    "playlist-read-private",
    "playlist-read-collaborative",
    "playlist-modify-public",
    "playlist-modify-private",
    "user-read-recently-played",
]

STATE_STR = " ".join(states)


@click.group()
@click.pass_context
def main(
    ctx,
    scope: str = STATE_STR,
    client_id: str = SPOTIFY_CLIENT_ID,
    client_secret: str = SPOTIFY_CLIENT_SECRET,
    redirect_uri: str = SPOTIFY_REDIRECT_URI,
):

    try:
        auth = sp.Spotify(
            auth_manager=SpotifyOAuth(
                scope=scope,
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
            )
        )

        ctx.obj = auth
    except:
        click.secho(
            "API authorization failed! Did you remember to set the environment variables?",
            fg="red",
        )


@main.command("prev")
@click.pass_obj
def previous_track(ctx):
    sp_auth = ctx
    sp_auth.previous_track()

    get_current_playback(sp_auth=sp_auth, display=True)


@main.command("next")
@click.pass_obj
def next_track(ctx):
    sp_auth = ctx
    sp_auth.next_track()

    get_current_playback(sp_auth=sp_auth, display=True)


@main.command("pause")
@click.pass_obj
def pause_playback(ctx):
    sp_auth = ctx
    sp_auth.pause_playback()

    click.secho("Playback paused.")


@main.command("play")
@click.pass_obj
def start_playback(ctx):
    sp_auth = ctx
    sp_auth.start_playback()

    click.secho("Playback resumed.")
    get_current_playback(sp_auth=sp_auth, display=True)


@main.command("cp")
@click.option("-pub/-pri", "--public/--private", default=True)
@click.option("-c/-i", "--collaborative/--individual", default=False)
@click.option("-d", "--description", type=str, default="")
@click.argument("name", nargs=-1, required=True)
@click.pass_obj
def create_playlist(ctx, public, collaborative, description, name):

    sp_auth = ctx

    concat_name = " ".join(name)

    if public == True and collaborative == True:
        click.secho(style("Collaborative playlists can only be private.", fg="red"))
    else:
        sp_auth.user_playlist_create(
            user=SPOTIFY_USER_ID,
            name=concat_name,
            public=public,
            collaborative=collaborative,
            description=description,
        )

        click.secho(
            style(f"Playlist '{concat_name}' created successfully!", fg="green")
        )


@main.command("seek")
@click.argument("timestamp", required=True)
@click.pass_obj
def seek(ctx, timestamp):

    sp_auth = ctx

    try:
        timestamp_in_ms = convert_timestamp(timestamp)
        sp_auth.seek_track(timestamp_in_ms)
    except:
        click.secho(
            style("Incorrect format: must be in minutes:seconds format", fg="red")
        )


@main.command("vol")
@click.option("-u/-d", "--up/--down", required=True)
@click.pass_obj
def volume(ctx, up):

    sp_auth = ctx
    playback_info = get_current_playback(sp_auth=sp_auth, display=False)
    previous_volume = playback_info["volume"]

    if up:
        new_volume = int(round(previous_volume + 10, 0))
    else:
        new_volume = int(round(previous_volume - 10, 0))

    if new_volume > 100:
        new_volume = 100
    elif new_volume < 0:
        new_volume = 0

    if not previous_volume == 100:
        sp_auth.volume(new_volume)

    click.secho(f"Current volume: {new_volume}")


@main.command("np")
@click.option("-v", "--verbose", is_flag=True)
@click.pass_obj
def now_playing(ctx, verbose):

    sp_auth = ctx
    playback = get_current_playback(sp_auth=sp_auth, display=True)

    if verbose:
        audio_features = sp_auth.audio_features(playback["track_uri"])
        click.secho(style("Estimates:", underline=True))
        click.echo(f"BPM: {audio_features[0]['tempo']}")
        click.echo(f"Time signature: 4/{audio_features[0]['time_signature']}")


@main.command("shuffle")
@click.option("-on/-off", default=True)
@click.pass_obj
def toggle_shuffle(ctx, on):

    sp_auth = ctx

    if on:
        sp_auth.shuffle(state=True)
        click.echo(f"Shuffle toggled {style('on', fg='green')}.")

    else:
        sp_auth.shuffle(state=False)
        click.echo(f"Shuffle toggled {style('off', fg='red')}.")


@main.command("prsa")
@click.pass_obj
def play_random_saved_album(ctx):

    # Only 50 albums can be retrieved at a time, so make as many requests as necessary to retrieve
    # all in library.
    sp_auth = ctx
    click.secho("This might take a few seconds...", fg="yellow")
    saved_albums = []
    offset = 0
    while True:
        albums_res = sp_auth.current_user_saved_albums(limit=50, offset=offset)
        albums = albums_res["items"]
        for album in albums:
            artists = []
            artists_res = album["album"]["artists"]
            for artist in artists_res:
                artists.append(artist["name"])

            saved_albums.append(
                {
                    "album_uri": album["album"]["uri"],
                    "artists": ", ".join(artists),
                    "album": album["album"]["name"],
                }
            )
        if len(albums) < 50:
            break
        else:
            offset += 50

    # Pick a random index that corresponds to an album URI
    rand_i = random.randint(0, len(saved_albums))

    while True:
        album = saved_albums[rand_i]["album"]
        artists = saved_albums[rand_i]["artists"]
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
            for track in tracks:
                sp_auth.add_to_queue(track["uri"])
            break
        else:
            sp_auth.start_playback(context_uri=saved_albums[rand_i]["album_uri"])
            break


@main.command("actp")
@click.pass_obj
def add_current_track_to_playlists(ctx):

    sp_auth = ctx

    try:
        playback = get_current_playback(sp_auth=sp_auth, display=True)

        playlist_res = sp_auth.current_user_playlists(limit=20)
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
            except:
                click.secho(
                    f"There was an issue adding the track to all specified playlists."
                )
    except TypeError:
        click.secho("Nothing is currently playing!", fg="red")


@main.command("rp")
@click.pass_obj
def recently_played(ctx):

    sp_auth = ctx
    recent_playback = sp_auth.current_user_recently_played(limit=25)

    positions = []
    track_names = []
    track_uris = []
    album_names = []
    album_uris = []
    album_types = []
    timestamps = []
    playback_items = recent_playback["items"]
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
    display_dict = dict(
        (k, recent_dict[k])
        for k in ("index", "track_name", "album_type", "album_name", "timestamp")
    )
    click.echo(tabulate(display_dict, headers="keys", tablefmt="github"))

    while True:
        action = click.prompt("Take further action? (y/n)")
        if action.lower() in ("y", "n"):
            if action.lower() == "y":
                while True:
                    index = click.prompt("Enter the index of the track/album")
                    try:
                        index = int(index)
                        if index in range(len(positions)):
                            while True:
                                item_type = click.prompt(
                                    "Track or associated album? (t/a)"
                                )
                                if item_type.lower() in ("t", "a"):
                                    while True:
                                        action_type = click.prompt(
                                            "Add to queue or play now? (q/p)"
                                        )
                                        if action_type.lower() in ("q", "p"):
                                            break
                                        else:
                                            click.secho(
                                                style(
                                                    f"{action_type} is not a valid input!",
                                                    fg="red",
                                                )
                                            )
                                    break
                                else:
                                    click.secho(
                                        style(
                                            f"{item_type} is not a valid input!",
                                            fg="red",
                                        )
                                    )
                        else:
                            click.secho(
                                style(f"{index} is not a valid input!", fg="red")
                            )
                    except:
                        click.secho(style(f"{index} is not a valid input!", fg="red"))

                    if action_type.lower() == "q":
                        if item_type == "t":
                            sp_auth.add_to_queue(recent_dict["track_uri"][i])
                        else:
                            tracks_res = sp_auth.album_tracks(
                                recent_dict["album_uri"][index], limit=50
                            )
                            tracks = tracks_res["items"]
                            for track in tracks:
                                sp_auth.add_to_queue(track[index]["uri"])
                            break
                    else:
                        if item_type == "t":
                            sp_auth.start_playback(
                                uris=[recent_dict["track_uri"][index]]
                            )
                            break
                        else:
                            sp_auth.start_playback(
                                context_uri=recent_dict["album_uri"][index]
                            )
                        break
            else:
                break
        else:
            click.secho(style(f"{action} is not a valid input!", fg="red"))


# TODO: recently_played, smart searching
