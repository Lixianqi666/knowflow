"""RabbitMQ 消费者：替代 Celery worker"""

import logging
import signal
import sys

from app.mq.connection import (
    QUEUE_INDEX,
    get_connection,
    setup_topology,
)
from app.mq.protocol import IndexTaskMessage

logger = logging.getLogger(__name__)


def check_idempotency(msg: IndexTaskMessage) -> bool:
    """检查幂等性，返回 True 表示应跳过"""
    from app.mq.idempotency import is_duplicate, mark_processing

    if is_duplicate(msg.idempotency_key):
        logger.info(f"跳过重复任务: {msg.idempotency_key}")
        return True
    mark_processing(msg.idempotency_key, msg.task_id)
    return False


def handle_index(msg: IndexTaskMessage):
    """处理索引任务"""
    import asyncio

    from app.tasks.indexing import _index

    if check_idempotency(msg):
        return

    try:
        asyncio.run(_index(msg.payload["document_id"]))
        from app.mq.idempotency import mark_completed

        mark_completed(msg.idempotency_key)
        logger.info(f"索引完成: {msg.task_id}")
    except Exception:
        from app.mq.idempotency import mark_failed

        mark_failed(msg.idempotency_key)
        raise


def on_message(channel, method, properties, body):
    """消息回调"""
    try:
        msg = IndexTaskMessage.from_json(body.decode())
        logger.info(f"收到任务: {msg.task_type} task_id={msg.task_id}")

        if msg.task_type == "index_document":
            handle_index(msg)
        else:
            logger.warning(f"未知任务类型: {msg.task_type}")

        channel.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        logger.exception(f"处理消息失败: {e}")
        # 拒绝消息，不重新入队（由 retry 队列处理）
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    conn = get_connection()
    ch = conn.channel()
    setup_topology(ch)

    ch.basic_qos(prefetch_count=1)
    ch.basic_consume(queue=QUEUE_INDEX, on_message_callback=on_message)

    def shutdown(sig, frame):
        logger.info("收到退出信号，关闭连接...")
        ch.stop_consuming()
        conn.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    logger.info("MQ 消费者已启动，等待消息...")
    ch.start_consuming()


if __name__ == "__main__":
    main()
