import RPi.GPIO as GPIO
import MFRC522
import signal
import sys
from time import sleep
from gatekeeper import Gatekeeper


if sys.version_info[0] < 3:
    raise "Python 3.x required to run"



reader = MIFAREReader = MFRC522.MFRC522()

door = GateKeeper('http://192.168.1.100/members/auth/')


while True:
    (status, data) = MIFAREReader.MFRC522_Request(MIFAREReader.PICC_REQIDL) 
    if status == IFAREReader.MI_OK:
        pass
    else:
        print("PICC_REQIDL error: {}".format(status))
        break



    (status, data) = MIFAREReader.MFRC522_Anticoll()
    if status == IFAREReader.MI_OK:
        uid = ''
        for byte in data[:-1]:
            uid += hex(byte)[2:]
        door.authenticate(uid)
    else:
        print("PICC_AntiColl error: {}".format(status))
        break
    
    sleep(1)
    