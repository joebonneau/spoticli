from typing import Any, Optional

import click
from click.exceptions import Abort
from click.termui import style

import spoticli.commands as commands
from spoticli.lib.util import (
    add_album_to_queue,
    check_url_format,
    convert_datetime,
    get_auth_and_device,
    get_current_playback,
    wait_display_playback,
)


@click.group()
@click.pass_context
def main(ctx):

    sp_auth, device_id, user = commands.setup_session(ctx)
    ctx.obj = {"sp_auth": sp_auth, "device_id": device_id, "user": user}


@main.command("cfg")
def cfg():
    """
    Generates a configuration file for Spotify credentials.
    """
    commands.generate_config()


@main.command("prev")
@click.option("--device")
@click.pass_obj
def previous_track(ctx: dict[str, Any], device: Optional[str]):
    """
    Skips playback to the track played previous to the current track.
    """
    device, sp_auth = get_auth_and_device(ctx, device)

    playback_res = sp_auth.current_playback()
    playback = get_current_playback(playback_res, display=False)
    if playback.get("skip_prev_disallowed"):
        click.echo("No previous tracks are available to skip to.")
    else:
        sp_auth.previous_track(device_id=device)
        wait_display_playback(sp_auth)


@main.command("next")
@click.option("--device")
@click.pass_obj
def next_track(ctx: dict[str, Any], device: Optional[str]):
    """
    Skips playback to the next track in the queue
    """
    device, sp_auth = get_auth_and_device(ctx, device)
    sp_auth.next_track(device_id=device)
    wait_display_playback(sp_auth)


@main.command("pause")
@click.option("--device")
@click.pass_obj
def pause_playback(ctx: dict[str, Any], device: Optional[str]):
    """
    Pauses playback.
    """
    device, sp_auth = get_auth_and_device(ctx, device)

    current_playback = sp_auth.current_playback()
    playback = get_current_playback(current_playback, display=False)
    if playback.get("pausing_disallowed"):
        click.echo("No current playback to pause.")
    else:
        sp_auth.pause_playback(device_id=device)
        click.echo("Playback paused.")


@main.command("play")
@click.option("--device")
@click.argument("url", required=False)
@click.pass_obj
def start_playback(ctx: dict[str, Any], device: Optional[str], url: Optional[str]):
    """
    Resumes playback on the active track.
    """
    device, sp_auth = get_auth_and_device(ctx, device)
    commands.start_playback(sp_auth, device, url)


@main.command("cp")
@click.option("-pub/-pri", default=True, help="public or private")
@click.option(
    "-c/-i",
    default=False,
    help="collaborative or non-collaborative",
)
@click.option("-d", type=str, default="", help="playlist description")
@click.argument("name", required=True)
@click.pass_obj
def create_playlist(ctx: dict[str, Any], pub: bool, c: bool, d: str, name: str):
    """
    Creates a new playlist.
    """
    _, sp_auth = get_auth_and_device(ctx, device=None)

    if all((pub, c)):
        click.secho(style("Collaborative playlists can only be private.", fg="red"))
        raise Abort()
    sp_auth.user_playlist_create(
        user=ctx["user"],
        name=name,
        public=pub,
        collaborative=c,
        description=d,
    )
    click.secho(style(f"Playlist '{name}' created successfully!", fg="green"))


@main.command("seek")
@click.option("--device")
@click.argument("timestamp", required=True)
@click.pass_obj
def seek(ctx: dict[str, Any], timestamp: str, device: str):
    """
    Seeks the track to the timestamp specified.

    Timestamp format is MM:SS
    """
    device, sp_auth = get_auth_and_device(ctx, device)
    commands.seek(sp_auth, timestamp, device)


@main.command("volup")
@click.option("--device")
@click.argument("amount", default=10)
@click.pass_obj
def increase_volume(ctx: dict[str, Any], amount: int, device: str):
    """
    Increases volume by the increment specified (defaults to 10%).
    """
    device, sp_auth = get_auth_and_device(ctx, device)
    commands.increase_volume(amount, device, sp_auth)


@main.command("voldown")
@click.option("--device")
@click.argument("amount", default=10)
@click.pass_obj
def decrease_volume(ctx: dict[str, Any], amount: int, device: str):
    """
    Decreases volume by the increment specified (defaults to 10%).
    """
    device, sp_auth = get_auth_and_device(ctx, device)
    commands.decrease_volume(amount, device, sp_auth)


@main.command("now")
@click.option("-v", "--verbose", is_flag=True, help="displays additional info")
@click.option("-u", "--url", default="t", help="displays current playback url")
@click.pass_obj
def now_playing(ctx: dict[str, Any], verbose: bool, url: str):
    """
    Displays info about the current playback.
    """
    _, sp_auth = get_auth_and_device(ctx, device=None)

    current_playback = sp_auth.current_playback()
    playback = get_current_playback(res=current_playback, display=True)
    track_uri = playback.get("track_uri")
    if track_uri and verbose:
        audio_features = sp_auth.audio_features(track_uri)
        click.echo(f"BPM: {audio_features[0]['tempo']}")
        click.echo(f"Time signature: 4/{audio_features[0]['time_signature']}")
        if url == "t":
            click.echo(f"Track URL: {style(playback['track_url'], fg='magenta')}")
        elif url == "a":
            click.echo(f"Album URL: {style(playback['album_url'], fg='blue')}")


@main.command("shuffle")
@click.option("--device")
@click.option("-on/-off", required=True, is_flag=True)
@click.pass_obj
def toggle_shuffle(ctx: dict[str, Any], on: bool, device: str):
    """
    Toggles shuffling on or off.
    """
    device, sp_auth = get_auth_and_device(ctx, device)

    msg = "on" if on else "off"
    color = "green" if on else "red"
    sp_auth.shuffle(state=on, device_id=device)
    click.echo(f"Shuffle toggled {style(msg, fg=color)}.")

@main.command("rsa")
@click.option("--device")
@click.pass_obj
def get_random_saved_album(ctx: dict[str, Any], device: str):
    """
    Fetches all albums in user library and selects one randomly.
    """
    device, sp_auth = get_auth_and_device(ctx, device)
    commands.get_random_saved_album(sp_auth, device=device)


@main.command("actp")
@click.pass_obj
def add_current_track_to_playlists(ctx: dict[str, Any]):
    """
    Adds the current track in playback to one or more playlist(s).
    """
    _, sp_auth = get_auth_and_device(ctx, device=None)
    commands.add_current_track_to_playlists(sp_auth)


@main.command("recent")
@click.option("-a", "--after", default=None, help="YYYYMMDD MM:SS")
@click.option("-l", "--limit", default=25, help="Entries to return (max 50)")
@click.option("--device")
@click.pass_obj
def recently_played(ctx: dict[str, Any], after: str, limit: int, device: str):
    """
    Displays information about recently played tracks.
    """
    device, sp_auth = get_auth_and_device(ctx, device)
    after = convert_datetime(after) if after else after
    commands.recently_played(
        sp_auth, after=after, limit=limit, device=device, user=ctx["user"]
    )


@main.command("search")
@click.option("--device")
@click.option(
    "-t",
    "type_",
    type=click.Choice(("album", "artist", "playlist", "track")),
    required=True,
)
@click.argument("query", required=True)
@click.pass_obj
def search(ctx: dict[str, Any], query: str, type_: str, device: str):
    """
    Queries Spotify's databases.
    """
    device, sp_auth = get_auth_and_device(ctx, device)
    commands.search(sp_auth=sp_auth, query=query, type_=type_, device=device)


@main.command("atq")
@click.option("--device")
@click.argument("url", required=True)
@click.pass_obj
def add_to_queue(ctx: dict[str, Any], url: str, device: str):
    """
    Adds a track or album to the queue from a Spotify URL.
    """
    device, sp_auth = get_auth_and_device(ctx, device)

    try:
        valid_url = check_url_format(url)
    except ValueError:
        click.secho("An invalid URL was provided.", fg="red")
    if "album" in url:
        add_album_to_queue(sp_auth, valid_url, device)
    else:
        sp_auth.add_to_queue(valid_url, device)
        click.secho("Track successfully added to queue.", fg="green")


@main.command("spa")
@click.argument("url", required=True)
@click.pass_obj
def save_playlist_albums(
    ctx: dict[str, Any],
    url: str,
):
    """
    Retrieves all albums from a given playlist and allows the user to add them to their
    library.
    """
    check_url_format(url)
    _, sp_auth = get_auth_and_device(ctx, device=None)
    commands.save_playlist_items(sp_auth, url)
