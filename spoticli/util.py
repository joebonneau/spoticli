from typing import Iterable
import os

import spotipy as sp
from spotipy.oauth2 import SpotifyOAuth
import click
from click.termui import style

SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.environ.get("SPOTIFY_REDIRECT_URI")

USER_READ_PLAYBACK_STATE = "user-read-playback-state"


def connect(
    scope: str,
    client_id: str = SPOTIFY_CLIENT_ID,
    client_secret: str = SPOTIFY_CLIENT_SECRET,
    redirect_uri: str = SPOTIFY_REDIRECT_URI,
) -> sp.Spotify:
    try:
        auth = sp.Spotify(
            auth_manager=SpotifyOAuth(
                scope=scope,
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
            )
        )

        return auth
    except:
        click.secho(
            "API authorization failed! Did you remember to set the environment variables?",
            fg="red",
        )


def get_current_playback(display: bool) -> dict:

    sp_auth = connect(scope=USER_READ_PLAYBACK_STATE)

    current_playback = sp_auth.current_playback()
    playback = {}

    artists = []
    for i in range(len(current_playback["item"]["artists"])):
        artists.append(current_playback["item"]["artists"][i]["name"])
    artists_str = ", ".join(artists)

    playback["artists"] = artists_str
    playback["track_name"] = current_playback["item"]["name"]
    playback["track_uri"] = current_playback["item"]["uri"]
    playback["album_name"] = current_playback["item"]["album"]["name"]
    playback["album_uri"] = current_playback["item"]["album"]["uri"]
    playback["release_date"] = current_playback["item"]["album"]["release_date"]
    playback["duration"] = convert_duration(current_playback["item"]["duration_ms"])
    playback["volume"] = current_playback["device"]["volume_percent"]
    playback["shuffle_state"] = current_playback["shuffle_state"]

    if display:
        track_name = style(playback["track_name"], fg="magenta")
        artists_name = style(playback["artists"], fg="green")
        album_name = style(playback["album_name"], fg="blue")

        click.secho(
            f"Now playing: {track_name} by {artists_name} from the album {album_name}"
        )
        click.echo(
            f"Duration: {playback['duration']}, Released: {playback['release_date']}"
        )

    return playback


def convert_duration(duration_ms: int) -> str:

    minutes, seconds = divmod(duration_ms / 1000, 60)
    duration = f"{int(minutes)}:{int(round(seconds,0))}"

    return duration
