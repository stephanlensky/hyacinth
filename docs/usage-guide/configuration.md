The `/configure` command allows for further customization of notification behavior.

## Available settings

### `notification_frequency`

Controls the frequency that notifications will be sent to the channel. Note, this does not affect how often searches are monitored internally - it simply changes how often the bot will check its internal database for new listings and send notifications as needed to the channel.

Set in seconds.

### `home_location`

When formatting notifications, having a home location set will add a "X miles away" subtitle to each listing, when available.

Set as a latitude/longitude pair, separated by a comma.
