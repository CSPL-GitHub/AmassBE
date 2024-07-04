import json
import random
from datetime import datetime

from asgiref.sync import async_to_sync

from koms.models import Station
import socket

class Rooms:
    def connect(self):
        stationList = Station.objects.filter().all()#TODO addVendor
        for station in stationList:
            station.station_name
            WebSocket(
                'ws://'
                + socket.gethostname()
                + '/ws/chat/'
                + station.station_name
                + '/'
            )
