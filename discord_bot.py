import discord
import configparser
import re
from collections import OrderedDict
from random import choice
from enum import Enum
import boolean
from boolean_rule_algebra import BooleanRuleAlgebra


client = discord.Client()
algebra = BooleanRuleAlgebra()

# https://github.com/bastikr/boolean.py/issues/82
algebra.TRUE.dual = type(algebra.FALSE)
algebra.FALSE.dual = type(algebra.TRUE)

config = configparser.ConfigParser()
config.read('config.ini')
token = config['discord']['token']

commands = {}
notifiers = OrderedDict()
affirmations = ['Okay', 'Sure', 'Sounds good', 'No problem']


class ChannelNotifier():

    def __init__(self, channel):
        self.channel = channel
        self.category = None
        self.area = None
        self.rules = []  # list of tuples (original user rule str, Expression)

    def _filter(self, result):
        name = result.lower()
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
        print(repr(total_rule))
        include_result = total_rule.simplify()
        return bool(include_result)


def command(r):
    def deco(f):
        def wrapper(*args, **kwargs):
            return f(*args, **kwargs)
        commands[re.compile(r, re.IGNORECASE)] = f
        return wrapper
    return deco


async def find_notifier(message):
    if message.channel not in notifiers:
        response = 'Sorry {}, I am not currently enabled to send notifications on this channel. Try `$cln`.'.format(
            message.author.mention)
        await message.channel.send(response)
        return None
    return notifiers[message.channel]


@command(r'cln$')
async def cmd_init(message, _):
    response = '{} {}, I\'ll start sending Craigslist notifications to {}'.format(
        choice(affirmations), message.author.mention, message.channel.mention)
    notifiers[message.channel] = ChannelNotifier(message.channel)
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
    response = '{}, I found {} notifier{} currently enabled.'.format(
        message.author.mention, len(notifiers), '' if len(notifiers) == 1 else 's')
    for channel, notifier in notifiers.items():
        response += '\n{}\n- Category: {}'.format(
            channel.mention,
            '`{}`'.format(notifier.category) if notifier.category is not None else 'not set')
    await message.channel.send(response)


@command(r'cln (category|cat) (.+)')
async def cmd_cat(message, m):
    notifier = await find_notifier(message)
    if not notifier:
        return
    category = m.groups()[1]
    notifier.category = category
    response = '{} {}, I\'ll search for listings in the `{}` category.'.format(choice(affirmations), message.author.mention, category)
    await message.channel.send(response)


@command(r'cln rules')
async def cmd_cat(message, m):
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


@command(r'cln (rule) (rm|r|d|delete|remove)($| (.+))')
async def cmd_cat(message, m):
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
    await message.channel.send(response)


@command(r'cln (rule)( add)? (.+)')
async def cmd_cat(message, m):
    notifier = await find_notifier(message)
    if not notifier:
        return

    rule_str = m.groups()[2]
    rule = algebra.parse(rule_str)
    notifier.rules.append((rule_str, rule))
    response = '{} {}, I\'ve added the following rule:\n```{}```'.format(choice(affirmations), message.author.mention, repr(rule))
    await message.channel.send(response)


@command(r'cln (debug|d) (eval) (.+)')
async def cmd_cat(message, m):
    notifier = await find_notifier(message)
    if not notifier:
        return

    test_str = m.groups()[2]
    result = notifier._filter(test_str)
    response = '{}'.format(result)
    await message.channel.send(response)


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))


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


client.run(token)
