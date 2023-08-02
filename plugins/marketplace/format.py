from datetime import timezone

import discord

from hyacinth.models import DiscordMessage
from hyacinth.notifier import ChannelNotifier
from hyacinth.util.geo import distance_miles
from plugins.marketplace.models import MarketplaceListing


def format_listing(notifier: ChannelNotifier, listing: MarketplaceListing) -> DiscordMessage:
    match (listing.city, listing.state):
        case (None, None):
            location_part = ""
        case (city, None):
            location_part = f" - {city}"
        case (None, state):
            location_part = f" - {state}"
        case (city, state):
            location_part = f" - {city}, {state}"
    distance_part = ""
    if (
        notifier.config.home_location is not None
        and listing.latitude is not None
        and listing.longitude is not None
    ):
        distance = distance_miles(
            notifier.config.home_location, (listing.latitude, listing.longitude)
        )
        distance_part = f" ({int(distance)} mi. away)"
    description = f"**${int(listing.price)}{location_part}{distance_part}**\n\n{listing.body}"

    embed = discord.Embed(
        title=listing.title,
        url=listing.url,
        description=description[:2048],
        timestamp=listing.creation_time.astimezone(timezone.utc),
    )
    if listing.image_urls:
        embed.set_image(url=listing.thumbnail_url)

    return DiscordMessage(embed=embed)
