After you have created a search, filters allow you to narrow down the results.

## The `/filter add` command

Similar to searches, new filters can be created for a given channel with `/filter add`. This command takes a few arguments:

`field`

: Each filter operates on a particular field of the listing. For example, `title` or `price`. Select which field you would like to filter on here.

`rule_type`

: There are two rule types to choose from: `and` and `or`. As their names suggest, these indicate the boolean operator type which will be used to evaluate this filter with the other filters defined in the channel. For more details, jump down to [Filter evaluation](#filter-evaluation).

`rule`

: The boolean expression representing this filter rule. There are two main types of rules, depending on the data type of the field you selected:

    1. Numerical rules - for numeric fields, such as `price`, the rule should take the following form:

        ```
        one of (>, >=. <, <=, =) (number)
        ```

        For example, to filter for listings less than $100: `<100`. For more complex ranges (for example, listings between $100 and $200), multiple `and` filters can be combined.

    2. String rules - for textual fields, such as `title` or `body`, the rule is a free-form boolean expression of text symbols and boolean operators. Type in any text, and it will automatically be parsed into an expression.

        For example, when searching for a new fabric couch, you might filter out leather couches with a rule such as:

        ```
        couch and not leather
        ```

## Filter evaluation

Whenever a new listing is detected in any of the searches active for the current channel, it is evaluated against all of the existing filter rules in order to determine whether or not a notification should be sent.

Filter rules of different types (`and` and `or`) are evaluated together as follows:

```
(and-rule-1 && and-rule-2 && ... and-rule-n) &&
    (or-rule-1 || or-rule-2 || ... or-rule-m)
```

If there are no `and`-type rules or no `or`-type rules, the corresponding section of the evaluation function is replaced with `true`. This means that when there are no filters present in a channel, notifications will be sent for all new listings.

## Editing or deleting a filter

If you made a mistake and would like to update or remove a filter from this channel, use the `/filter edit` and `/filter delete` commands, respectively.

## Showing all existing filters

To display a list of all searches and filters currently active on the channel, use the `/show` command.

## Unpausing the notifier

When you're ready to start receiving notifications, unpause the notifier with the `/pause` toggle command!
