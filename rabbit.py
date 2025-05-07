import os
import pika
import json
import time
from api import api_handler
from logger import server_log
from dotenv import load_dotenv
from backuper import backuper


class RabbittManager:
    def __init__(self):
        # RabbitMQ connection parameters
        load_dotenv()
        self.rabbit_host = os.getenv('RABBITMQ_HOST', 'localhost')
        self.rabbit_port = int(os.getenv('RABBITMQ_PORT', 5672))
        self.rabbit_queue = os.getenv('RABBITMQ_QUEUE', 'backup_queue')
        self.rabbit_user = os.getenv('RABBITMQ_USER', 'guest')
        self.rabbit_pass = os.getenv('RABBITMQ_PASS', 'guest')
        self.connection = None
        self.channel = None
        server_log.info(f"Rabbit manager initialized")

    def _connect_rabbitmq(self):
        """Establish connection to RabbitMQ"""
        credentials = pika.PlainCredentials(self.rabbit_user, self.rabbit_pass)
        parameters = pika.ConnectionParameters(
            host=self.rabbit_host,
            port=self.rabbit_port,
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300
        )
        
        try:
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue=self.rabbit_queue, durable=True)
            server_log.info(f"Connected to RabbitMQ at {self.rabbit_host}:{self.rabbit_port}")
        except Exception as e:
            server_log.warning(f"Failed to connect to RabbitMQ: {str(e)}")
            raise


    def _process_message(self, ch, method, properties, body):
        """Callback for processing RabbitMQ messages"""
        try:
            message = json.loads(body)
            id = message.get('id')
            ip = message.get('ip')
            device = message.get('device')
            if not id or not ip or not device:
                server_log.warning("Invalid message format, missing id, ip or device field")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                return
            server_log.info(f"\nReceived backup request for IP: {ip} - {device}")
            time.sleep(5)
            if device == 'ubnt':
                api_handler.set_backup_status(id, backuper.backupUbnt(ip))
                ch.basic_ack(delivery_tag=method.delivery_tag)
            else:
                server_log.warning(f"Unknown device field {device}")
                api_handler.set_backup_status(id, f"Unknown device field {device}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        except json.JSONDecodeError:
            server_log.warning("Failed to parse JSON message")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as e:
            server_log.warning(f"Error processing message: {str(e)}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


    def start_listening(self):
        """Start listening for messages from RabbitMQ"""
        while True:
            try:
                if not self.connection or self.connection.is_closed:
                    self._connect_rabbitmq()

                server_log.info(f"Waiting for messages on queue {self.rabbit_queue}...")
                self.channel.basic_qos(prefetch_count=1)
                self.channel.basic_consume(
                    queue=self.rabbit_queue,
                    on_message_callback=self._process_message,
                    auto_ack=False
                )
                self.channel.start_consuming()
                
            except pika.exceptions.AMQPConnectionError:
                server_log.warning("Connection lost, attempting reconnect in 5 seconds...")
                time.sleep(5)
            except Exception as e:
                server_log.warning(f"Unexpected error: {str(e)}, reconnecting...")
                time.sleep(5)

rabbit_manager = RabbittManager()
