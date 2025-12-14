import network
import ujson as json
import time
import socket
from machine import Pin

g_led = Pin('LED', Pin.OUT)
g_led.off()

HTML_FORM = b"""HTTP/1.1 200 OK\r
Content-Type: text/html\r
\r
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Pico WiFi Debug</title>
</head>
<body>
  <h1>Pico WiFi debug form</h1>
  <form method="POST" action="/">
    <label>SSID:</label><br>
    <input type="text" name="ssid"><br><br>
    <label>Password:</label><br>
    <input type="password" name="password"><br><br>
    <button type="submit">Odeslat</button>
  </form>
</body>
</html>
"""
def parse_post_body(body: str):
    params = {}
    pairs = body.split("&")

    for pair in pairs:
        if not pair:
            continue
        if "=" in pair:
            key, value = pair.split("=", 1)
        else:
            key, value = pair, ""
        
        key = key.strip()
        value = value.replace("+", " ")

        params[key] = value
    return params

def run_debug_http_server(host="0.0.0.0", port=80):
    addr_info = socket.getaddrinfo(host, port)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr_info)
    s.listen(1)

    print("HTTP debug server listening on", addr_info)

    while True:
        client_sock, client_addr = s.accept()
        print("Client connected from", client_addr)

        try:
            raw = client_sock.recv(1024)
            if not raw:
                client_sock.close()
                continue

            req_str = raw.decode()

            print("========== RAW REQUEST BEGIN ==========")
            print(req_str)
            print("=========== RAW REQUEST END ===========")

            first_line = req_str.split("\r\n")[0]
            parts = first_line.split(" ")
            method = parts[0] if len(parts) > 0 else ""
            path = parts[1] if len(parts) > 1 else ""

            if method == "GET" and path == "/":
                client_sock.sendall(HTML_FORM)
                client_sock.close()
                continue

            if not (method == "POST" and path == "/"):
                client_sock.sendall(HTML_FORM)
                client_sock.close()
                continue

            if "\r\n\r\n" in req_str:
                headers_str, body = req_str.split("\r\n\r\n", 1)
            else:
                headers_str = req_str
                body = ""
            
            content_length = 0
            for line in headers_str.split("\r\n"):
                if line.lower().startswith("content-length:"):
                    content_length = int(line.split(":", 1)[1].strip())
            
            body_bytes = body.encode()
            missing = content_length - len(body_bytes)

            while missing > 0:
                chunk = client_sock.recv(1024)
                if not chunk:
                    break
                body_bytes += chunk
                missing = content_length - len(body_bytes)

            full_body = body_bytes.decode()

            print("FULL BODY:", full_body)

            params = parse_post_body(full_body)
            ssid = params.get("ssid", "").strip()
            password = params.get("password", "").strip()

            print(f"PARSED SSID: {ssid}")
            print(f"PARSED PASSWORD: {password}")

            if ssid and password:
                save_wifi_config(ssid, password)
                response = b"""HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nWiFi config saved. You can reboot the device now.\r\n"""
            else:
                response = b"""HTTP/1.1 400 Bad Request\r\nContent-Type: text/plain\r\n\r\nMissing ssid or password.\r\n"""
            client_sock.sendall(response)

        except Exception as e:
            print("Error in HTTP server:", e)

        finally:
            client_sock.close()

def save_wifi_config(ssid: str, password: str, path: str = "wifi_config.json"):
    data = {
        "ssid" : ssid,
        "password" : password,
    }
    with open(path, "w") as f:
        json.dump(data, f)
    print(f"Saved wifi config for {ssid}")

def load_wifi_config(path: str = "wifi_config.json"):
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except OSError:
        raise RuntimeError("wifi_config.json not found")
    
    if "ssid" not in data or "password" not in data:
        raise RuntimeError("wifi_config.json is missing required fields")
    
    ssid = data["ssid"]
    password = data["password"]

    if not ssid:
        raise RuntimeError("WiFi SSID ,ust not be empty")
    
    return ssid, password

def connect_sta_from_config(timeout_ms: int = 10000):
    ssid, password = load_wifi_config()

    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    sta.connect(ssid, password)

    print(f"Connecting to WiFi SSID={ssid!r} ...")

    start = time.ticks_ms()
    while not sta.isconnected():
        if time.ticks_diff(time.ticks_ms(), start) > timeout_ms:
            raise RuntimeError("Failed to connect to WiFi within timeout")
        time.sleep(0.2)
    
    ip = sta.ifconfig()[0]
    print(f"STA connected, IP: {ip}")
    return sta, ip

def blink_led(led: Pin, last_ms, interval_ms=100):
    now = time.ticks_ms()
    if time.ticks_diff(now, last_ms) >= interval_ms:
        led.toggle()
        return now
    return last_ms

class APConfig:
    """Config access point"""
    def __init__(self, ssid : str, password : str):
        self.ssid = ssid
        self.password = password

class AccessPoint:
    """Higl level wrapper around network.WLAN(AP_IF)."""
    def __init__(self, config: APConfig, led: Pin | None = None, debug: bool = True):
        self._config = config
        self._led = led
        self._debug = debug
        self._ap = network.WLAN(network.AP_IF)
    
    def _log(self, *args):
        if self._debug:
            print("[AP]", *args)
    
    def _wait_for_active(self, timeout_ms: int = 5000):
        start = time.ticks_ms()
        while not self._ap.active():
            if self._led is not None:
                blink_led(g_led, 0.1)

            if time.ticks_diff(time.ticks_ms(), start) > timeout_ms:
                raise RuntimeError("AP failed to start within timeout")
            
    def start(self):
        """Start and config AP"""
        self._log("Starting access point...")
        self._ap.active(True)

        self._ap.config(
            essid = self._config.ssid,
            password = self._config.password,
        )

        ip = self.ip()
        
        self._wait_for_active()

        self._log(f"AP live, SSID={self._config.ssid}, IP={ip}")
        print("AP live")
        print("SSID:", self._config.ssid)
        print("IP:  ", ip)

    def stop(self):
            """Turn of AP if running"""
            if self._ap.active():
                self._log("Stopping access point...")
                self._ap.active(False)

    def is_running(self) -> bool:
            return self._ap.active()
        
    def ip(self) -> str:
            """Return IP address AP (str)"""
            return self._ap.ifconfig()[0]
    
def load_config(path="config.json"):
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except OSError:
        raise RuntimeError("Missing config.json on device!")
    if "ssid" not in data or "password" not in data:
        raise RuntimeError("Config.json is missing required fields!")
    
    ssid =  data["ssid"]
    password = data["password"]

    return APConfig(ssid=ssid, password=password)

def main():
    # config = load_config()
    # ap = AccessPoint(config, led=g_led, debug=True)
    # ap.start()

    # run_debug_http_server()
    try:
        sta, ip = connect_sta_from_config()
        print(f"Connected, STA IP: {ip}")
        while True:
            time.sleep(1)
    except Exception as e:
        print(f"STA connect failed: " ,e)
if __name__ == "__main__":
    main()