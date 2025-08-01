import json
import time
import threading
from typing import Dict, Any, Callable

import redis
import structlog
from pymongo import MongoClient

logger = structlog.get_logger()

class EventConsumer:
    def __init__(self, redis_url: str, mongo_url: str, consumer_group: str, consumer_name: str):
        self.redis_client = redis.from_url(redis_url)
        self.mongo_client = MongoClient(mongo_url)
        self.consumer_group = consumer_group
        self.consumer_name = consumer_name
        self.event_handlers = {}
        self.running = False
        self.threads = []
        
    def register_handler(self, event_type: str, handler: Callable[[Dict[str, Any]], None]):
        """Enregistre un handler pour un type d'événement"""
        self.event_handlers[event_type] = handler
        
    def start_consuming(self, streams: list):
        """Démarre la consommation d'événements"""
        self.running = True
        
        for stream in streams:
            # Créer le consumer group s'il n'existe pas
            try:
                self.redis_client.xgroup_create(stream, self.consumer_group, id='0', mkstream=True)
            except redis.exceptions.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    raise
                    
            # Démarrer un thread pour chaque stream
            thread = threading.Thread(
                target=self._consume_stream,
                args=(stream,),
                daemon=True
            )
            thread.start()
            self.threads.append(thread)
            
        logger.info(
            "Started consuming events",
            consumer_group=self.consumer_group,
            consumer_name=self.consumer_name,
            streams=streams
        )
        
    def _consume_stream(self, stream: str):
        """Consomme les événements d'un stream"""
        while self.running:
            try:
                # Lire les nouveaux messages
                messages = self.redis_client.xreadgroup(
                    self.consumer_group,
                    self.consumer_name,
                    {stream: '>'},
                    count=1,
                    block=1000
                )
                
                for stream_name, msgs in messages:
                    for msg_id, fields in msgs:
                        if self._process_message(stream_name.decode(), msg_id.decode(), fields):
                            # Acquitter le message seulement si traité avec succès
                            self.redis_client.xack(stream, self.consumer_group, msg_id)
                        
                # Traiter les messages en attente (non-acknowledgés)
                pending_messages = self.redis_client.xpending_range(
                    stream,
                    self.consumer_group,
                    min='-',
                    max='+',
                    count=5
                )
                
                for pending in pending_messages:
                    msg_id = pending['message_id']
                    # Récupérer le message
                    msgs = self.redis_client.xrange(stream, msg_id, msg_id)
                    if msgs:
                        msg_id_str, fields = msgs[0]
                        if self._process_message(stream, msg_id_str.decode(), fields):
                            self.redis_client.xack(stream, self.consumer_group, msg_id)
                        
            except Exception as e:
                logger.error(
                    "Error consuming stream",
                    stream=stream,
                    error=str(e)
                )
                time.sleep(1)
                
    def _process_message(self, stream: str, msg_id: str, fields: Dict[bytes, bytes]) -> bool:
        """Traite un message événementiel"""
        try:
            # Décoder les champs
            event_data = {}
            for key, value in fields.items():
                event_data[key.decode()] = value.decode()
                
            event_type = event_data.get('event_type')
            
            if event_type in self.event_handlers:
                # Traiter l'événement
                self.event_handlers[event_type](event_data)
                
                logger.info(
                    "Event processed",
                    event_type=event_type,
                    event_id=event_data.get('event_id'),
                    msg_id=msg_id,
                    stream=stream
                )
                return True
            else:
                logger.warning(
                    "No handler for event type",
                    event_type=event_type,
                    msg_id=msg_id
                )
                return True  # Acquitter pour éviter la répétition
                
        except Exception as e:
            logger.error(
                "Error processing message",
                msg_id=msg_id,
                stream=stream,
                error=str(e)
            )
            return False  # Ne pas acquitter en cas d'erreur
            
    def stop_consuming(self):
        """Arrête la consommation d'événements"""
        self.running = False
        for thread in self.threads:
            thread.join()
        logger.info("Stopped consuming events")