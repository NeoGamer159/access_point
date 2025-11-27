import network
import ujson as json
import time
from machine import Pin

g_led = Pin('LED', Pin.OUT)
g_led.off()



def load_config(path="config.json"):
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except OSError:
        raise RuntimeError("Missing config.json on device!")
    if "ssid" not in data or "password" not in data:
        raise RuntimeError("Config.json is missing required fields!")
    return data["ssid"], data["password"]



def start_ap():
    ap = network.WLAN(network.AP_IF) # Create object for access point
    AP_SSID, AP_PASSWORD = load_config()
    ap.config(essid=AP_SSID, password=AP_PASSWORD)
    ap.active(True)

    while not ap.active():
        g_led.on()
        time.sleep(0.1)
        g_led.off()
    
    g_led.off()

    ip_info = ap.ifconfig()
    ip = ip_info[0]

    print("AP live")
    print("SSID:", AP_SSID)
    print("IP: ", ip)

    return ap, ip

def main():
    ap, ip = start_ap()

    while True:
        time.sleep(1)

main()