import random
import os
from time import sleep
from pprint import pprint

import spotipy as sp
from spotipy.oauth2 import SpotifyOAuth, SpotifyOauthError
from spotipy.client import SpotifyException

import click
from click.types import Choice
from click.termui import style

from tabulate import tabulate

from spoticli.util import (
    convert_datetime,
    convert_timestamp,
    convert_ms,
    get_artist_names,
    get_current_playback,
    truncate,
    add_album_to_queue,
    add_playlist_to_queue,
)


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

device_error_message = " Try pressing play on the device that you want to control."


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
    except (SpotifyException, SpotifyOauthError) as e:
        # Spotipy uses SPOTIPY in its environment variables which might be confusing for user.
        message = str(e).replace("SPOTIPY", "SPOTIFY")
        click.secho(
            f"API authorization failed!\nError: {message}",
            fg="red",
        )


@main.command("prev")
@click.pass_obj
def previous_track(ctx):
    """
    Skips playback to the track played previous to the current track.
    """
    sp_auth = ctx

    try:
        sp_auth.previous_track()
        # delay to prevent fetching current playback before it updates on server side.
        sleep(0.1)
        get_current_playback(sp_auth=sp_auth, display=True)
    except AttributeError:
        # AttributeError is thrown if authorization was unsuccessful, so show that error instead.
        pass
    except SpotifyException as e:
        click.secho(str(e) + device_error_message, fg="red")


@main.command("next")
@click.pass_obj
def next_track(ctx):
    """
    Skips playback to the next track in the queue.
    """
    sp_auth = ctx

    try:
        sp_auth.next_track()
        # delay to prevent fetching current playback before it updates on server side.
        sleep(0.1)
        get_current_playback(sp_auth=sp_auth, display=True)
    except AttributeError:
        # AttributeError is thrown if authorization was unsuccessful, so show that error instead.
        pass
    except SpotifyException as e:
        click.secho(str(e) + device_error_message, fg="red")


@main.command("pause")
@click.pass_obj
def pause_playback(ctx):
    """
    Pauses playback.
    """
    sp_auth = ctx

    try:
        sp_auth.pause_playback()

        click.secho("Playback paused.")
    except AttributeError:
        # AttributeError is thrown if authorization was unsuccessful, so show that error instead.
        pass
    except SpotifyException as e:
        click.secho(str(e) + device_error_message, fg="red")


@main.command("play")
@click.pass_obj
def start_playback(ctx):
    """
    Resumes playback on the active track.
    """
    sp_auth = ctx

    try:
        sp_auth.start_playback()

        click.secho("Playback resumed.")
        get_current_playback(sp_auth=sp_auth, display=True)
    except AttributeError:
        # AttributeError is thrown if authorization was unsuccessful, so show that error instead.
        pass
    except SpotifyException as e:
        click.secho(str(e) + device_error_message, fg="red")


@main.command("cp")
@click.option("-pub/-pri", default=True, help="public or private")
@click.option(
    "-c/-i",
    default=False,
    help="collaborative or non-collaborative",
)
@click.option("-d", type=str, default="", help="playlist description")
@click.argument("name", nargs=-1, required=True)
@click.pass_obj
def create_playlist(ctx, public, collaborative, description, name):
    """
    Creates a new playlist.
    """

    sp_auth = ctx

    concat_name = " ".join(name)

    if public == True and collaborative == True:
        click.secho(style("Collaborative playlists can only be private.", fg="red"))
    else:
        try:
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
        except AttributeError:
            # AttributeError is thrown if authorization was unsuccessful, so show that error instead.
            pass
        except SpotifyException as e:
            click.secho(str(e) + device_error_message, fg="red")


@main.command("seek")
@click.argument("timestamp", required=True)
@click.pass_obj
def seek(ctx, timestamp):
    """
    Seeks the track to the timestamp specified.

    TIMESTAMP format is MM:SS
    """

    sp_auth = ctx

    try:
        timestamp_in_ms = convert_timestamp(timestamp)
        sp_auth.seek_track(timestamp_in_ms)
    except AttributeError:
        # AttributeError is thrown if authorization was unsuccessful, so show that error instead.
        pass
    except SpotifyException as e:
        click.secho(str(e) + device_error_message, fg="red")
    except:
        click.secho(
            style("Incorrect format: must be in minutes:seconds format", fg="red")
        )


@main.command("volup")
@click.argument("amount", default=10)
@click.pass_obj
def increase_volume(ctx, amount):
    """
    Increases volume by the increment specified (defaults to 10%).
    """

    sp_auth = ctx

    try:
        playback_info = get_current_playback(sp_auth=sp_auth, display=False)
        previous_volume = playback_info["volume"]

        new_volume = int(round(previous_volume + amount, 0))
        if new_volume > 100:
            new_volume = 100

        sp_auth.volume(new_volume)
        click.secho(f"New volume: {new_volume}")
    except AttributeError:
        # AttributeError is thrown if authorization was unsuccessful, so show that error instead.
        pass
    except SpotifyException as e:
        click.secho(str(e) + device_error_message, fg="red")


@main.command("voldown")
@click.argument("amount", default=10)
@click.pass_obj
def decrease_volume(ctx, amount):
    """
    Decreases volume by the increment specified (defaults to 10%).
    """

    sp_auth = ctx

    try:
        playback_info = get_current_playback(sp_auth=sp_auth, display=False)
        previous_volume = playback_info["volume"]

        new_volume = int(round(previous_volume - amount, 0))
        if new_volume < 0:
            new_volume = 0

        sp_auth.volume(new_volume)
        click.secho(f"New volume: {new_volume}")
    except AttributeError:
        # AttributeError is thrown if authorization was unsuccessful, so show that error instead.
        pass
    except SpotifyException as e:
        click.secho(str(e) + device_error_message, fg="red")


@main.command("now")
@click.option("-v", "--verbose", is_flag=True, help="displays additional info")
@click.pass_obj
def now_playing(ctx, verbose):
    """
    Displays info about the current playback.
    """

    sp_auth = ctx

    try:
        playback = get_current_playback(sp_auth=sp_auth, display=True)

        if verbose:
            audio_features = sp_auth.audio_features(playback["track_uri"])
            click.secho(style("Estimates:", underline=True))
            click.echo(f"BPM: {audio_features[0]['tempo']}")
            click.echo(f"Time signature: 4/{audio_features[0]['time_signature']}")
    except AttributeError:
        # AttributeError is thrown if authorization was unsuccessful, so show that error instead.
        pass
    except SpotifyException as e:
        click.secho(str(e) + device_error_message, fg="red")


@main.command("shuffle")
@click.option("-on/-off", required=True, is_flag=True)
@click.pass_obj
def toggle_shuffle(ctx, on):
    """
    Toggles shuffling on or off.
    """

    sp_auth = ctx

    try:
        if on:
            sp_auth.shuffle(state=True)
            click.echo(f"Shuffle toggled {style('on', fg='green')}.")

        else:
            sp_auth.shuffle(state=False)
            click.echo(f"Shuffle toggled {style('off', fg='red')}.")
    except AttributeError:
        # AttributeError is thrown if authorization was unsuccessful, so show that error instead.
        pass
    except SpotifyException as e:
        click.secho(str(e) + device_error_message, fg="red")


@main.command("prsa")
@click.pass_obj
def play_random_saved_album(ctx):
    """
    Fetches all albums in user library and selects one randomly.
    """

    # Only 50 albums can be retrieved at a time, so make as many requests as necessary to retrieve
    # all in library.
    sp_auth = ctx

    try:
        saved_albums = []
        offset = 0
        while True:
            albums_res = sp_auth.current_user_saved_albums(limit=50, offset=offset)
            if offset == 0:
                click.secho(
                    "Retrieving saved albums. This may take a few moments...",
                    fg="magenta",
                )
            albums = albums_res["items"]
            for album in albums:
                saved_albums.append(
                    {
                        "album_uri": album["album"]["uri"],
                        "artists": get_artist_names(album["album"]),
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
            new_album = click.prompt(
                "Select this album?",
                type=Choice(("y", "n"), case_sensitive=False),
                show_choices=True,
            )
            if new_album == "n":
                # Pick a random index that corresponds to an album URI
                rand_i = random.randint(0, len(saved_albums))
            else:
                break

        while True:
            queue = click.prompt(
                "Play album now or add to queue?",
                type=Choice(("p", "q"), case_sensitive=False),
                show_choices=True,
            )
            if queue == "q":
                add_album_to_queue(sp_auth, saved_albums[rand_i]["album_uri"])
                break
            else:
                sp_auth.start_playback(context_uri=saved_albums[rand_i]["album_uri"])
                sleep(0.5)
                get_current_playback(sp_auth, display=True)
                break
    except AttributeError:
        # AttributeError is thrown if authorization was unsuccessful, so show that error instead.
        pass
    except SpotifyException as e:
        click.secho(str(e) + device_error_message, fg="red")


@main.command("actp")
@click.pass_obj
def add_current_track_to_playlists(ctx):
    """
    Adds the current track in playback to one or more playlist(s).
    """

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
    except AttributeError:
        # AttributeError is thrown if authorization was unsuccessful, so show that error instead.
        pass
    except SpotifyException as e:
        click.secho(str(e) + device_error_message, fg="red")


@main.command("recent")
@click.option("-a", "--after", default=None, help="YYYYMMDD MM:SS")
@click.pass_obj
def recently_played(ctx, after):
    """
    Displays information about recently played tracks.
    """

    sp_auth = ctx

    try:
        if after:
            recent_playback = sp_auth.current_user_recently_played(
                limit=25, after=convert_datetime(after)
            )
        else:
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
            action = click.prompt(
                "Take further action?",
                type=Choice(("y", "n"), case_sensitive=False),
                show_choices=True,
            )
            if action == "y":
                task = click.prompt(
                    "Play now, add to queue, or create playlist?",
                    type=Choice(("p", "q", "cp"), case_sensitive=False),
                    show_choices=True,
                )
                if task == "cp":
                    while True:
                        indices = click.prompt(
                            "Enter the range of indices (comma separated) you want to include in the playlist"
                        )
                        index_list = indices.split(",")
                        if len(index_list) == 2:
                            try:
                                index_list = [int(i) for i in index_list]
                                playlist_name = click.prompt("Enter the playlist name")
                                sp_auth.user_playlist_create(
                                    user=SPOTIFY_USER_ID, name=playlist_name
                                )
                                playlist_res = sp_auth.current_user_playlists(limit=1)
                                playlist_uri = playlist_res["items"][0]["uri"]
                                sp_auth.playlist_add_items(
                                    playlist_uri,
                                    track_uris[index_list[0] : index_list[1] + 1],
                                )
                                click.secho(
                                    f"Playlist {playlist_name} created successfully!",
                                    fg="green",
                                )
                                break
                            except:
                                click.secho(
                                    "Invalid input. Correct format is '0, 15'", fg="red"
                                )
                        else:
                            click.secho(
                                "Invalid input. Correct format is '0, 15'", fg="red"
                            )
                else:
                    index = click.prompt(
                        "Enter the index of interest",
                        type=Choice([str(i) for i in positions]),
                        show_choices=False,
                    )
                    index = int(index)
                    item_type = click.prompt(
                        "Track or associated album?",
                        type=Choice(("t", "a"), case_sensitive=False),
                        show_choices=True,
                    )
                    action_type = click.prompt(
                        "Add to queue or play now?",
                        type=click.Choice(("q", "p"), case_sensitive=False),
                        show_choices=True,
                    )

                    if action_type == "q":
                        if item_type == "t":
                            sp_auth.add_to_queue(recent_dict["track_uri"][i])
                        else:
                            add_album_to_queue(sp_auth, recent_dict["album_uri"][index])
                    else:
                        if item_type == "t":
                            sp_auth.start_playback(
                                uris=[recent_dict["track_uri"][index]]
                            )
                        else:
                            sp_auth.start_playback(
                                context_uri=recent_dict["album_uri"][index]
                            )
            else:
                break
    except ValueError:
        click.secho("Invalid format. Proper format is 'YYYYMMDD MM:SS", fg="red")
    except AttributeError:
        # AttributeError is thrown if authorization was unsuccessful, so show that error instead.
        pass
    except SpotifyException as e:
        click.secho(str(e) + device_error_message, fg="red")


@main.command("search")
@click.option(
    "-t",
    "type_",
    type=click.Choice(("album", "artist", "playlist", "track")),
    required=True,
)
@click.argument("term", required=True)
@click.pass_obj
def search(ctx, term, type_):
    """
    Queries Spotify's databases.
    """
    sp_auth = ctx

    k = type_ + "s"
    try:
        search_res = sp_auth.search(q=term, limit=10, type=type_)
        items = search_res[k]["items"]
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
        click.secho(tabulate(results, headers="keys", tablefmt="github"))
        proceed = click.prompt(
            "Do you want to proceed with one of these items?",
            type=Choice(("y", "n"), case_sensitive=False),
            show_choices=True,
        )
        if proceed == "y":
            if len(results) == 2:
                index = 0
            else:
                index = click.prompt(
                    "Enter the index",
                    type=Choice((str(num) for num in range(len(results)))),
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
                    sp_auth.start_playback(context_uri=uris[index])
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
                    display_albums = []
                    for i, item in enumerate(artist_albums_res["items"]):
                        album_type = item["album_type"]
                        artists = truncate(get_artist_names(item))
                        album_name = item["name"]
                        release_date = item["release_date"]
                        total_tracks = item["total_tracks"]
                        uri = item["uri"]
                        albums.append(
                            {
                                "index": i,
                                "album name": album_name,
                                "album type": album_type,
                                "tracks": total_tracks,
                                "release date": release_date,
                                "uri": uri,
                            }
                        )
                        display_albums.append(
                            {
                                "index": i,
                                "album name": album_name,
                                "album type": album_type,
                                "tracks": total_tracks,
                                "release date": release_date,
                            }
                        )
                    click.echo(
                        tabulate(display_albums, headers="keys", tablefmt="github")
                    )
                    further_action = click.prompt(
                        "Do you want to take further action?",
                        type=Choice(("y", "n"), case_sensitive=False),
                        show_choices=True,
                    )
                    if further_action == "y":
                        idx = click.prompt(
                            "Enter the index",
                            type=Choice((str(num) for num in range(len(albums)))),
                            show_choices=False,
                        )
                        idx = int(idx)
                        play_or_queue = click.prompt(
                            "Do you want to play it now or add to queue?",
                            type=Choice(("p", "q"), case_sensitive=False),
                            show_choices=True,
                        )
                        if play_or_queue == "p":
                            sp_auth.start_playback(context_uri=albums[idx]["uri"])
                        else:
                            add_album_to_queue(sp_auth, albums[idx]["uri"])
                            click.secho(
                                "Album successfully added to queue!", fg="green"
                            )
                        sleep(0.5)
                        get_current_playback(sp_auth, display=True)
                    else:
                        pass
        else:
            pass
    except AttributeError:
        pass
    except SpotifyException as e:
        click.secho(str(e) + device_error_message, fg="red")
