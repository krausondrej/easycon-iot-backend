import json

from django.conf import settings
from django.shortcuts import get_object_or_404, redirect

from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from pymongo import MongoClient
import paho.mqtt.publish as publish

from .models import Device
from .serializers import DeviceSerializer

from django.contrib.auth import logout


@api_view(['GET'])
def get_data(request):
    client_param = request.GET.get('client')
    try:
        mongo = MongoClient(settings.MONGO_URI)
        db = mongo.get_database()
        query = {}
        if client_param is not None:
            query['device_id'] = int(client_param)

        docs = list(
            db.modbus_data
              .find(query)
              .sort('timestamp', -1)
              .limit(50)
        )
    except ValueError:
        return Response({'error': 'Invalid client id, must be integer'},
                        status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': f'Database error: {str(e)}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # JSON serializace
    for d in docs:
        d['_id'] = str(d['_id'])
    return Response(docs)


class DeviceViewSet(viewsets.ModelViewSet):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer

    # GET /api/clients/id/readings/
    @action(detail=True, methods=['get'])
    def readings(self, request, pk=None):
        get_object_or_404(Device, pk=pk)
        try:
            mongo = MongoClient(settings.MONGO_URI)
            db = mongo.get_database()
            docs = list(
                db.modbus_data
                  .find({'device_id': int(pk)})
                  .sort('timestamp', -1)
                  .limit(50)
            )
        except Exception as e:
            return Response({'error': f'Database error: {str(e)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        for d in docs:
            d['_id'] = str(d['_id'])
        return Response(docs)

    # POST /api/clients/id/control/
    @action(detail=True, methods=['post'])
    def control(self, request, pk=None):
        cmd = request.data.get('command')
        if not isinstance(cmd, str) or not cmd.strip():
            return Response({'error': 'command must be a non-empty string'},
                            status=status.HTTP_400_BAD_REQUEST)

        device = get_object_or_404(Device, pk=pk)

        topic = f"client/{device.id}/control"
        payload = json.dumps({'command': cmd})

        # MQTT autentizace z settings
        auth = {
            'username': settings.MQTT_USERNAME,
            'password': settings.MQTT_PASSWORD,
        }
        try:
            publish.single(
                topic,
                payload,
                hostname=settings.MQTT_HOST,
                port=int(settings.MQTT_PORT),
                auth=auth,
            )
        except Exception as e:
            return Response({'error': f"MQTT publish failed: {str(e)}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'status': 'sent', 'topic': topic, 'payload': payload})
    
def logout_view(request):
    logout(request)
    return redirect('login')
