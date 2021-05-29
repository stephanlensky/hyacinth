import discord
import configparser
import re
from collections import OrderedDict
from random import choice
import boolean
from boolean_rule_algebra import BooleanRuleAlgebra
from craigslist_notifier import CraigslistMonitor, CraigslistObserver, tsprint, area_names
import datetime
import signal
import sys
import shelve
import asyncio
import pickle
import ast
from datetime import timedelta
from state_names import state_names
import threading
import tempfile
import requests
import pickle


client = discord.Client()
logged_in = asyncio.Event()
stale_channels = set()

algebra = BooleanRuleAlgebra()

config = configparser.ConfigParser()
config.read('config.ini')
token = config['discord']['token']

commands = {}
affirmations = ['Okay', 'Sure', 'Sounds good', 'No problem']

craigslist = None


class ChannelNotifier():

    def __init__(self, channel):
        self.finished_init = asyncio.Event()
        self.channel = channel
        self.channel_name = channel.name
        self.channel_guild_name = channel.guild.name
        self.message_length = 1024
        self.unpaused = True

        self.lat_long = (42.771, -71.510)
        self.interval = timedelta(minutes=10)
        self.categories = ['mca']
        self.areas = list(area_names)
        self.craigslist_observer = CraigslistObserver(self.categories, self.areas)

        self.rules = []  # list of tuples (original user rule str, Expression)
        self.preremoval_rules = []  # remove these words before applying rules
        self.disallowed_words = []  # auto fail any listing with these words
        self.last_run = None
        self.scheduled_notify_task = None

        self.__threading_init()
        self.finished_init.set()

        client.loop.create_task(self.get_new_results())

    def __threading_init(self):
        """
        initializes some async-related objects that can't be pickled/unpickled normally
        """
        self.unpaused_event = asyncio.Event()
        if self.unpaused:
            self.unpaused_event.set()
        self.craigslist_observer = CraigslistObserver(self.categories, self.areas)

    def __getstate__(self):
        d = self.__dict__.copy()
        del d['channel']
        del d['finished_init']
        del d['unpaused_event']
        del d['craigslist_observer']
        d['scheduled_notify_task'] = None
        d['channel_id'] = self.channel.id
        return d

    def __setstate__(self, state):
        self.finished_init = asyncio.Event()
        channel_id = state['channel_id']
        del state['channel_id']

        async def get_channel():
            await logged_in.wait()
            self.channel = client.get_channel(channel_id)
            if self.channel is None:
                tsprint('Channel {}#{} ({}) no longer exists. Deleting saved notifier for this channel.'.format(
                    self.channel_guild_name, self.channel_name, channel_id))
                stale_channels.add(channel_id)
                self.finished_init.set()
                return
            self.channel_name = self.channel.name
            self.channel_guild_name = self.channel.guild.name
            self.finished_init.set()
            tsprint('Loaded saved notifier for {}#{} ({})'.format(self.channel.guild.name, self.channel, channel_id))
            client.loop.create_task(self.get_new_results())

        self.__dict__.update(state)
        self.__threading_init()
        client.loop.create_task(get_channel())

    def _filter(self, result):
        name = result['name'].lower()
        for preremoval_rule in self.preremoval_rules:
            name = name.replace(preremoval_rule, '')
        for disallowed_word in self.disallowed_words:
            if disallowed_word in name:
                return False

        total_rule = None
        for _, rule in self.rules:
            if total_rule is None:
                total_rule = rule
            else:
                total_rule = total_rule | rule

        if total_rule is None:
            return False

        symbols = total_rule.get_symbols()
        subs = {}
        for sym in symbols:
            subs[sym] = algebra.TRUE if sym.obj in name else algebra.FALSE
        total_rule = total_rule.subs(subs)
        include_result = total_rule.simplify()
        return bool(include_result)

    def close(self):
        self.scheduled_notify_task.cancel()

    def pause(self):
        self.unpaused = False
        self.unpaused_event.clear()

    def unpause(self):
        self.unpaused = True
        self.unpaused_event.set()

    async def get_new_results(self):
        await self.unpaused_event.wait()

        self.last_run = datetime.datetime.now()
        save_notifiers()  # to trigger a save of the last run

        results = self.craigslist_observer.get_new_listings()
        results.sort(key=lambda r: r['created'])
        tsprint('{}#{} observed {} results'.format(self.channel.guild.name, self.channel, len(results)))
        for r in results:
            if self._filter(r):
                await self.send_result(r)
        self.scheduled_notify_task = client.loop.call_later(self.interval.seconds, self.get_new_results())

    async def send_result(self, r):
        r['location'] = r['location'].split(', ')
        # sometimes street address is missing from geocode result, so town/state position in geocoded string varies
        try:
            state_idx = [i for i, e in enumerate(r['location']) if e in state_names][0]
            if state_idx > 0:
                location = '{}, {}'.format(r['location'][max(state_idx - 2, 0)], r['location'][state_idx])
            else:
                location = r['location'][state_idx]
        except Exception:
            location = r['location']
        description = '**{} - {} ({} mi. away)**\n\n{}'.format(r['price'], location, int(r['distance']), r['body'])
        if len(description) > self.message_length - 3:
            description = description[:self.message_length - 3] + '...'

        embed = discord.Embed(
            title=r['name'],
            url=r['url'],
            description=description[:2048],
            timestamp=r['created'].astimezone(datetime.timezone.utc)
        )
        if len(r['images']):
            embed.set_image(url=r['images'][0])
        await self.channel.send(embed=embed)


def command(r):
    def deco(f):
        def wrapper(*args, **kwargs):
            return f(*args, **kwargs)
        commands[re.compile(r, re.IGNORECASE)] = f
        return wrapper
    return deco


async def find_notifier(message):
    if message.channel.id not in notifiers:
        response = 'Sorry {}, I am not currently enabled to send notifications on this channel. Try `$cln`.'.format(
            message.author.mention)
        await message.channel.send(response)
        return None
    return notifiers[message.channel.id]


def save_notifiers():
    shelf['notifiers'] = notifiers
    if craigslist:
        shelf['last_craigslist_check_time'] = craigslist.last_run


@command(r'cln$')
async def cmd_init(message, _):
    if message.channel.id not in notifiers:
        response = '{} {}, I\'ll start sending Craigslist notifications to {}'.format(
            choice(affirmations), message.author.mention, message.channel.mention)
        notifier = ChannelNotifier(message.channel)
        notifiers[message.channel.id] = notifier
        craigslist.subscribe(notifier.craigslist_observer)
        save_notifiers()
    else:
        response = 'Sorry {}, it looks like there\'s already a notifier enabled for this channel.'.format(
            message.author.mention)
    await message.channel.send(response)


@command(r'(status|(you|u|still) (there|up|aliv|alive)|(what|wat)\'?s? up)')
async def cmd_status(message, _):
    response = choice([
        'Don\'t worry {}, I know how high the steaks are. Everything is operating normally.',
        'If you ask me that one more time {}, I\'ll be tanning *your* hide.',
        'Don\'t have a cow {}, all systems are operational.',
        'No cause for concern {}, I\'m still milking Craigslist for all it\'s worth.',
        '{}, I know you must be over the moon with joy that I am still working as intended!',
        'No bull here {}, systems operating nominally.',
        '{}, the fact that my code is still working as intended can only be described as bovine intervention.',
        'I\'m still working just fine {}, maybe you should focus more on your udder problems?',
        'Still here {}, you couldn\'t see a good bot if it was steering you right in the face.',
        'Cowabunga {}, I\'m alive!',
        'I can promise you {}, I\'ll be here until the cows come home.',
        '{}, let us disbull the fiction that I am not operating as intended. I am operating exactly as intended.',
        '{}, it is udderly ridiculous that you think there is a possibility I am not operating correctly.',
        'Hay there {}, I\'m still here if you are.',
        'Don\'t worry {}, I won\'t hit the hay until you do.',
        'It\'s no cowincidence {}, all of my systems are still operating normally.',
        'Do you think I have no accowntability {}? Systems operating nominally.',
        '{} MOOOOOOOOO!',
        'Beep Boop. I am a robot cow.'
    ])
    if '{}' in response:
        response = response.format(message.author.mention)
    await message.channel.send(response)


@command(r'cln info')
async def cmd_info(message, _):
    # TODO fix
    response = '{}, I found {} notifier{} currently enabled.'.format(
        message.author.mention, len(notifiers), '' if len(notifiers) == 1 else 's')
    for channel_id, notifier in notifiers.items():
        response += '\n{}\n- Category: {}'.format(
            '<#{}>'.format(channel_id),
            '`{}`'.format(notifier.categories) if notifier.categories else 'not set')
    await message.channel.send(response)


@command(r'cln (category|cat) (.+)')
async def cmd_cat(message, m):
    notifier = await find_notifier(message)
    if not notifier:
        return
    category = m.groups()[1]
    notifier.categories = [category]
    response = '{} {}, I\'ll search for listings in the `{}` category.'.format(choice(affirmations), message.author.mention, category)
    save_notifiers()
    await message.channel.send(response)


@command(r'cln (rules?) (rm|r|d|delete|remove)($| (.+))')
async def cmd_rm_rule(message, m):
    notifier = await find_notifier(message)
    if not notifier:
        return

    if len(notifier.rules) == 0:
        await message.channel.send('Sorry {}, I didn\'t find any rules enabled for this channel.'.format(message.author.mention))
        return

    selection_str = m.groups()[3]
    if selection_str is None:
        selection = -1
    elif selection_str.isdigit():
        selection = int(selection_str) - 1
        if selection > len(notifier.rules) - 1:
            await message.channel.send('Sorry {}, I only found {} rule{} enabled for this channel.'.format(
                message.author.mention, len(notifier.rules), 's' if len(notifier.rules) > 1 else ''))
            return
    else:
        rules_strs = [r[0] for r in notifier.rules]
        try:
            selection = rules_strs.index(selection_str)
        except ValueError:
            await message.channel.send('Sorry {}, I couldn\'t find a rule matching `{}`.'.format(
                message.author.mention, selection_str))
            return

    response = '{} {}, I\'ve removed the following rule from this channel:\n```{}```'.format(
        choice(affirmations), message.author.mention, repr(notifier.rules[selection][1]))
    notifier.rules.pop(selection)
    save_notifiers()
    await message.channel.send(response)


@command(r'cln (rules?)( add)? (.+)')
async def cmd_add_rule(message, m):
    notifier = await find_notifier(message)
    if not notifier:
        return

    rule_str = m.groups()[2].strip()
    rule = algebra.parse(rule_str)
    notifier.rules.append((rule_str, rule))
    response = '{} {}, I\'ve added the following rule:\n```{}```'.format(choice(affirmations), message.author.mention, repr(rule))
    save_notifiers()
    await message.channel.send(response)


@command(r'cln rules?$')
async def cmd_ls_rules(message, m):
    notifier = await find_notifier(message)
    if not notifier:
        return

    if len(notifier.rules):
        rules_repr = ['{}. {}'.format(i + 1, repr(notifier.rules[i][1])) for i in range(len(notifier.rules))]
        response = '{} {}, I found the following rules enabled for this channel:\n```{}```'.format(
            choice(affirmations), message.author.mention, '\n'.join(rules_repr))
    else:
        response = 'Sorry {}, there are currently no rules enabled for this channel.'.format(message.author.mention)
    await message.channel.send(response)


@command(r'cln (preremove) (rm|r|d|delete|remove)($| (.+))')
async def cmd_rm_preremoval(message, m):
    notifier = await find_notifier(message)
    if not notifier:
        return

    if len(notifier.preremoval_rules) == 0:
        await message.channel.send('Sorry {}, I didn\'t find any preremoval rules enabled for this channel.'.format(message.author.mention))
        return

    selection_str = m.groups()[3]
    if selection_str is None:
        selection = -1
    elif selection_str.isdigit():
        selection = int(selection_str) - 1
        if selection > len(notifier.preremoval_rules) - 1:
            await message.channel.send('Sorry {}, I only found {} preremoval rule{} enabled for this channel.'.format(
                message.author.mention, len(notifier.preremoval_rules), 's' if len(notifier.preremoval_rules) > 1 else ''))
            return
    else:
        try:
            selection = notifier.preremoval_rules.index(selection_str)
        except ValueError:
            await message.channel.send('Sorry {}, I couldn\'t find a preremoval rule matching `{}`.'.format(
                message.author.mention, selection_str))
            return

    response = '{} {}, I\'ve removed the following preremoval rule from this channel:\n```{}```'.format(
        choice(affirmations), message.author.mention, notifier.preremoval_rules[selection])
    notifier.preremoval_rules.pop(selection)
    save_notifiers()
    await message.channel.send(response)


@command(r'cln (preremove)( add)? (.+)')
async def cmd_add_preremoval(message, m):
    notifier = await find_notifier(message)
    if not notifier:
        return

    rule = m.groups()[2].strip()
    notifier.preremoval_rules.append(rule)
    response = '{} {}, I\'ve added the following preremoval rule:\n```{}```'.format(choice(affirmations), message.author.mention, rule)
    save_notifiers()
    await message.channel.send(response)


@command(r'cln preremove$')
async def cmd_ls_preremovals(message, m):
    notifier = await find_notifier(message)
    if not notifier:
        return

    if len(notifier.preremoval_rules):
        rules_repr = ['{}. {}'.format(i + 1, notifier.preremoval_rules[i]) for i in range(len(notifier.preremoval_rules))]
        response = '{} {}, I found the following preremoval rules enabled for this channel:\n```{}```'.format(
            choice(affirmations), message.author.mention, '\n'.join(rules_repr))
    else:
        response = 'Sorry {}, there are currently no preremoval rules enabled for this channel.'.format(message.author.mention)
    await message.channel.send(response)


@command(r'cln (not|disallow) (rm|r|d|delete|remove)($| (.+))')
async def cmd_rm_disallow(message, m):
    notifier = await find_notifier(message)
    if not notifier:
        return

    if len(notifier.disallowed_words) == 0:
        await message.channel.send('Sorry {}, I didn\'t find any disallowed words for this channel.'.format(message.author.mention))
        return

    selection_str = m.groups()[3]
    if selection_str is None:
        selection = -1
    elif selection_str.isdigit():
        selection = int(selection_str) - 1
        if selection > len(notifier.disallowed_words) - 1:
            await message.channel.send('Sorry {}, I only found {} disallowed word{} enabled for this channel.'.format(
                message.author.mention, len(notifier.disallowed_words), 's' if len(notifier.disallowed_words) > 1 else ''))
            return
    else:
        try:
            selection = notifier.disallowed_words.index(selection_str)
        except ValueError:
            await message.channel.send('Sorry {}, I couldn\'t find a disallowed word matching `{}`.'.format(
                message.author.mention, selection_str))
            return

    response = '{} {}, I\'ve removed the following disallowed word from this channel:\n```{}```'.format(
        choice(affirmations), message.author.mention, notifier.disallowed_words[selection])
    notifier.disallowed_words.pop(selection)
    save_notifiers()
    await message.channel.send(response)


@command(r'cln (disallow|not)( add)? (.+)')
async def cmd_add_disallow(message, m):
    notifier = await find_notifier(message)
    if not notifier:
        return

    rule = m.groups()[2].strip()
    notifier.disallowed_words.append(rule)
    response = '{} {}, I\'ve added the following disallowed word rule:\n```{}```'.format(choice(affirmations), message.author.mention, rule)
    save_notifiers()
    await message.channel.send(response)


@command(r'cln (disallow|not)$')
async def cmd_ls_disallow(message, m):
    notifier = await find_notifier(message)
    if not notifier:
        return

    if len(notifier.disallowed_words):
        rules_repr = ['{}. {}'.format(i + 1, notifier.disallowed_words[i]) for i in range(len(notifier.disallowed_words))]
        response = '{} {}, I found the following disallowed words for this channel:\n```{}```'.format(
            choice(affirmations), message.author.mention, '\n'.join(rules_repr))
    else:
        response = 'Sorry {}, there are currently no disallowed words for this channel.'.format(message.author.mention)
    await message.channel.send(response)


@command(r'cln pause')
async def cmd_pause(message, _):
    notifier = await find_notifier(message)
    if not notifier:
        return

    notifier.pause()
    save_notifiers()
    response = '{} {}, I\'ve paused notifications for this channel.'.format(choice(affirmations), message.author.mention)
    await message.channel.send(response)


@command(r'cln (start|unpause)')
async def cmd_start(message, _):
    notifier = await find_notifier(message)
    if not notifier:
        return

    notifier.unpause()
    save_notifiers()
    response = '{} {}, I\'ve resumed notifications for this channel.'.format(choice(affirmations), message.author.mention)
    await message.channel.send(response)


@command(r'cln last( run)?$')
async def cmd_last_run(message, m):
    notifier = await find_notifier(message)
    if not notifier:
        return

    if notifier.last_run:
        response = '{}, I last checked Craigslist for you at {} (last observed at {})'.format(
            message.author.mention, craigslist.last_run.ctime(), notifier.last_run.ctime())
    else:
        response = '{}, I have not yet checked Craigslist for you on this channel (maybe I am paused?).'.format(
            message.author.mention)
    await message.channel.send(response)


@command(r'cln (debug|d) (eval) (.+)')
async def cmd_eval(message, m):
    notifier = await find_notifier(message)
    if not notifier:
        return

    test_str = m.groups()[2]
    result = notifier._filter({
        'name': test_str
    })
    response = '{}'.format(result)
    await message.channel.send(response)


@command(r'cln (debug|d) (dump|export)')
async def cmd_dump(message, _):
    notifier = await find_notifier(message)
    if not notifier:
        return

    dump = pickle.dumps(notifier)
    with tempfile.TemporaryFile() as fp:
        fp.write(dump)
        fp.seek(0)
        await message.channel.send(file=discord.File(fp, '{}-notifier.pickle'.format(message.channel.name)))


@command(r'cln (debug|d) (load|import)')
async def cmd_load(message, m):
    if message.author.id != 136892717870350340:
        return

    attachment_url = message.attachments[0].url
    pf = requests.get(attachment_url, stream=True).raw

    notifier = pickle.load(pf)
    await notifier.finished_init.wait()
    notifiers[message.channel.id] = notifier
    save_notifiers()

    response = 'Success.'
    await message.channel.send(response)


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    logged_in.set()

    for notifier in notifiers.values():
        await notifier.finished_init.wait()

    for channel_id in stale_channels:
        try:
            del notifiers[channel_id]
        except KeyError:
            pass
    stale_channels.clear()
    save_notifiers()

    global craigslist
    craigslist = CraigslistMonitor(
        observers=[n.craigslist_observer for n in notifiers.values()],
        last_run=shelf['last_craigslist_check_time'] if 'last_craigslist_check_time' in shelf else None)


@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if client.user.mentioned_in(message):
        mention_regex = r'<@!?{}>'.format(client.user.id)
        message.content = re.sub(mention_regex, '', message.content, 1).strip()
    elif message.content.startswith('$'):
        message.content = message.content[1:].strip()
    else:
        return  # this is not a bot command

    for r in commands:
        m = r.match(message.content)
        if m:
            await commands[r](message, m)
            break


if __name__ == '__main__':
    shelf = shelve.open('bot_storage')
    if 'notifiers' in shelf:
        notifiers = shelf['notifiers']
    else:
        notifiers = OrderedDict()
    client.run(token)
