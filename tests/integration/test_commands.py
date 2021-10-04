import os
from configparser import ConfigParser
from pathlib import Path

from appdirs import user_config_dir
from click.testing import CliRunner

from spoticli.spoticli import main

SPOTIFY_DEVICE_ID = os.environ.get("SPOTIFY_DEVICE_ID")


def test_play():
    runner = CliRunner()
    result = runner.invoke(main, ["play", f"--device={SPOTIFY_DEVICE_ID}"])
    assert "Now playing:" in result.output


def test_next_track():
    runner = CliRunner()

    result = runner.invoke(main, ["next", f"--device={SPOTIFY_DEVICE_ID}"])

    assert "Now playing:" in result.output


def test_previous_track():
    runner = CliRunner()

    result = runner.invoke(main, ["prev", f"--device={SPOTIFY_DEVICE_ID}"])

    assert "Now playing:" in result.output


def test_seek():
    runner = CliRunner()

    result = runner.invoke(main, ["seek", "00:10", f"--device={SPOTIFY_DEVICE_ID}"])

    assert result.output == ""


def test_pause():
    runner = CliRunner()

    result = runner.invoke(main, ["pause", f"--device={SPOTIFY_DEVICE_ID}"])

    assert "Playback paused." in result.output


def test_voldown():
    runner = CliRunner()

    result = runner.invoke(main, ["volup", "50", f"--device={SPOTIFY_DEVICE_ID}"])

    assert "New volume:" in result.output


def test_volup():
    runner = CliRunner()

    result = runner.invoke(main, ["volup", "50", f"--device={SPOTIFY_DEVICE_ID}"])

    assert "New volume:" in result.output


def test_now():
    runner = CliRunner()

    result = runner.invoke(main, ["now"])

    assert "Released:" in result.output


def test_now_verbose():
    runner = CliRunner()

    result = runner.invoke(main, ["now", "-v"])

    assert "Time signature:" in result.output


def test_add_current_track_to_playlist():
    runner = CliRunner()

    result = runner.invoke(main, ["actp"], input="0, 1")

    assert "was successfully added to all specified playlists!" in result.output


def test_recent_action_play_track():
    runner = CliRunner()

    inputs = ("y", "p", "0", "t")
    result = runner.invoke(
        main, ["recent", f"--device={SPOTIFY_DEVICE_ID}"], input="\n".join(inputs)
    )

    assert "Now playing:" in result.output


def test_recent_action_play_album():
    runner = CliRunner()

    inputs = ("y", "p", "0", "a")
    result = runner.invoke(
        main, ["recent", f"--device={SPOTIFY_DEVICE_ID}"], input="\n".join(inputs)
    )

    assert "Now playing:" in result.output


def test_recent_action_queue_track():
    runner = CliRunner()

    inputs = ("y", "q", "0", "t")
    result = runner.invoke(
        main, ["recent", f"--device={SPOTIFY_DEVICE_ID}"], input="\n".join(inputs)
    )

    assert "Track successfully added to the queue." in result.output


def test_recent_action_queue_album():
    runner = CliRunner()

    inputs = ("y", "q", "0", "a")
    result = runner.invoke(
        main, ["recent", f"--device={SPOTIFY_DEVICE_ID}"], input="\n".join(inputs)
    )

    assert "Album successfully added to the queue." in result.output


def test_recent_action_create_playlist():
    runner = CliRunner()

    inputs = ("y", "cp", "0, 5", "recent_test")
    result = runner.invoke(
        main, ["recent", f"--device={SPOTIFY_DEVICE_ID}"], input="\n".join(inputs)
    )

    assert "Playlist 'recent_test' created successfully!" in result.output


def test_shuffle_on():
    runner = CliRunner()

    result = runner.invoke(main, ["shuffle", "-on", f"--device={SPOTIFY_DEVICE_ID}"])

    assert "Shuffle toggled on" in result.output


def test_shuffle_off():
    runner = CliRunner()

    result = runner.invoke(main, ["shuffle", "-off", f"--device={SPOTIFY_DEVICE_ID}"])

    assert "Shuffle toggled off" in result.output


def test_create_playlist_valid_inputs():
    runner = CliRunner()

    playlist_name = "test_playlist"

    result = runner.invoke(main, ["cp", "-pub", "-i", playlist_name])

    assert f"Playlist '{playlist_name}' created successfully!" in result.output


def test_create_playlist_invalid_inputs():
    runner = CliRunner()

    playlist_name = "test_playlist"

    result = runner.invoke(main, ["cp", "-pub", "-c", playlist_name])

    assert "Collaborative playlists can only be private." in result.output


def test_cfg_cancel():
    runner = CliRunner()

    result = runner.invoke(main, ["cfg"], input="n")

    assert "Configuration creation canceled." in result.output


def test_cfg_success():
    runner = CliRunner()

    config_dir = Path(user_config_dir()) / "spoticli"
    config_file = config_dir / "spoticli.ini"

    inputs = [
        "420aec9e1e8e191480695d095e3ad2ed",
        "220bec4e6e8e291300695d095e3ad2ed",
        "http://localhost:8887/callback",
        "dp9s41ge8dlrl1mi77hwptmco",
    ]

    if config_file.exists():
        inputs.insert(0, "y")

    result = runner.invoke(main, ["cfg"], input="\n".join(inputs))

    config = ConfigParser()
    config.read(config_file)

    # this is important to check for the case where the config file existed and is
    # being overwritten
    assert config.sections() == ["auth"]
    assert config["auth"]["spotify_client_id"] == "420aec9e1e8e191480695d095e3ad2ed"
    assert config["auth"]["spotify_client_secret"] == "220bec4e6e8e291300695d095e3ad2ed"
    assert config["auth"]["spotify_user_id"] == "dp9s41ge8dlrl1mi77hwptmco"
    assert config["auth"]["spotify_redirect_uri"] == "http://localhost:8887/callback"
    assert "Config file created successfully!" in result.output
