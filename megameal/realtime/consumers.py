from koms.views import stationCategoryWise,CategoryWise,statuscount, waiterdata,webSocketPush,allStationData,stationdata,notify
from static.order_status_const import WHEELSTATS, STATION, STATIONSIDEBAR, STATUSCOUNT,MESSAGE, WOMS
from woms.views import gettable,filterTables
from koms.views import getOrder, stationQueueCount
from pos.views import order_data, order_data_start_thread
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from koms.models import Order
from woms.models import Floor
from datetime import datetime
import json
import re


class ChatConsumer(WebsocketConsumer):
    def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = 'chat_%s' % str(self.room_name).replace(" ","")
        self.user = self.scope["user"]
        if str(self.user)=="AnonymousUser":
            ## Uncomment if needed to disconnect when token is invalid
            # self.accept()
            # self.send(text_data=json.dumps({}))
            # self.disconnect()
            print("")
        
        # Join room group
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )
        # print("self.room_group_name",self.room_group_name)
        print("self.room_name",self.room_name)


        result = {}
        
        if str(self.room_name).__contains__(WHEELSTATS):
            vendorId= str(self.room_name).replace(WHEELSTATS,'')
            result=stationQueueCount(vendorId=vendorId)

        elif str(self.room_name).__contains__("POS") and not str(self.room_name).__contains__("WOMS") and not str(self.room_name).__contains__("MESSAGE"):
            id = str(self.room_name).replace("POS",'')
            
            if id.__contains__("-"):
                data = id.split("-")

                if data[0]:
                    order_status = int(data[0])
                else:
                    order_status = "All"

                if data[1]:
                    search = data[1]
                else:
                    search = "All"

                if data[2]:
                    platform = int(data[2])
                else:
                    platform = "All"

                if data[3]:
                    order_type = int(data[3])
                else:
                    order_type = "All"

                if data[4]:
                    page_number = int(data[4])
                else:
                    page_number = 1

                if data[5]:
                    s_date = data[5]
                else:
                    s_date = None

                if data[6]:
                    e_date = data[6]
                else:
                    e_date = None

                if data[7]:
                    is_dashboard = int(data[7])
                else:
                    is_dashboard = 0

                if data[8]:
                    language = data[8]
                else:
                    language = "en"
                
                if data[9]:
                    vendorId = int(data[9])
                else:
                    vendorId = None

                result = order_data_start_thread(
                    vendor_id=vendorId, page_number=page_number, search=search, order_status=order_status, order_type=order_type,
                    platform=platform ,s_date=s_date,e_date=e_date, is_dashboard=is_dashboard, language=language
                )

        elif str(self.room_name) == STATIONSIDEBAR:
            result=CategoryWise()
        elif str(self.room_name).__contains__(STATIONSIDEBAR):
            print(STATIONSIDEBAR)
            stationId=str(self.room_name).replace(STATIONSIDEBAR, '')
            print("station",stationId)
            ###Query param
            query_string = self.scope['query_string'].decode('utf-8')
            query_params = dict(qc.split("=") for qc in query_string.split("&"))
            vendorId = query_params.get('vendorId')
            result ={} if str(self.user)=="AnonymousUser" else stationCategoryWise(id=stationId,vendorId=vendorId)
        elif str(self.room_name).__contains__(STATUSCOUNT):
            vendorId= str(self.room_name).replace(STATUSCOUNT,'')
            result=statuscount(vendorId=vendorId)
        elif str(self.room_name) == MESSAGE:
            result={
                    "type": "chat_message",
                    "message": {
                        "type": 0,
                        "orderId": 0,
                        "description":"",
                        "station":""
                    },
                    "username": "CORE"
                }
        elif str(self.room_name).__contains__(MESSAGE):
            # pattern = r"^(.*?)-(\d+)-(\d+)$"
            # match = re.match(pattern, self.room_name)
            match = str(self.room_name).split("-")
            if match:
                message = match[0]  # "MESSAGE"
                vendorId = int(match[1])  # 1
                stationId = match[2] # 2
                result={
                    "type": "chat_message",
                    "message": {
                        "type": 0,
                        "orderId": 0,
                        "description":"",
                        "station":[stationId],
                        "vendorId":vendorId,
                        "status":0,
                        "order_type":0
                    },
                    "username": "CORE"
                }
            else:
                print("No match foundfor ",self.room_name)
                result={}
        elif str(self.room_name).__contains__(WOMS) and not str(self.room_name).__contains__("STATION"):
            id= str(self.room_name).replace(WOMS,'')
            
            if id.__contains__("-"):
                data = id.split("-")
                waiterId = data[0]
                filter = data[1] or "All"
                search = data[2] or "All"
                status = [data[3] if data[3] != "OutOfService" else "Out Of Service"][0] or "All"
                waiter = data[4] or "All"
                floor = data[5] or ""
                language = data[6]
                vendorId = data[7]
                
                if data[5] == "":
                    floor = Floor.objects.filter(is_active=True, vendorId=vendorId).first().pk
                
                result = {
                    "type": "waiter in the room",
                    "tables": filterTables(
                        waiterId=waiterId, filter=filter, search=search, status=str(status), waiter=waiter,
                        floor=floor, language=language, vendorId=vendorId
                    )
                }

            else:
                result = {
                    "type": "waiter in the room",
                    "tables": gettable(id=id, vendorId=vendorId, language=language)
                }

        else:
            date = datetime.today().strftime("20%y-%m-%d")
            if str(self.room_name) == STATION:
                if str(self.user)=="AnonymousUser":
                    result={}

                else:
                    result = allStationData()
            elif str(self.room_name).__contains__(STATION):
                stationId=str(self.room_name).replace(STATION, '')
                ###Query param
                try:
                    query_string = self.scope['query_string'].decode('utf-8')
                    query_params = dict(qc.split("=") for qc in query_string.split("&"))
                    vendorId = query_params.get('vendorId')
                except:
                    print("Unable to parse query_string")

                if str(stationId).__contains__(WOMS):
                    id=str(stationId).replace(WOMS, '')
                    data=id.split("-")
                    waiterId=data[0]
                    filter=data[1] or "All"
                    search=data[2] or "All"
                    vendorId=data[3]
                    result=waiterdata(id=waiterId,filter=filter,search=search,vendorId=vendorId)
                else:
                    if str(self.user)=="AnonymousUser":
                        result={}
                    else:
                        result = stationdata(id=stationId, vendorId=vendorId)
            else:
                pattern = r"^(\d+)-(\d+)$"
                match = re.match(pattern, self.room_name)
                if match:
                    vendorId=int(match.group(1))
                    orderStatus=int(match.group(2))
                else:
                    vendorId=-1
                    orderStatus=-1
                    print("Match notfound")
                orderList = Order.objects.filter(order_status=orderStatus, arrival_time__contains=date,vendorId=vendorId)
                
                for singleOrder in orderList:
                    mapOfSingleOrder = getOrder(ticketId=singleOrder.pk,vendorId=vendorId)
                    result[singleOrder.externalOrderId] = mapOfSingleOrder
                result=dict(sorted(result.items(), key=lambda x: not x[1]["isHigh"]))  # puts tickets with isHigh=True at the begining
        self.accept()
        self.send(text_data=json.dumps(result))

    def disconnect(self, close_code, ):
        print(f"disconnect: {self.room_group_name}")
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    def receive(self, text_data):
        print("Receive")
        print("receive room_name : " + str(self.room_name) + " , group_name : " + str(
            self.room_group_name) + ", channel : " + str(self.channel_name))
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        # Send message to room group
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'username': self.user.username,
                'date': str(datetime.now().strftime("%Y-%m-%d %H:%M"))
            }
        )
    

    # Receive message from room group
    def chat_message(self, event, type='chat_message'):
        print("Chat Message")
        message = event['message']
        username = event['username']

        # Send message to WebSocket

        self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': message,
            'username': username,
        }))
