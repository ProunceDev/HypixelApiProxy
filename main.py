from flask import Flask, request, jsonify
import requests, time, json, os
from mojang import API

app = Flask(__name__)

mojangAPI = API()

# Configuration
HYPIXEL_API_KEY = "Enter key here"
HOST_IP = "0.0.0.0"
HOST_PORT = "8000"
DEBUG = True

def divide(a, b):
	try:
		return a/b
	except ZeroDivisionError:
		return a

class InvalidPlayerError(Exception):
	"""Invalid player was entered"""
	pass

class Cache:
	def __init__(self, cache_folder="cache_data", expiration_time=900):
		self.cache_folder = cache_folder
		self.expiration_time = expiration_time

		# Ensure the cache folder exists
		if not os.path.exists(self.cache_folder):
			os.makedirs(self.cache_folder)

	def get_cached_data(self, name):
		cache_file = self._get_cache_file_path(name)
		if os.path.exists(cache_file):
			with open(cache_file, 'r') as file:
				cached_data = json.load(file)
				data, timestamp = cached_data
				if time.time() - timestamp < self.expiration_time:
					return data
				else:
					self._remove_from_cache(name)
		return None

	def cache_data(self, name, data):
		cache_file = self._get_cache_file_path(name)
		cached_data = (data, time.time())
		with open(cache_file, 'w') as file:
			json.dump(cached_data, file)

	def _get_cache_file_path(self, name):
		# Generate a safe filename for the cache file
		return os.path.join(self.cache_folder, f"{name}.json")

	def _remove_from_cache(self, name):
		cache_file = self._get_cache_file_path(name)
		if os.path.exists(cache_file):
			os.remove(cache_file)

class HypixelAPI:
	def __init__(self, key) -> None:
		self.key = key
		self.cache = Cache(cache_folder="proxy_cache")
	
	def GetPlayerData(self, username) -> dict:
		username = username.lower()
		cached_data = self.cache.get_cached_data(username)
		if cached_data:
			print(f"Loaded data from cache for {username}")
			if 'player' in cached_data:
				return cached_data
		
		data = self._get_data(username)
		if 'player' in data:
			self.cache.cache_data(username, data)
		else:
			raise InvalidPlayerError("Invalid player was entered")
		print(f"Retrieved fresh data for {username}")
		return data
	
	def RefineBedwarsStats(self, data, _level) -> dict:
		_total_final_kills = self._get_total(data, "final_kills_bedwars", ("void_", "attack_", "magic_", "fall_", "underworld_"))
		_total_final_deaths = self._get_total(data, "final_deaths_bedwars", ("void_", "attack_", "magic_", "fall_", "underworld_"))
		_fkdr = divide(_total_final_kills, _total_final_deaths)
		_total_kills = self._get_total(data, "kills_bedwars", ("final_", "void_", "attack_", "magic_", "fall_", "underworld_"))
		_total_deaths = self._get_total(data, "deaths_bedwars", ("final_", "void_", "attack_", "magic_", "fall_", "underworld_"))
		_kdr = divide(_total_kills, _total_deaths)
		_total_games_played = self._get_total(data, "games_played_bedwars")
		_total_games_won = self._get_total(data, "wins_bedwars")
		_total_games_lost = self._get_total(data, "losses_bedwars") + self._get_total(data, "lossesbedwars")
		_wlr = divide(_total_games_won, _total_games_lost)
		return {
				'final_kills':  _total_final_kills,
				'final_deaths': _total_final_deaths,
				'fkdr':		 _fkdr,
				'kills':		_total_kills,
				'deaths':	   _total_deaths,
				'kdr':		  _kdr,
				'wins':		 _total_games_won,
				'losses':	   _total_games_lost,
				'games_played': _total_games_played,
				'winrate':	  _wlr,
				'level':		_level
				}
	
	def GetLast30DayStats(self, last_30_days, Statistics, current_level) -> dict:
		_total_final_kills = Statistics['final_kills'] - last_30_days['final_kills']
		_total_final_deaths = Statistics['final_deaths'] - last_30_days['final_deaths']
		_fkdr = divide(_total_final_kills, _total_final_deaths)
		_total_kills = Statistics['kills'] - last_30_days['kills']
		_total_deaths = Statistics['deaths'] - last_30_days['deaths']
		_kdr = divide(_total_kills, _total_deaths)
		_total_games_played = Statistics['games_played'] - last_30_days['games_played']
		_total_games_won = Statistics['wins'] - last_30_days['wins']
		_total_games_lost = Statistics['losses'] - last_30_days['losses']
		_wlr = divide(_total_games_won, _total_games_lost)
		_level = current_level -  last_30_days['level']
		return {
				'final_kills':  _total_final_kills,
				'final_deaths': _total_final_deaths,
				'fkdr':		 _fkdr,
				'kills':		_total_kills,
				'deaths':	   _total_deaths,
				'kdr':		  _kdr,
				'wins':		 _total_games_won,
				'losses':	   _total_games_lost,
				'games_played': _total_games_played,
				'winrate':	  _wlr,
				'levels_gained':_level
				}

	def _get_data(self, username) -> dict:
		username = username.lower()
		data = requests.get(url = "https://api.hypixel.net/player", params = {"key": self.key, "name": username}).json()
		return data
	
	def _get_total(self, data, value, exclude_list=()) -> int:
		total = 0
		for key in data:
			if value == key:
				if not any(exclude in key for exclude in exclude_list):
					total += data[key]
		return total

@app.route('/player', methods=['GET'])
def get_player_stats():
	username = request.args.get('username')
	uuid = request.args.get('uuid')
	if uuid != None:
		username = mojangAPI.get_username(uuid)

	if not username:
		return jsonify({"error": "Username or UUID is required"}), 400

	try:
		data = API.GetPlayerData(username)

		if not data.get("success", False):
			return jsonify({"error": data.get("cause", "Unknown error")}), 400

		# Return the player's data
		return jsonify(data)
	
	except requests.RequestException as e:
		return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
	API = HypixelAPI(HYPIXEL_API_KEY)
	app.run(host=HOST_IP,port=HOST_PORT, debug=DEBUG)