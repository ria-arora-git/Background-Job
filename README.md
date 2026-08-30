A bad topic gets a 400 instead of a retry because retries are meant for temporary problems that might work if tried again, while missing or invalid input will not fix itself by retrying. It is better to reject it immediately than waste three attempts on something that cannot succeed.

Build both on [crontab.guru](https://crontab.guru) to double-check:

> - Every day at 08:00: `0 8 * * *`
> - Every Sunday at 22:00: `0 22 * * 0`