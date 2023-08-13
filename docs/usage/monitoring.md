Hyacinth operates by scraping third-party websites. At any time, a change could be made to these websites which breaks Hyacinth's integrations with them. If you wish to increase your visibility into such issues, the following page details some potential solutions.

## Metrics

Hyacinth includes built-in support for writing metrics to a [Victoria Metrics](https://victoriametrics.com/) cluster. This allows metrics such as request counts and poll job execution results to be monitored live with an observability platform like [Grafana](https://grafana.com/).

To enable metrics support, add the following variables to your `.env` file:

```
METRICS_ENABLED=true
VICTORIA_METRICS_HOST=<your victoria metrics host>
```

The following metrics are supported:

- `hyacinth_scrape_count` - Counter of pages scraped by Browserless, labeled by domain.
- `hyacinth_poll_job_execution_count` - Counter representing the results of completed search poll jobs. Metric includes labels for `success` to indicate whether the polling job succeeded as well as the `plugin` the search was executed with.

Some example queries on these metrics are provided below, ready to be pasted into a Grafana panel.

### Browserless requests by domain

```
count_over_time(hyacinth_scrape_count[$__interval]) or on() vector(0)
```

### Successful poll job executions

```
count_over_time(hyacinth_poll_job_execution_count{success="true"}[$__interval]) or on() vector(0)
```

### Failing poll job executions

```
count_over_time(hyacinth_poll_job_execution_count{success="false"}[$__interval]) or on() vector(0)
```

## Error reporting

By default, a failing search poll job will write a crash report to the `logs/` directory. This behavior can be configured with the `SAVE_CRASH_REPORTS` and `CRASH_REPORTS_SAVE_FOLDER` environment variables.

```sh
# default setings
SAVE_CRASH_REPORTS = true
CRASH_REPORTS_SAVE_FOLDER = logs
```
