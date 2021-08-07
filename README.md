# SpotiCLI
A command line interface for Spotify written in Python!

The goal of this project is to provide both basic functionality available in the Spotify desktop or mobile apps as well as new functionality that currently is not straightforward. Some examples are:
* `play_random_saved_album`: randomly selects an album from the user library and allows you to either directly start playback or add to the queue
* `add_current_track_to_playlists`: allows for the addition of the current track to multiple playlists simultaneously

# Requirements
* Must have a Spotify Premium account
* Must sign up for a Developer account at [Spotify Developer](https://developer.spotify.com)
  * You'll need both the `Client ID` and `Client Secret` for API authorization
## Usage

### Setting environment variables

Currently, the parameters for API authorization must be specified as environment variables.

MacOS/Linux:
```bash
export SPOTIFY_CLIENT_ID="4gw43g3"
export SPOTIFY_CLIENT_SECRET="32458cwerg"
export SPOTIFY_REDIRECT_URI="https://"
```

Windows:
```bash
set SPOTIFY_CLIENT_ID="4gw43g3"
set SPOTIFY_CLIENT_SECRET="32458cwerg"
set SPOTIFY_REDIRECT_URI="https://"
```


