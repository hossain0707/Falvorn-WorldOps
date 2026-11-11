"""Background scheduler with PostgreSQL advisory leader election.

Only one worker instance advances worlds at a time. Advisory locks protect
against duplicate schedulers; per-world row locks protect concurrent API steps.
They do not solve the long-held transaction during remote LLM calls; see OPERATIONS.
"""
import logging
import signal
import time
from sqlalchemy import select, text
from app.core.config import get_settings
from app.core.database import SessionLocal, engine
from app.domain.models import World
from app.services.engine import step_world

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)
LEADER_LOCK_ID = 871006122026  # shared across WorldOps workers using one database
running = True


def shutdown(*_):
    global running
    running = False


def process_running_worlds():
    """One tick; per-world errors are isolated and logged."""
    with SessionLocal() as db:
        ids = db.scalars(select(World.id).where(World.status == 'running')).all()
    for world_id in ids:
        if not running:
            break
        try:
            step_world(world_id)
        except Exception:
            log.exception('World step failed: world_id=%s', world_id)


def main():
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    cfg = get_settings()
    log.info('WorldOps worker started; PostgreSQL leader election enabled where available')
    if engine.dialect.name != 'postgresql':
        # SQLite development is intentionally limited to a single scheduler process.
        while running:
            process_running_worlds()
            time.sleep(cfg.polling_interval_seconds)
        return
    while running:
        try:
            # Advisory lock belongs to this dedicated database connection and is
            # released automatically when this worker dies/disconnects.
            with engine.connect() as leader:
                elected = leader.scalar(text('SELECT pg_try_advisory_lock(:key)'), {'key': LEADER_LOCK_ID})
                if elected:
                    log.info('Worker became scheduler leader')
                    try:
                        while running:
                            # Check the lock session is still live before stepping.
                            leader.execute(text('SELECT 1'))
                            process_running_worlds()
                            time.sleep(cfg.polling_interval_seconds)
                    finally:
                        leader.execute(text('SELECT pg_advisory_unlock(:key)'), {'key': LEADER_LOCK_ID})
                else:
                    log.info('Scheduler leader exists; standing by')
                    time.sleep(cfg.polling_interval_seconds)
        except Exception:
            log.exception('Scheduler leader connection failed; retrying')
            time.sleep(max(3.0, cfg.polling_interval_seconds))


if __name__ == '__main__':
    main()
