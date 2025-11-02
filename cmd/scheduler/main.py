"""
Scheduler Service for running periodic tasks.
Follows Single Responsibility Principle - only handles scheduled jobs.
"""

import asyncio
import signal
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from core import get_settings, logger
from core.database import get_database
from core.messaging import get_queue_manager
from services import TaskService


class SchedulerService:
    """
    Scheduler Service for running periodic tasks.
    Uses APScheduler for cron-like job scheduling.
    """

    def __init__(self):
        self.settings = get_settings()
        self.scheduler = AsyncIOScheduler(timezone=self.settings.scheduler_timezone)
        self.message_broker = None
        self.task_service = TaskService()
        self.is_running = False

    async def start(self):
        """Start the scheduler service."""
        logger.info("Starting Scheduler Service...")

        # Connect to database
        try:
            await get_database()
            logger.info("Database connected")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

        # Connect to message broker
        try:
            self.message_broker = get_queue_manager()
            await self.message_broker.connect()
            logger.info("Message broker connected")
        except Exception as e:
            logger.error(f"Failed to connect to message broker: {e}")
            raise

        # Setup scheduled jobs
        self._setup_jobs()

        # Start scheduler
        self.scheduler.start()
        self.is_running = True

        logger.info("Scheduler Service started successfully")
        logger.info(f"Scheduled jobs: {len(self.scheduler.get_jobs())}")

        # Keep running
        try:
            while self.is_running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Scheduler cancelled")

    async def stop(self):
        """Stop the scheduler service."""
        logger.info("Stopping Scheduler Service...")
        self.is_running = False

        # Shutdown scheduler
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            logger.info("Scheduler shutdown")

        # Disconnect from message broker
        try:
            await self.message_broker.disconnect()
            logger.info("Message broker disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting message broker: {e}")

        # Disconnect from database
        try:
            from core.database import close_database
            await close_database()
            logger.info("Database disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting database: {e}")

        logger.info("Scheduler Service stopped")

    def _setup_jobs(self):
        """Setup all scheduled jobs."""
        logger.info("Setting up scheduled jobs...")

        # Job 1: Cleanup old tasks - runs daily at 2 AM
        self.scheduler.add_job(
            self.cleanup_old_tasks,
            trigger=CronTrigger(hour=2, minute=0),
            id="cleanup_old_tasks",
            name="Cleanup old tasks",
            replace_existing=True,
        )
        logger.info("Added job: cleanup_old_tasks (daily at 2 AM)")

        # Job 2: Process pending tasks - runs every 5 minutes
        self.scheduler.add_job(
            self.process_pending_tasks,
            trigger=IntervalTrigger(minutes=5),
            id="process_pending_tasks",
            name="Process pending tasks",
            replace_existing=True,
        )
        logger.info("Added job: process_pending_tasks (every 5 minutes)")

        # Job 3: Health check and metrics - runs every 1 minute
        self.scheduler.add_job(
            self.health_check,
            trigger=IntervalTrigger(minutes=1),
            id="health_check",
            name="Health check and metrics",
            replace_existing=True,
        )
        logger.info("Added job: health_check (every 1 minute)")

        # Job 4: Queue monitoring - runs every 10 minutes
        self.scheduler.add_job(
            self.monitor_queue,
            trigger=IntervalTrigger(minutes=10),
            id="monitor_queue",
            name="Monitor message queue",
            replace_existing=True,
        )
        logger.info("Added job: monitor_queue (every 10 minutes)")

        # Job 5: Example weekly job - runs every Monday at 8 AM
        self.scheduler.add_job(
            self.weekly_report,
            trigger=CronTrigger(day_of_week="mon", hour=8, minute=0),
            id="weekly_report",
            name="Weekly report generation",
            replace_existing=True,
        )
        logger.info("Added job: weekly_report (every Monday at 8 AM)")

    # Scheduled Job Implementations
    async def cleanup_old_tasks(self):
        """
        Cleanup old completed/failed tasks.
        Runs daily at 2 AM.
        """
        try:
            logger.info("Running cleanup_old_tasks job...")
            result = await self.task_service.cleanup_old_tasks(days=30)
            logger.info(
                f"Cleanup completed: {result.get('deleted_count', 0)} tasks deleted"
            )
        except Exception as e:
            logger.error(f"Error in cleanup_old_tasks job: {e}")

    async def process_pending_tasks(self):
        """
        Process pending tasks by publishing them to the queue.
        Runs every 5 minutes.
        """
        try:
            logger.info("Running process_pending_tasks job...")

            # Get pending tasks
            pending_tasks = await self.task_service.get_pending_tasks(limit=10)

            if not pending_tasks:
                logger.info("No pending tasks to process")
                return

            # Publish each pending task to queue
            for task in pending_tasks:
                try:
                    message = {
                        "type": "task",
                        "task_id": task["_id"],
                        "task_type": task["task_type"],
                        "payload": task["payload"],
                    }
                    await self.message_broker.publish(message)
                    logger.info(f"Published pending task {task['_id']} to queue")
                except Exception as e:
                    logger.error(f"Error publishing task {task['_id']}: {e}")

            logger.info(f"Processed {len(pending_tasks)} pending tasks")
        except Exception as e:
            logger.error(f"Error in process_pending_tasks job: {e}")

    async def health_check(self):
        """
        Perform health check and log metrics.
        Runs every 1 minute.
        """
        try:
            logger.debug("Running health_check job...")

            # Get task statistics
            task_stats = await self.task_service.get_statistics()

            # Get queue size
            queue_size = await self.message_broker.get_queue_size()

            logger.info(
                f"Health metrics - "
                f"Total tasks: {task_stats.get('total_tasks', 0)}, "
                f"Queue size: {queue_size}"
            )
        except Exception as e:
            logger.error(f"Error in health_check job: {e}")

    async def monitor_queue(self):
        """
        Monitor message queue and alert if needed.
        Runs every 10 minutes.
        """
        try:
            logger.info("Running monitor_queue job...")

            queue_size = await self.message_broker.get_queue_size()

            # Alert thresholds
            WARNING_THRESHOLD = 100
            CRITICAL_THRESHOLD = 500

            if queue_size >= CRITICAL_THRESHOLD:
                logger.error(
                    f"CRITICAL: Queue size is {queue_size} (threshold: {CRITICAL_THRESHOLD})"
                )
                # TODO: Send alert notification (email, Slack, etc.)
            elif queue_size >= WARNING_THRESHOLD:
                logger.warning(
                    f"WARNING: Queue size is {queue_size} (threshold: {WARNING_THRESHOLD})"
                )
            else:
                logger.info(f"Queue size is healthy: {queue_size}")
        except Exception as e:
            logger.error(f"Error in monitor_queue job: {e}")

    async def weekly_report(self):
        """
        Generate weekly report.
        Runs every Monday at 8 AM.
        """
        try:
            logger.info("Running weekly_report job...")

            # Get statistics
            task_stats = await self.task_service.get_statistics()

            # Generate report
            report = {
                "timestamp": datetime.utcnow().isoformat(),
                "period": "weekly",
                "task_statistics": task_stats,
            }

            logger.info(f"Weekly report generated: {report}")

            # TODO: Send report via email or save to file
            # TODO: Publish report to a dedicated queue for processing
        except Exception as e:
            logger.error(f"Error in weekly_report job: {e}")


async def main():
    """Main entry point."""
    service = SchedulerService()

    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()

    def signal_handler(sig):
        logger.info(f"Received signal {sig}, shutting down...")
        asyncio.create_task(service.stop())

    # Register signal handlers
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))

    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Service error: {e}")
    finally:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main())
