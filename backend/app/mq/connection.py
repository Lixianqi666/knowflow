"""RabbitMQ 连接管理"""

import logging
import os

import pika

logger = logging.getLogger(__name__)

EXCHANGE = "knowflow.task.direct"
QUEUE_INDEX = "knowflow.index.command"
QUEUE_RETRY = "knowflow.index.retry"
QUEUE_DLQ = "knowflow.index.dlq"
RK_INDEX = "index.command"
RK_RETRY = "index.retry"
RK_DLQ = "index.dlq"


def get_connection() -> pika.BlockingConnection:
    url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    params = pika.URLParameters(url)
    return pika.BlockingConnection(params)


def setup_topology(channel: pika.channel.Channel):
    """声明 Exchange、Queue、Binding"""
    channel.exchange_declare(exchange=EXCHANGE, exchange_type="direct", durable=True)

    # 主队列：失败路由到 retry
    channel.queue_declare(
        queue=QUEUE_INDEX,
        durable=True,
        arguments={
            "x-dead-letter-exchange": EXCHANGE,
            "x-dead-letter-routing-key": RK_RETRY,
        },
    )

    # 重试队列：TTL 30s 后回主队列
    channel.queue_declare(
        queue=QUEUE_RETRY,
        durable=True,
        arguments={
            "x-dead-letter-exchange": EXCHANGE,
            "x-dead-letter-routing-key": RK_INDEX,
            "x-message-ttl": 30_000,
            "x-max-length": 1000,
        },
    )

    # 死信队列
    channel.queue_declare(queue=QUEUE_DLQ, durable=True)

    channel.queue_bind(QUEUE_INDEX, EXCHANGE, RK_INDEX)
    channel.queue_bind(QUEUE_RETRY, EXCHANGE, RK_RETRY)
    channel.queue_bind(QUEUE_DLQ, EXCHANGE, RK_DLQ)

    logger.info("RabbitMQ 拓扑已初始化")
