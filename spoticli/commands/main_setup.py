import json
import os
from configparser import ConfigParser
from configparser import Error as ConfigError
from pathlib import Path
from time import sleep
from typing import Any

import click
from appdirs import user_config_dir
from click import Context, IntRange
from click.exceptions import Abort
from spotipy import Spotify
from spotipy.cache_handler import MemoryCacheHandler
from spotipy.client import SpotifyException
from spotipy.oauth2 import SpotifyOAuth, SpotifyOauthError

from spoticli.lib.exceptions import NoDevicesFound
from spoticli.lib.util import display_table

CACHED_TOKEN_INFO = os.environ.get("CACHED_TOKEN_INFO")

states = [
    "user-modify-playback-state",
    "user-read-playback-state",
    "user-library-read",
    "user-library-modify",
    "playlist-read-private",
    "playlist-read-collaborative",
    "playlist-modify-public",
    "playlist-modify-private",
    "user-read-recently-played",
]
STATE_STR = " ".join(states)
NO_DEVICE_REQUIRED = (
    "create_playlist",
    "now_playing",
    "add_current_track_to_playlists",
    "save_playlist_albums",
)
PAUSE_AFTER_PLAYBACK_TRANSFER = (
    "get_random_saved_album",
    "recently_played",
    "search",
    "add_to_queue",
)
CONFIG_DIR = Path(user_config_dir("spoticli", "joebonneau"))
CONFIG_FILE = CONFIG_DIR / "spoticli.ini"


def setup_session(ctx: Context) -> tuple[Spotify, str, str]:

    sp_auth = None
    client_id = None
    client_secret = None
    redirect_uri = None
    user = None
    subcmd = ctx.invoked_subcommand
    if subcmd != "cfg":
        token_info = None
        if CACHED_TOKEN_INFO:
            token_info = json.loads(CACHED_TOKEN_INFO)
        elif CONFIG_FILE.exists():
            client_id, client_secret, redirect_uri, user = _parse_config()
        else:
            click.secho("Authorization failed. Try running 'spoticli cfg'.", fg="red")
            raise Abort()

        cache_handler = (
            MemoryCacheHandler(token_info=token_info) if token_info else None
        )
        sp_auth = _get_auth(client_id, client_secret, redirect_uri, cache_handler)

        device_id = None
        if ctx.invoked_subcommand not in NO_DEVICE_REQUIRED:
            devices_res = sp_auth.devices()
            device_id = _get_device(subcmd, sp_auth, devices_res)

    return sp_auth, device_id, user


def _parse_config():
    try:
        config = ConfigParser()
        config.read(CONFIG_FILE)

        auth = config["auth"]
        client_id = auth["spotify_client_id"]
        client_secret = auth["spotify_client_secret"]
        redirect_uri = auth["spotify_redirect_uri"]
        user = auth["spotify_user_id"]
    except (KeyError, ConfigError) as e:
        click.secho(
            "Config file exists but is set up improperly. Try recreating the config file "
            "with 'spoticli cfg'.",
            fg="red",
        )
        raise Abort() from e
    return client_id, client_secret, redirect_uri, user


def _get_device(subcmd, sp_auth, devices_res):
    try:
        device_id, is_active = check_devices(devices_res)
    except NoDevicesFound as e:
        click.secho(str(e), fg="red")
        raise Abort() from e
    if not is_active:
        # currently, forcing the device to play the transferred playback is the only way to
        # reliably activate a device.
        sp_auth.transfer_playback(device_id=device_id, force_play=True)
        # pause after the playback transfer if having current playback isn't necessary for
        # the rest of the command.
        if subcmd in PAUSE_AFTER_PLAYBACK_TRANSFER:
            sp_auth.pause_playback(device=device_id)
        sleep(0.2)
    return device_id


def _get_auth(client_id, client_secret, redirect_uri, cache_handler):
    try:
        sp_auth = Spotify(
            auth_manager=SpotifyOAuth(
                scope=STATE_STR,
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                cache_handler=cache_handler,
            )
        )
    except (SpotifyException, SpotifyOauthError) as e:
        click.secho(
            "Authorization failed! Try reconfiguring the client params with "
            f"'spoticli cfg'. Error: {str(e)}",
            fg="red",
        )
        raise Abort() from e
    return sp_auth


def check_devices(res: dict[str, list[dict[str, Any]]]) -> tuple[str, bool]:

    active_device = False
    device_options: list[dict[str, Any]] = []
    device_id = None
    for i, device in enumerate(res["devices"]):
        device_options.append(
            {
                "index": i,
                "name": device["name"],
                "type": device["type"],
                "id": device["id"],
            }
        )

        if device["is_active"]:
            active_device = True
            device_id = device_id
            break

    if not device_options:
        raise NoDevicesFound(
            "No devices were found. Verify the Spotify client is open on a device."
        )

    if not active_device:
        if len(device_options) == 1:
            device_to_activate = 0
        else:
            display_table(device_options)

            device_to_activate = click.prompt(
                "Enter the index of the device to activate",
                type=IntRange(min=0, max=len(device_options) - 1),
                show_choices=False,
            )
        return device_options[int(device_to_activate)]["id"], active_device
    return device_id, active_device
