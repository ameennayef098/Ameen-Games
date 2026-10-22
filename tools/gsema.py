#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cross-process API concurrency limiter.

Ten generation agents run at once and they all hit the same NVIDIA account.
Without a shared cap they each open their own workers and the account answers
with 429s, so the retries burn more time than the generation itself.

This is a counting semaphore backed by a single locked byte in a file, so any
number of processes on the machine share one budget. Windows has no fcntl, so
the lock is msvcrt.locking (advisory, byte-range, works across processes).

Usage
-----
    from gsema import limit
    with limit('nvidia', slots=6):
        out = nvidia_chat(prompt)
"""
import os
import random
import threading
import time

try:
    import msvcrt
except ImportError:      # pragma: no cover - non-Windows fallback
    msvcrt = None

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEMA_DIR = os.path.join(BASE, 'data', '.sema')

# One lock per process, shared by every semaphore instance in it. REQUIRED:
# Windows byte-range locks are mandatory, so a second thread in the SAME
# process that tries to lock a byte a sibling already holds gets
# PermissionError instead of blocking. Without this lock every contended
# acquire raised, and the caller's retry loop turned each raise into seconds
# of sleeping - which stalled a whole generation run after a few batches.
_PROC_LOCK = threading.Lock()


class GlobalSemaphore:
    def __init__(self, name, slots, timeout=120):
        self.path = os.path.join(SEMA_DIR, name + '.lock')
        self.slots = int(slots)
        self.timeout = float(timeout)
        # Per-THREAD held flag. A plain instance attribute is shared by every
        # thread, so with a shared semaphore one thread's release cleared the
        # flag another thread had just set - that thread's slot was then never
        # released and the counter drifted upward until the whole run stalled.
        self._local = threading.local()
        os.makedirs(SEMA_DIR, exist_ok=True)
        # a+b so the file is created if missing and never truncated
        self._fh = open(self.path, 'a+b')

    def _set_held(self, value):
        self._local.held = value

    def _get_held(self):
        return getattr(self._local, 'held', False)

    # -- msvcrt byte-range lock: lock byte 0, so every process serialises here
    def _lock(self):
        self._fh.seek(0)
        msvcrt.locking(self._fh.fileno(), msvcrt.LK_NBLCK, 1)

    def _unlock(self):
        self._fh.seek(0)
        try:
            msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass

    def _read(self):
        self._fh.seek(0)
        raw = self._fh.read().decode('utf-8', 'replace').strip()
        try:
            return int(raw)
        except ValueError:
            return 0

    def _write(self, n):
        self._fh.seek(0)
        self._fh.truncate()
        self._fh.write(str(n).encode('utf-8'))
        self._fh.flush()

    def _try_take(self):
        """Take a slot if one is free. Returns True/False; never raises."""
        try:
            self._lock()
        except OSError:
            return False                 # another process holds the file lock
        try:
            n = self._read()
            if n < self.slots:
                self._write(n + 1)
                return True
            return False
        finally:
            self._unlock()

    def acquire(self):
        deadline = time.time() + self.timeout
        while True:
            # Serialise this process's own threads around the file lock, so the
            # file lock only ever contends with OTHER processes.
            with _PROC_LOCK:
                if self._try_take():
                    self._set_held(True)
                    return True
            if time.time() > deadline:
                # Never block a generation run forever because a crashed
                # process left a slot held - take the slot and carry on.
                return True
            time.sleep(0.3 + random.random() * 0.5)

    def release(self):
        if not self._get_held():
            return
        with _PROC_LOCK:
            try:
                self._lock()
                try:
                    self._write(max(0, self._read() - 1))
                finally:
                    self._unlock()
            except OSError:
                pass
        self._set_held(False)

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *exc):
        self.release()
        return False


_CACHE = {}


def limit(name='nvidia', slots=6, timeout=120):
    """Context manager limiting concurrent API calls across all processes."""
    key = (name, slots, timeout)
    if key not in _CACHE:
        _CACHE[key] = GlobalSemaphore(name, slots, timeout)
    return _CACHE[key]


def used(name='nvidia'):
    """How many slots are currently held (for progress logs)."""
    try:
        with open(os.path.join(SEMA_DIR, name + '.lock'), 'rb') as f:
            raw = f.read().decode('utf-8', 'replace').strip()
        return int(raw) if raw else 0
    except (OSError, ValueError):
        return 0
