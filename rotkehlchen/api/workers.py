import logging
import queue
import threading
from collections.abc import Callable
from typing import Any

import gevent

from rotkehlchen.logging import RotkehlchenLogsAdapter

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class RestAPIWorker:
    def __init__(self):
        # Async tasks queue for greenlet-based tasks.
        self.task_queue: queue.Queue[tuple[int, Callable, tuple, dict] | None] = (
            queue.Queue()
        )
        # New queue for synchronous tasks that return a result.
        # Each item is a tuple: (function, args, kwargs, result_queue)
        self.sync_task_queue: queue.Queue[
            tuple[Callable, tuple, dict, queue.Queue]
        ] = queue.Queue()

        self._worker_thread: threading.Thread | None = None
        self._worker_stop_event = threading.Event()

        self._task_lock = threading.Lock()  # Guard shared state
        self.task_id = -1  # Next task ID
        self.task_results: dict[int, Any] = {}
        self.running_greenlets: dict[int, gevent.Greenlet] = {}

    def _start_worker_thread(self) -> None:
        """Starts the dedicated worker thread."""
        log.debug("Starting worker thread...")
        pool = gevent.get_hub().threadpool
        self._worker_thread = pool.spawn(self._worker_main_loop)
        log.debug("Worker thread started.")

    def _store_task_result(self, task_id: int, data: Any) -> None:
        """Stores the task result or error safely."""
        with self._task_lock:
            log.debug(f"Updating status of task {task_id} to {data}")
            log.debug(f"B: {self.task_results}")
            self.task_results[task_id] = {"status": "completed", "data": data}
            log.debug(f"A: {self.task_results}")

    def submit_task(self, func: Callable, *args, **kwargs) -> int:
        """Submits an asynchronous task to the worker queue and returns a task id."""
        with self._task_lock:
            self.task_id += 1
            current_task_id = int(self.task_id)
            # Initialize status as pending
            self.task_results[current_task_id] = {"status": "pending"}
        # Put the task (ID, function, args, kwargs) onto the queue.
        self.task_queue.put((current_task_id, func, args, kwargs))
        log.debug(f"Main thread: Submitted async task {current_task_id} to queue.")
        return current_task_id

    def get_tasks_status(self) -> dict[str, list[int]]:
        completed, pending = [], []
        with self._task_lock:
            for task_id, info in self.task_results.items():
                if info["status"] == "completed":
                    completed.append(task_id)
                elif info["status"] == "pending":
                    pending.append(task_id)
        return {"pending": pending, "completed": completed}

    def get_task_status(self, task_id: int) -> dict[str, Any]:
        """Retrieves the status and result (if ready) of a task."""
        with self._task_lock:
            return self.task_results.get(task_id, {"status": "not_found"})

    def execute_sync_task(self, func: Callable, *args, **kwargs) -> Any:
        """
        Submits a synchronous task to the worker thread and blocks until
        the result is available.
        """
        # Create a thread-safe queue to receive the result.
        # We assume that only one result will be put in it.
        result_queue: queue.Queue[Any] = queue.Queue(maxsize=1)
        self.sync_task_queue.put((func, args, kwargs, result_queue))
        log.debug(f"Main thread: Submitted sync task for {func}.")
        # Block waiting for the result.
        result = result_queue.get()
        # Optionally, you can check if the result is an exception and raise it.
        if isinstance(result, Exception):
            raise result
        return result

    def _worker_main_loop(self) -> None:
        """
        The main loop executed by the worker thread. It spawns two auxiliary
        greenlets: one for asynchronous tasks, and one for synchronous tasks.
        """
        log.debug("Worker thread: Entering main loop.")
        self._worker_gevent_stop_event = gevent.event.Event()

        # Greenlet to consume async tasks.
        def _gevent_task_consumer_greenlet():
            while not self._worker_stop_event.is_set():
                try:
                    # Try to get an async task with a short timeout.
                    task_item = self.task_queue.get(block=True, timeout=0.1)
                except queue.Empty:
                    gevent.sleep(0.01)
                    continue  # No async task available.
                task_id, func, args, kwargs = task_item
                log.debug(f"Worker thread: Received async task {task_id}")

                def task_runner(executing_task_id):
                    try:
                        with self.app.app_context():
                            result = func(self, *args, **kwargs)
                        self._store_task_result(executing_task_id, result)
                    except Exception as e:
                        err_msg = (
                            "The backend query task died unexpectedly: "
                            f"{str(e)}"
                        )
                        self._store_task_result(
                            executing_task_id,
                            {"result": None, "message": err_msg},
                        )
                        log.error(
                            f"Worker thread: Task {executing_task_id} failed "
                            f"with error: {e}"
                        )

                # Spawn a greenlet to run the async task.
                self.running_greenlets[task_id] = gevent.spawn(
                    task_runner, task_id
                )
                self.task_queue.task_done()

        # Greenlet to consume synchronous tasks.
        def _sync_task_consumer_greenlet():
            while not self._worker_stop_event.is_set():
                try:
                    # Try to get a synchronous task with a short timeout.
                    sync_task = self.sync_task_queue.get(block=True, timeout=0.1)
                except queue.Empty:
                    gevent.sleep(0.01)
                    continue  # No sync task available.
                sync_func, args, kwargs, result_queue = sync_task
                log.debug("Worker thread: Received sync task")
                try:
                    with self.app.app_context():
                        result = sync_func(*args, **kwargs)
                except Exception as e:
                    log.error(
                        f"Worker thread: Sync task failed with error: {e}"
                    )
                    result_queue.put(e)
                else:
                    result_queue.put(result)

        # Spawn both consumer greenlets.
        async_consumer_greenlet = gevent.spawn(_gevent_task_consumer_greenlet)
        sync_consumer_greenlet = gevent.spawn(_sync_task_consumer_greenlet)

        print(
            "Worker thread: Blocking on gevent event to keep gevent hub alive."
        )
        self._worker_gevent_stop_event.wait()
        print("Worker thread: Gevent event unblocked. Exiting worker thread.")

        # Optional: wait briefly for any last-minute tasks.
        gevent.sleep(0.1)
        gevent.joinall([async_consumer_greenlet, sync_consumer_greenlet])
        log.debug("Worker thread: Exiting main loop.")
