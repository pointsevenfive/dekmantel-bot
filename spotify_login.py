from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
import creds
import urllib.parse as parse
import random

user_auth_url = 'https://accounts.spotify.com/authorize?' \
                'client_id=' + creds.spotify_client_id + '&' \
                'response_type=token' + '&' \
                'redirect_uri=' + str(parse.quote_plus(creds.callback_url)) + '&' \
                'state=userauth' + '&' \
                'scope=playlist-modify-public' + '&' \
                'show_dialog=false'

def login_to_spotify():
    options = Options()
    options.headless = True
    print('Starting webdriver...')
    driver = webdriver.Firefox(options=options, executable_path='./geckodriver.exe')
    driver.get(user_auth_url)
    print('Logging in to spotify...')
    txt_login = driver.find_element_by_id('login-username')
    txt_login.send_keys(creds.spotify_uname)
    txt_passw = driver.find_element_by_id('login-password')
    txt_passw.send_keys(creds.spotify_passw)
    btn_click = driver.find_element_by_id('login-button')
    btn_click.click()
    wait = WebDriverWait(driver, 10)
    wait.until(lambda driver: driver.title.startswith('GitHub'))
    redirect_url = driver.current_url
    print('Logged in and user token received')
    driver.quit()
    return get_token_from_url(redirect_url)

def get_token_from_url(url):
    response = url.replace('https://github.com/pointsevenfive/spotify-bot/#', '')
    segments = response.split('&')
    return segments[0].replace('access_token=', '')