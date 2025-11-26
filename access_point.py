import network
import time
from machine import Pin

g_led = Pin('LED', Pin.OUT)
g_led.off()

AP_SSID = "PicoSetup"
AP_PASSWORD = "lordakiuM159"

def start_ap():
    ap = network.WLAN(network.AP_IF) # Create object for access point
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