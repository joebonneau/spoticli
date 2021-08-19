from click.testing import CliRunner

from spoticli.spoticli import main

DEVICE_ID = "8530ebdfd4de076e834fced6928868d39f9c0d12"
FAKE_DEVICE_ID = "8512ebdfd4de076e456kced6928868d39f9c0d"


def test_previous_track_fake_device():
    runner = CliRunner()

    result = runner.invoke(main, ["prev", f"--device={FAKE_DEVICE_ID}"])

    assert "Device not found, reason: None" in result.output


def test_previous_track_no_active_device():
    runner = CliRunner()

    result = runner.invoke(main, ["prev"])

    assert "No active device found, reason: NO_ACTIVE_DEVICE" in result.output


def test_previous_track_valid_device():
    runner = CliRunner()

    result = runner.invoke(main, ["prev", f"--device={DEVICE_ID}"])

    assert "Now playing" in result.output
    assert "Duration:" in result.output
