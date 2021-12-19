"""Example of adding tasks on app startup."""
import logging

from .extensions import scheduler

if False:
    @scheduler.task(
        "interval",
        id="job_sync",
        seconds=10,
        max_instances=1,
        start_date="2000-01-01 12:19:00",
    )
    def task1():
        """Sample task 1.

        Added when app starts.
        """
        logging.debug("running task 1!")  # noqa: T001

        # oh, do you need something from config?
        with scheduler.app.app_context():
            logging.debug(scheduler.app.config)  # noqa: T001


def task2():
    """Sample task 2.

    Added when /add url is visited.
    """
    logging.debug("running task 2!")  # noqa: T001
