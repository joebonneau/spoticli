from configparser import ConfigParser
from os import mkdir
from pathlib import Path

import click
from appdirs import user_config_dir

from spoticli.lib.types import SpotifyCredential
from spoticli.lib.util import Y_N_CHOICE_CASE_INSENSITIVE


def generate_config():

    config_dir = Path(user_config_dir()) / "spoticli"
    config_file = config_dir / "spoticli.ini"
    config = ConfigParser()

    if not config_dir.exists():
        mkdir(config_dir)

    proceed = "y"
    if config_file.exists():
        proceed = click.prompt(
            "A config file already exists. Do you want to overwrite its contents?",
            type=Y_N_CHOICE_CASE_INSENSITIVE,
            show_choices=True,
        )

    if proceed == "y":
        _accept_config_input(config, config_file)
    else:
        click.secho("Configuration creation canceled.")


def _accept_config_input(config, config_file):
    client_id = click.prompt(
        "Provide the Spotify client ID from the developer dashboard",
        type=SpotifyCredential(),
    )
    client_secret = click.prompt(
        "Provide the Spotify client secret from the developer dashboard",
        type=SpotifyCredential(),
    )
    redirect_uri = click.prompt(
        "Provide the redirect URI you specified in the Spotify app"
    )
    user_id = click.prompt("Provide the Spotify user ID")

    config["auth"] = {
        "SPOTIFY_CLIENT_ID": client_id,
        "SPOTIFY_CLIENT_SECRET": client_secret,
        "SPOTIFY_USER_ID": user_id,
        "SPOTIFY_REDIRECT_URI": redirect_uri,
    }

    with open(config_file, "w") as cfg:
        config.write(cfg)

    click.secho("Config file created successfully!", fg="green")
