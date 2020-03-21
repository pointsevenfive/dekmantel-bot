#/bin/usr/python

from bs4 import BeautifulSoup, Tag
import requests
import urllib.parse as parse
import json
import creds
import base64
import spotify_login as spotify
import re as regex

MAX_TRACKS = 10

RA_SEARCH = 'https://www.residentadvisor.net/search.aspx?searchstr={artist}'
RA_TRACKS = 'https://www.residentadvisor.net{link}/tracks?sort=mostcharted'
API_SPOTIFY = 'https://api.spotify.com'
OPEN_SPOTIFY = 'https://open.spotify.com'
ACCT_SPOTIFY = 'https://accounts.spotify.com'

status_codes = {}
artist_most_charted = {}

festival_artists = open('list_artists.txt')

def log_response(url, rsp_code, content):
    code = str(rsp_code)
    status_codes[url] = code
    print('Received {code} response from {url}'.format(code=code, url=url))

def get_oauth_spotify():
    url = ACCT_SPOTIFY + '/api/token'
    data = 'grant_type=client_credentials'
    auth = str(base64.urlsafe_b64encode((creds.spotify_client_id + ':' + creds.spotify_client_secret).encode()), 'utf-8')
    headers = {
        'Authorization': 'Basic {auth}'.format(auth=str(auth)),
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.post(url, data=data, headers=headers)
    oauth = json.loads(response.content)
    log_response(url, response.status_code, response.content)
    return oauth.get('access_token')

def append_spotify_query_string(endpoint, track, query_type):
    track = track.replace(' ', '+')
    query = endpoint + '?q={track}&type={type}'.format(track=track, type=query_type)
    return regex.sub('(#|\(|\)|&amp)', ' ', query)

def get_track_id_from_response(reponse):
    items = reponse['tracks']['items']
    if len(items) > 0:
        track_id = items[0]['id']
        return track_id
    return ''

def query_spotify(spotify_auth, artist, title):
    spotify_search = API_SPOTIFY + '/v1/search'
    query_type = 'track'
    track = '{artist} - {track}'.format(artist=artist, track=title)
    headers = {'Authorization': 'Bearer ' + spotify_auth}
    url = append_spotify_query_string(spotify_search, track, query_type)
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return get_track_id_from_response(json.loads(response.content))
    return ''


def append_track_to_master_list(spotify_auth, artist_name, track_div):
    track_data = {}
    track_data['artist'] = artist_name
    if len(track_div.contents) > 0:
        track = track_div.contents[0]
        if isinstance(track, Tag):
            if len(track.contents) > 0:
                track_data['title'] = track.contents[0]
        elif not isinstance(track, Tag):
            track_data['title'] = track

        if 'title' in track_data:
            track_data['id'] = query_spotify(spotify_auth, artist_name,track_data['title'])
            if track_data['id'] != '':
                artist_most_charted[artist_name].append(track_data)
                print('\t{track}'.format(track=track_data))

def extract_tracks(spotify_auth, artist_name, response):
    soup = BeautifulSoup(response.content, 'html.parser')
    track_table = soup.find(id='tracks')
    if track_table is not None:
        list_items = track_table.find_all('li')
        for item in list_items:
            track_div = item.find(class_='title')
            append_track_to_master_list(spotify_auth, artist_name, track_div)

def search_tracks(spotify_auth, artist_name, response):
    soup = BeautifulSoup(response.content, 'html.parser')
    found_result = soup.find('div', class_='pb4')
    if found_result is not None and 'An exact artist match was found...' in found_result:
        artist_link = soup.find('a', class_='f24')
        response = requests.get(RA_TRACKS.format(link=artist_link['href']))
        if response.status_code == 200:
            extract_tracks(spotify_auth, artist_name, response)

def search_artist(spotify_auth, artist_name):
    response = requests.get(RA_SEARCH.format(artist=parse.quote_plus(artist_name.encode('utf-8'))))
    if response.status_code == 200:
        search_tracks(spotify_auth, artist_name, response)

def mine_tracks():
    spotify_auth = get_oauth_spotify()
    for artist in festival_artists:
        artist_name = artist.rstrip('\n')
        print(artist_name)
        artist_most_charted[artist_name] = []
        search_artist(spotify_auth, artist_name)

def chunks(uri_list, n):
    for i in range(0, len(uri_list), n):
        yield uri_list[i:i + n]

def get_tracks_json():
    track_uris = []
    batch = []
    for artist in artist_most_charted:
        tracks = artist_most_charted[artist]
        for track in tracks:
            track_uri = 'spotify:track:{id}'.format(id=str(track['id']))
            track_uris.append(track_uri)
    return chunks(track_uris, 100)

def add_tracks(playlist_id, auth):
    url = API_SPOTIFY + '/v1/playlists/{id}/tracks'.format(id=playlist_id)
    headers = {
        'Authorization': 'Bearer {token}'.format(token=auth),
        'Content-Type': 'application/json'
    }
    tracks_split = get_tracks_json()
    for batch_tracks in tracks_split:
        uris = {}
        uris['uris'] = batch_tracks
        response = requests.post(url, data=json.dumps(uris['uris']), headers=headers)
        log_response(url, response.status_code, response.content)
    return OPEN_SPOTIFY + '/user/{user_id}/playlist/{id}'.format(user_id=creds.spotify_uname, id=playlist_id)

def create_playlist():
    auth = spotify.login_to_spotify()
    url = API_SPOTIFY + '/v1/users/{id}/playlists'.format(id=creds.spotify_uname)
    playlist_name = 'Dekmantel Selektorz'
    description = 'A playlist of the selektorz playing at Dekmantel this year'
    data = {
        'name': playlist_name,
        'public': True,
        'description': description
    }
    headers = {
        'Authorization': 'Bearer {token}'.format(token=auth),
        'Content-Type': 'application/json'
    }
    response = requests.post(url, data=json.dumps(data), headers=headers)
    log_response(url, response.status_code, response.content)
    playlist_json = json.loads(response.content)
    return add_tracks(playlist_json['id'], auth)

mine_tracks()
create_playlist()
