import click

from spoticli.lib.util import get_current_playback


def increase_volume(amount, device, sp_auth):
    previous_volume = _get_previous_volume(sp_auth)
    new_volume = int(round(previous_volume + amount, 0))
    new_volume = min(new_volume, 100)
    _set_and_display(device, sp_auth, new_volume)


def decrease_volume(amount, device, sp_auth):
    previous_volume = _get_previous_volume(sp_auth)
    new_volume = int(round(previous_volume - amount, 0))
    new_volume = max(new_volume, 0)
    _set_and_display(device, sp_auth, new_volume)


def _set_and_display(device, sp_auth, new_volume):
    sp_auth.volume(new_volume, device_id=device)
    click.secho(f"New volume: {new_volume}")


def _get_previous_volume(sp_auth):
    current_playback = sp_auth.current_playback()
    playback = get_current_playback(res=current_playback, display=False)
    return playback["volume"]
