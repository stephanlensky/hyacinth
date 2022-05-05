from notifier_bot.celery import app


@app.task
def add(x: int, y: int) -> int:
    return x + y
