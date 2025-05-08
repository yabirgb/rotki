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
        self.task_queue: queue.Queue[tuple[int, Callable, tuple, dict] | None] = queue.Queue()  # Thread-safe queue
        self._worker_thread: threading.Thread | None = None
        self._worker_stop_event = threading.Event()  # Threading Event to signal worker to stop

        self._task_lock = threading.Lock()  # Use threading Lock for shared state
        self.task_id = -1  # Next task ID
        self.task_results: dict[int, Any] = {}
        self.running_greenlets = dict()

    def _start_worker_thread(self) -> None:
        """Starts the dedicated worker thread."""
        log.debug('Starting worker thread...')
        pool = gevent.get_hub().threadpool
        self._worker_thread = pool.spawn(self._worker_main_loop)
        log.debug('Worker thread started.')

    def _store_task_result(self, task_id: int, data: Any) -> None:
        """Stores the task result or error safely."""
        with self._task_lock:
            log.debug(f'Updating stauts of task {task_id} to {data}')
            log.debug(f'B: {self.task_results}')
            self.task_results[task_id] = {'status': 'completed', 'data': data}
            log.debug(f'A: {self.task_results}')

    def submit_task(self, func: Callable, *args, **kwargs) -> int:
        """Submits a task to the worker queue and returns a task id."""
        with self._task_lock:
            self.task_id += 1
            current_task_id = int(self.task_id)
            # Initialize status as pending
            self.task_results[current_task_id] = {'status': 'pending'}

        # Put the task (ID, function, args, kwargs) onto the queue
        # Use a non-blocking put, as the queue should theoretically have capacity
        self.task_queue.put((current_task_id, func, args, kwargs))
        log.debug(f'Main thread: Submitted task {current_task_id} to queue.')

        return current_task_id

    def get_tasks_status(self) -> dict[str, list[int]]:
        completed, pending = [], []
        with self._task_lock:
            for task_id, information in self.task_results.items():
                if information['status'] == 'completed':
                    completed.append(task_id)
                elif information['status'] == 'pending':
                    pending.append(task_id)

        return {'pending': pending, 'completed': completed}

    def get_task_status(self, task_id: int) -> dict[str, Any]:
        """Retrieves the status and result (if ready) of a task."""
        with self._task_lock:
            return self.task_results.get(task_id, {'status': 'not_found'})

    def _worker_main_loop(self) -> None:
        """The main loop executed by the worker thread."""
        log.debug('Worker thread: Entering main loop.')
        self._worker_gevent_stop_event = gevent.event.Event()

        def _gevent_task_consumer_greenlet():
            while not self._worker_stop_event.is_set():
                try:
                    # Get a task from the queue with a timeout so we can check the stop event
                    # Use a short timeout to be responsive to the stop signal
                    task_item = self.task_queue.get(block=False, timeout=0.1)  # Use timeout for responsiveness
                except queue.Empty:
                    gevent.sleep(0.01)
                    continue  # No tasks, check stop event and continue loop

                task_id, func, args, kwargs = task_item
                log.debug(f'Worker thread: Received task {task_id}')

                try:
                    # Spawn the function as a greenlet in *this* thread's gevent hub
                    # We use a wrapper to handle storing results/exceptions
                    def task_runner(executing_task_id):
                        try:
                            result = func(self, *args, **kwargs)
                            self._store_task_result(executing_task_id, result)
                        except Exception as e:
                            self._store_task_result(executing_task_id, {'result': None, 'message': f'The backend query task died unexpectedly: {str(e)}'})
                            log.error(f'Worker thread: Task {executing_task_id} failed with error: {e}')

                    # Spawn the task and immediately let the worker loop continue to get next task
                    # We don't .get() the greenlet here in the main worker loop, allowing
                    # multiple task greenlets to potentially run concurrently within this thread.
                    self.running_greenlets[task_id] = gevent.spawn(task_runner, task_id)

                except Exception as e:
                    # Handle errors during greenlet spawning or initial task setup
                    log.debug(f'Worker thread: Error spawning task {task_id}: {e}')
                    self._store_task_result(task_id, 'error', f'Failed to spawn: {e}')
                finally:
                    # Signal that this queue item has been processed
                    self.task_queue.task_done()

        # Spawn the greenlet that will consume tasks from the threading queue
        # This greenlet runs within the worker thread's gevent context
        consumer_greenlet = gevent.spawn(_gevent_task_consumer_greenlet)

        # Keep the worker thread alive and let the gevent hub schedule greenlets.
        # This call blocks the *threading* thread until _worker_gevent_stop_event is set
        print("Worker thread: Blocking on gevent event to keep gevent hub alive.")
        self._worker_gevent_stop_event.wait()
        print("Worker thread: Gevent event unblocked. Worker thread exiting.")

        # Optional: Wait briefly for any last-minute greenlets to finish after stop signal
        gevent.sleep(0.1)
        # Try to join the consumer greenlet to ensure it exited its loop
        consumer_greenlet.join(timeout=1) # Use timeout to avoid hanging
        log.debug('Worker thread: Exiting main loop.')
