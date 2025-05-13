import time
import json
import os
import base64
import requests

class SpotifyTokenManager:
    def __init__(self, client_id, client_secret, token_file="spotify_token.json"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_file = token_file

    def loadToken(self):
        if os.path.exists(self.token_file):
            with open(self.token_file, 'r') as file:
                return json.load(file)
        return None

    def saveToken(self, token_data):
        with open(self.token_file, 'w') as file:
            json.dump(token_data, file)

    def isTokenExpired(self, token_data):
        expiry_time = token_data.get("expiry_time", 0)
        return time.time() >= expiry_time

    def requestNewToken(self):
        url = "https://accounts.spotify.com/api/token"
        headers = {
            "Authorization": "Basic " + base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        }
        data = {"grant_type": "client_credentials"}

        try:
            response = requests.post(url, headers=headers, data=data)
            response.raise_for_status()
            token_info = response.json()
            # Calculate expiry time: current time + expires_in seconds
            expiry_time = time.time() + token_info['expires_in']
            token_info['expiry_time'] = expiry_time
            print("token acquired...")
            return token_info
        except Exception as e:
            print("Failed to get Spotify access token:", e)
            return None
        
    def getToken(self):
        token_data = self.loadToken()
        if token_data is None or self.isTokenExpired(token_data):
            print("Fetching new Spotify token...")
            token_data = self.requestNewToken()
            self.saveToken(token_data)
            return token_data['access_token']
        else:
            print("Using previous Spotify token...")
            return token_data['access_token']
