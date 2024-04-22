import pyshark

capture = pyshark.LiveCapture()

for packet in capture.sniff_continuously():
    print(packet)