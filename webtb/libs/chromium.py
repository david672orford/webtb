import json
import tempfile
import shutil
import re
import subprocess
from time import sleep

import websocket

class CDP:
	def __init__(self, debug:bool):
		self.debug = debug
		self.id = 1

		# Launch Chrome in headless mode with a temporary profile
		if self.debug:
			print(" Starting Chrome...")
		chrome_cmd = [
			"chromium",
			"--headless=new",
			"--remote-debugging-port=0",
			"--window-size=1280,720",
			"--disable-gpu",
			"--mute-audio",
			"--disable-blink-features=RemoteFonts",
			"--allow-file-access-from-files",			# allow file:// URLs
			]
		self.temp_profile = tempfile.mkdtemp(prefix="webtb_chrome_")
		chrome_cmd.append(f"--user-data-dir={self.temp_profile}")
		self.chrome = subprocess.Popen(
			chrome_cmd,
			stdout = subprocess.DEVNULL,
			stderr = subprocess.PIPE,
			text = True,
			)

		# Find the URL of the CDP websocket
		assert self.chrome.stderr is not None
		for line in self.chrome.stderr:
			m = re.search(r"^DevTools listening on (ws://[^\s]+)$", line)
			if m:
				browser_ws_url = m.group(1)
				break
		else:
			raise RuntimeError("Websocket URL for Chrome not found")

		self.ws = websocket.create_connection(browser_ws_url, suppress_origin=True)
		targets = self.cmd("Target.getTargets")
		target_id = targets["result"]["targetInfos"][0]["targetId"]
		self.ws.close()

		page_ws_url = browser_ws_url.split("/devtools/browser/")[0] + f"/devtools/page/{target_id}"
		self.ws = websocket.create_connection(page_ws_url, suppress_origin=True)

		response = self.cmd("Emulation.setDeviceMetricsOverride",
			width=1280,
			height=720,
			deviceScaleFactor=1,
			mobile=False,
			)
		assert response["result"] == {}

	def close(self):
		if self.debug:
			print("Shutting down Chrome...")
		self.ws.close()
		self.chrome.terminate()
		self.chrome.wait()
		for i in range(50):
			try:
				shutil.rmtree(self.temp_profile)
				break
			except (FileNotFoundError, OSError):
				sleep(.1)
		else:
			raise TimeoutError("Cannot delete temporary profile directory")

		if self.debug:
			print("Done.")

	def cmd(self, method:str, **params):
		self.ws.send(json.dumps({
			"id": self.id,
			"method": method,
			"params": params,
			}))
		response_json = self.ws.recv()
		response = json.loads(response_json)
		return response

	def navigate(self, url:str):
		if self.debug:
			print(f" Navigating to \"{url}\"...")
		response = self.cmd("Page.navigate", url=url)
		#print(response)

		# Wait for the page to finish loading.
		for i in range(10):
			response = self.cmd("Runtime.evaluate", expression="document.readyState")
			#print(response)
			state = response["result"]["result"]["value"]
			if self.debug:
				print(f" document.readyState: {state}")
			if state == "complete":
				break
			sleep(.5)
		else:
			raise TimeoutError("Page is still not ready")
