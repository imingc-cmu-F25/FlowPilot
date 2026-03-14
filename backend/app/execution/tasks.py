from celery import shared_task


@shared_task(name="execution.ping")
def ping() -> str:
    return "pong"
