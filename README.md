
# SpotiCLI

[![Build Status](https://travis-ci.com/joebonneau/spoticli.svg?branch=main)](https://travis-ci.com/joebonneau/spoticli)
[![codecov](https://codecov.io/gh/joebonneau/spoticli/branch/main/graph/badge.svg?token=W42UPW2CLN)](https://codecov.io/gh/joebonneau/spoticli)

A command line interface for Spotify written in Python!

The goal of this project is to provide both basic functionality available in the Spotify desktop or mobile apps as well as new functionality that currently is not straightforward. Some examples are:

* `rsa`: randomly selects an album from the user library and allows you to either directly start playback or add to the queue
* `actp`: allows for the addition of the current track to multiple playlists simultaneously
* `recent`: displays information about recently played tracks and allows you to interactively add them to your queue or playlists

## Requirements

* Must have a Spotify Premium account
* Must sign up for a Developer account at [Spotify Developer](https://developer.spotify.com)
* Create an app
  * Set the `Redirect URI` to anything that will open in a web browser - doesn't need to be on your local network or an actual domain.
  * You'll need both the `Client ID` and `Client Secret` for API authorization
* Log into Spotify and navigate to your account details - you'll need your username (which is an ID)

## Installation

**NOTE: All development work has been on Ubuntu 20.04 and has not been tested on any other platform, though it should also work!**

Clone the repo:

```bash
cd github_repos
git clone https://github.com/joebonneau/spoticli.git
cd spoticli
```

### Via the source code

Dependencies for SpotiCLI are configured using [Poetry](https://python-poetry.org/).

If using a virtual environment, activate the environment then install Poetry (you can also use `pip install poetry`, but the methods below are officially recommended by the Poetry devs).

OSX/Linux

```bash
curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py | python -
```

Windows Powershell:

```powershell
(Invoke-WebRequest -Uri https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py -UseBasicParsing).Content | python -
```

Once Poetry is installed, install the dependencies from the `pyproject.toml` file by running the following in the spoticli directory:

```bash
poetry install --no-dev
```

If you happen to be contributing, go ahead and drop the `--no-dev` :)

### Via a package manager

SpotiCLI is not currently deployed to PyPI as a package that is installable via pip or some other package manager. (Coming at a later date)

## Usage

SpotiCLI is intentionally intuitive and easy to use.

### Setting environment variables

Currently, the parameters for API authorization as well as the username must be specified as environment variables.

OSX/Linux:

```bash
export SPOTIFY_USER_ID=""
export SPOTIFY_CLIENT_ID=""
export SPOTIFY_CLIENT_SECRET=""
export SPOTIFY_REDIRECT_URI="https://"
```

Windows Powershell:

```bash
set SPOTIFY_USER_ID=""
set SPOTIFY_CLIENT_ID=""
set SPOTIFY_CLIENT_SECRET=""
set SPOTIFY_REDIRECT_URI="https://"
```

### Running commands

You should be good to get started with using SpotiCLI!

Start by running the following to quickly test the installation:

```bash
spoticli --help
```

This will show you all available commands. To get more information about a specific command, try something like the following"

```bash
spoticli recent --help
```

As of August 21, 2021, here is a comprehensive list of all available commands:

* `actp` (add current track to playlists)
* `cp` (create playlist)
* `next`
* `now` (current playback)
* `pause`
* `play`
* `prev` (previous)
* `recent` (recent playback)
* `rsa` (play random saved album)
* `search`
* `seek` (jump forwards or backwards in the current playback)
* `shuffle`
* `voldown`
* `volup`
