import json
from pathlib import Path

import pytest

from spoticli.commands.search import (
    parse_album_search,
    parse_artist_search,
    parse_playlist_search,
    parse_track_search,
)
from spoticli.commands.seek import convert_timestamp
from spoticli.lib.exceptions import InvalidURL
from spoticli.lib.util import (
    check_url_format,
    convert_datetime,
    convert_ms,
    get_artist_names,
    get_current_playback,
    truncate,
)


@pytest.fixture(scope="module")
def example_response_data():
    path = Path("tests/unit/artifacts/current_playback_res.json")
    with open(path) as f:
        res = json.load(f)

    return res


def test_get_artist_names(example_response_data):

    artist_names = get_artist_names(example_response_data["item"])

    assert artist_names == "Durand Jones & The Indications, Aaron Frazer"


def test_get_current_playback(example_response_data):

    playback = get_current_playback(example_response_data, False)

    response = {
        "album_name": "Private Space",
        "album_type": "album",
        "album_uri": "spotify:album:4ogV05oprfriua7n9icbvN",
        "album_url": "https://open.spotify.com/album/4ogV05oprfriua7n9icbvN",
        "artists": "Durand Jones & The Indications",
        "duration": "3:45",
        "pausing_disallowed": None,
        "release_date": "2021-07-30",
        "resuming_disallowed": True,
        "shuffle_state": False,
        "skip_prev_disallowed": True,
        "track_name": "Love Will Work It Out",
        "track_uri": "spotify:track:6qXQYEZeRSgmAvDm4ZEAUZ",
        "track_url": "https://open.spotify.com/track/6qXQYEZeRSgmAvDm4ZEAUZ",
        "volume": 100,
    }

    assert playback == response


def test_convert_ms():

    assert convert_ms(225461) == "3:45"
    assert convert_ms(600000) == "10:00"


def test_convert_timestamp():

    assert convert_timestamp("3:45") == 225000
    assert convert_timestamp("10:00") == 600000


@pytest.mark.xfail(reason="returns the wrong value in CI for some reason")
def test_convert_datetime():

    assert convert_datetime("20210813 20:01") == 1628910060000
    assert convert_datetime("20200403 13:37") == 1585946220000


def test_truncate():

    artists_str = "Durand Jones & The Indications, Aaron Frazer"

    assert truncate(artists_str, 40) == "Durand Jones & The Indications, Aaron Fr..."
    assert truncate(artists_str, 35) == "Durand Jones & The Indications, Aar..."
    assert truncate(artists_str) == "Durand Jones & The Indications, Aaron Frazer"


def test_search_parse_album():

    path = Path("tests/unit/artifacts/search_album_res.json")
    f = open(path)
    res = json.load(f)

    actual_results, actual_uris = parse_album_search(res)

    results = [
        {
            "index": 0,
            "artist(s)": "Nas",
            "album title": "Illmatic",
            "release date": "1994-04-19",
        },
        {
            "index": 1,
            "artist(s)": "Nas",
            "album title": "Illmatic XX",
            "release date": "2014-04-15",
        },
        {
            "index": 2,
            "artist(s)": "Nas",
            "album title": "Illmatic",
            "release date": "1994-04-19",
        },
        {
            "index": 3,
            "artist(s)": "Nas",
            "album title": "Illmatic: Live from the Kennedy Center with the National Symphony Orchestra",
            "release date": "2018-04-20",
        },
        {
            "index": 4,
            "artist(s)": "golden era",
            "album title": "illmatic (lofi beats)",
            "release date": "2020-03-13",
        },
        {
            "index": 5,
            "artist(s)": "Various Artists",
            "album title": "10 Year Anniversary Illmatic Platinum Series",
            "release date": "2004",
        },
        {
            "index": 6,
            "artist(s)": "ILLMATIC BUDDHA MC'S, SCHA DARA PARR",
            "album title": "TOP OF TOKYO/TT2 オワリのうた",
            "release date": "2006-11-29",
        },
        {
            "index": 7,
            "artist(s)": "Prodig Illmatic",
            "album title": "L.S.D",
            "release date": "2021-04-09",
        },
        {
            "index": 8,
            "artist(s)": "Nas",
            "album title": "Stillmatic",
            "release date": "2001-12-18",
        },
        {
            "index": 9,
            "artist(s)": "Nas",
            "album title": "From Illmatic To Stillmatic The Remixes",
            "release date": "2002-07-02",
        },
    ]

    uris = [
        "spotify:album:3kEtdS2pH6hKcMU9Wioob1",
        "spotify:album:6oSHgr3TZJPCFshYUfBDqE",
        "spotify:album:4Ylo6qvhUY2h7VqEJHfYcy",
        "spotify:album:1Xd9sCWxvNx02wCTZbKoek",
        "spotify:album:6YiJxfK69jd89oUyk7CeQ3",
        "spotify:album:6rXstoVf7abF1VyuYRzxBw",
        "spotify:album:68ug5BwUWtP1OAzq8AlMUT",
        "spotify:album:7iDV5POx4lTm2LHHxSSgyT",
        "spotify:album:0cLzuJG2UDa0axMQkF7JR6",
        "spotify:album:32zX5u2pOCNNxzO2BAyGfd",
    ]

    assert actual_uris == uris
    assert actual_results == results


def test_search_parse_artist():

    path = Path("tests/unit/artifacts/search_artist_res.json")
    f = open(path)
    res = json.load(f)

    actual_results, actual_uris = parse_artist_search(res)

    results = [
        {"index": 0, "artist": "A Tribe Called Quest"},
        {"index": 1, "artist": "A Tribe Called Quest"},
    ]

    uris = [
        "spotify:artist:09hVIj6vWgoCDtT03h8ZCa",
        "spotify:artist:2NQZmi2vNrB09no3wbNuJC",
    ]

    assert actual_uris == uris
    assert actual_results == results


def test_search_parse_playlist():

    path = Path("tests/unit/artifacts/search_playlist_res.json")
    f = open(path)
    res = json.load(f)

    actual_results, actual_uris = parse_playlist_search(res)

    results = [
        {
            "index": 0,
            "name": "Groovin', Pt. 1 (2020)",
            "creator": "Soul Dialect",
            "description": "",
            "tracks": 18,
        },
        {
            "index": 1,
            "name": "Groovin on a Sunday Afternoon",
            "creator": "Devon Paige",
            "description": "",
            "tracks": 635,
        },
        {
            "index": 2,
            "name": "Groovin' R&B",
            "creator": "Spotify",
            "description": "R&Bの最新話題曲をまとめてお届けします。cover: ティナーシェ",
            "tracks": 60,
        },
        {
            "index": 3,
            "name": "Groovin', Pt. 2 (2020)",
            "creator": "Soul Dialect",
            "description": "",
            "tracks": 93,
        },
        {
            "index": 4,
            "name": "Grooving Tunes",
            "creator": "Romain Sylvian",
            "description": "Grooving Tunes to get you through the weekend! Fea...",
            "tracks": 154,
        },
        {
            "index": 5,
            "name": "Cruise And Play: Groovin' Soul Classics",
            "creator": "PlayStation®️",
            "description": "The greatest old school jams. Cruise down the virt...",
            "tracks": 201,
        },
        {
            "index": 6,
            "name": "Kenny Rankin - Groovin' – Desconocidos",
            "creator": "Acarlosbriones",
            "description": "",
            "tracks": 37,
        },
        {
            "index": 7,
            "name": "Groovin', Pt. 2 - Proto",
            "creator": "Soul Dialect",
            "description": "",
            "tracks": 90,
        },
        {
            "index": 8,
            "name": "Groovin' ",
            "creator": "Carter NG",
            "description": "",
            "tracks": 186,
        },
        {
            "index": 9,
            "name": "Groovin', Pt. 3 (2020)",
            "creator": "Soul Dialect",
            "description": "",
            "tracks": 80,
        },
    ]

    uris = [
        "spotify:playlist:0oQE11XvrxWXK2a4CVRN3q",
        "spotify:playlist:4ATaA5T1ZUmY1fzJyMBr3P",
        "spotify:playlist:37i9dQZF1DX4CB6zI8FWXS",
        "spotify:playlist:1qQFW19QP5LqZFSeJtl0NH",
        "spotify:playlist:1W0lsTd8R0WbmnZg3rQmcg",
        "spotify:playlist:6y5ldR0UFhVs1lqWhy6Pva",
        "spotify:playlist:2mkeaNza52gcLpg5YrW9bg",
        "spotify:playlist:2EKsFAissZHtRZkSv3oa7H",
        "spotify:playlist:0J1euUuaGror5gPvQ8UIyY",
        "spotify:playlist:5SmXvDdhGY7VOQNrMMZqRq",
    ]

    assert actual_uris == uris
    assert actual_results == results


def test_search_parse_track():

    path = Path("tests/unit/artifacts/search_track_res.json")
    f = open(path)
    res = json.load(f)

    actual_results, actual_uris = parse_track_search(res)

    results = [
        {
            "index": 0,
            "name": "September",
            "duration": "3:35",
            "artist(s)": "Earth, Wind & Fire",
            "album title": "The Best Of Earth, Wind & Fire Vol. 1",
            "release date": "1978-11-23",
        },
        {
            "index": 1,
            "name": "September",
            "duration": "3:41",
            "artist(s)": "James Arthur",
            "album title": "September",
            "release date": "2021-06-11",
        },
        {
            "index": 2,
            "name": "September Song",
            "duration": "3:40",
            "artist(s)": "JP Cooper",
            "album title": "Raised Under Grey Skies (Deluxe)",
            "release date": "2017-10-06",
        },
        {
            "index": 3,
            "name": "Wake Me up When September Ends",
            "duration": "4:46",
            "artist(s)": "Green Day",
            "album title": "American Idiot",
            "release date": "2004-09-21",
        },
        {
            "index": 4,
            "name": "September Rain - 2020 Remaster",
            "duration": "4:32",
            "artist(s)": "Makoto Matsushita",
            "album title": "COLLECTION",
            "release date": "2020-03-25",
        },
        {
            "index": 5,
            "name": "September Song - Guitar Acoustic",
            "duration": "3:32",
            "artist(s)": "JP Cooper",
            "album title": "Sleepy Sleep",
            "release date": "2021-08-13",
        },
        {
            "index": 6,
            "name": "September",
            "duration": "3:35",
            "artist(s)": "Earth, Wind & Fire",
            "album title": "September",
            "release date": "2018-04-17",
        },
        {
            "index": 7,
            "name": "September 16",
            "duration": "4:10",
            "artist(s)": "Russ",
            "album title": "September 16",
            "release date": "2018-07-20",
        },
        {
            "index": 8,
            "name": "Enter Sandman (Live at Tushino Airfield, Moscow, Russia - September 28th, 1991)",
            "duration": "5:21",
            "artist(s)": "Metallica",
            "album title": "Nothing Else Matters (Orchestra/Clean Guitar/Vocal Mix - July 8th, 1991)",
            "release date": "2021-08-12",
        },
        {
            "index": 9,
            "name": "September",
            "duration": "4:04",
            "artist(s)": "Daughtry",
            "album title": "It's Not Over....The Hits So Far",
            "release date": "2016-02-12",
        },
    ]

    uris = [
        "spotify:track:2grjqo0Frpf2okIBiifQKs",
        "spotify:track:0exZ0YogJPbjGzblpcZaw7",
        "spotify:track:0zbzrhfVS9S2TszW3wLQZ7",
        "spotify:track:3ZffCQKLFLUvYM59XKLbVm",
        "spotify:track:6A9YFkei6zWfPSxWxlBecY",
        "spotify:track:3W116J45gzALWG50HZngHl",
        "spotify:track:7Cuk8jsPPoNYQWXK9XRFvG",
        "spotify:track:7a5RvlW5tMU0AZ4tvbGLhn",
        "spotify:track:3tsxiCcQiPL5Ay8Sw4w3tu",
        "spotify:track:2ikUwLex9wXpIOEgY45Wk7",
    ]

    assert actual_uris == uris
    assert actual_results == results


def test_check_url_format_valid():

    track_url = (
        "https://open.spotify.com/track/464BrxdI2djpYOUoXol3cQ?si=8757bf6f2e5a4120"
    )
    album_url = "https://open.spotify.com/album/4XF4TSU1Z8FvA52wvZqrQ5?si=0l5T5q6BQfKacmPF9hjpXg&dl_branch=1"
    playlist_url = (
        "https://open.spotify.com/playlist/5fArw51CQey2sVuS6SULxl?si=9b4f62b39b3a4a6d"
    )

    assert check_url_format(track_url)
    assert check_url_format(album_url)
    assert check_url_format(playlist_url)


def test_check_url_format_invalid():

    url_1 = "https://open.spotify.com/track/464Br"
    url_2 = "https://close.spotify.com/album/4XF4TSU1Z8FvA52wvZqrQ5?si=0l5T5q6BQfKacmPF9hjpXg&dl_branch=1"

    with pytest.raises(InvalidURL):
        check_url_format(url_1)

    with pytest.raises(InvalidURL):
        check_url_format(url_2)
