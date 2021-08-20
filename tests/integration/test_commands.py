from click.testing import CliRunner

from spoticli.spoticli import main

DEVICE_ID = "8530ebdfd4de076e834fced6928868d39f9c0d12"


def test_play():
    runner = CliRunner()

    result = runner.invoke(main, ["play", f"--device={DEVICE_ID}"])

    assert "Now playing:" in result.output


def test_next_track():
    runner = CliRunner()

    result = runner.invoke(main, ["next", f"--device={DEVICE_ID}"])

    assert "Now playing:" in result.output


def test_previous_track():
    runner = CliRunner()

    result = runner.invoke(main, ["prev", f"--device={DEVICE_ID}"])

    assert "Now playing:" in result.output


def test_seek():
    runner = CliRunner()

    result = runner.invoke(main, ["seek", "00:10"])

    assert result.output == ""


def test_voldown():
    runner = CliRunner()

    result = runner.invoke(main, ["volup", "50"])

    assert "New volume:" in result.output


def test_volup():
    runner = CliRunner()

    result = runner.invoke(main, ["volup", "50"])

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

    assert (
        "The track was successfully added to all specified playlists!" in result.output
    )


def test_recent_no_action():
    runner = CliRunner()

    result = runner.invoke(main, ["recent"], input="n")

    assert "track_name" in result.output


def test_recent_action_play_track():
    runner = CliRunner()

    inputs = ("y", "p", "0", "t")
    result = runner.invoke(main, ["recent"], input="\n".join(inputs))

    assert "Now playing:" in result.output


def test_recent_action_play_album():
    runner = CliRunner()

    inputs = ("y", "p", "0", "a")
    result = runner.invoke(main, ["recent"], input="\n".join(inputs))

    assert "Now playing:" in result.output


def test_recent_action_queue_track():
    runner = CliRunner()

    inputs = ("y", "q", "0", "t")
    result = runner.invoke(main, ["recent"], input="\n".join(inputs))

    assert "Track successfully added to the queue." in result.output


def test_recent_action_queue_album():
    runner = CliRunner()

    inputs = ("y", "q", "0", "a")
    result = runner.invoke(main, ["recent"], input="\n".join(inputs))

    assert "Album successfully added to the queue." in result.output


def test_recent_action_create_playlist():
    runner = CliRunner()

    inputs = ("y", "cp", "0, 5", "recent_test")
    result = runner.invoke(main, ["recent"], input="\n".join(inputs))

    assert "Playlist 'recent_test' created successfully!" in result.output


def test_pause():
    runner = CliRunner()

    result = runner.invoke(main, ["pause", f"--device={DEVICE_ID}"])

    assert "Playback paused." in result.output


def test_shuffle_on():
    runner = CliRunner()

    result = runner.invoke(main, ["shuffle", "-on"])

    assert "Shuffle toggled on" in result.output


def test_shuffle_off():
    runner = CliRunner()

    result = runner.invoke(main, ["shuffle", "-off"])

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
