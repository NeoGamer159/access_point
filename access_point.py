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

def load_config(path="config.json"):
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except OSError:
        raise RuntimeError("Missing config.json on device!")
    if "ssid" not in data or "password" not in data:
        raise RuntimeError("Config.json is missing required fields!")
    return data["ssid"], data["password"]

def wait_for_ap(ap, timeout_ms = 5000):
    start = time.ticks_ms()
    while not ap.active():
        blink_led(g_led, 0.1)

        if time.ticks_diff(time.ticks_ms(), start) > timeout_ms:
            raise RuntimeError("AP failed to start within timeout")

def start_ap():
    ap = network.WLAN(network.AP_IF) 
    AP_SSID, AP_PASSWORD = load_config()
    
    ap.config(essid=AP_SSID, password=AP_PASSWORD)
    ap.active(True)

    wait_for_ap(ap)
    
    g_led.off()

    ip = ap.ifconfig()[0]

    print("AP live")
    print("SSID:", AP_SSID)
    print("IP: ", ip)

    return ap, ip

def main():
    ap, ip = start_ap()

    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()