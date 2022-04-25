import asyncio
from datetime import timedelta

from notifier_bot.monitor import MarketplaceMonitor
from notifier_bot.notifier import LoggerNotifier

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
monitor = MarketplaceMonitor(loop=loop)
notifier = LoggerNotifier(monitor=monitor, notification_frequency=timedelta(seconds=5), loop=loop)
loop.run_forever()
