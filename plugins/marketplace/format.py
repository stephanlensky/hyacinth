import discord

from hyacinth.models import DiscordMessage
from hyacinth.notifier import ChannelNotifier
from plugins.marketplace.models import MarketplaceListing


def format_listing(notifier: ChannelNotifier, listing: MarketplaceListing) -> DiscordMessage:
    embed = discord.Embed(
        title=listing.title,
    )

    return DiscordMessage(embed=embed)
