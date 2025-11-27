import network
import ujson as json
import time
from machine import Pin

g_led = Pin('LED', Pin.OUT)
g_led.off()

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
    config = load_config()
    ap = AccessPoint(config, led=g_led, debug=True)
    
    ap.start()

    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()