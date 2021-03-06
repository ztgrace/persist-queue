# coding=utf-8

import random
import shutil
import tempfile
import unittest
from threading import Thread

from persistqueue import SQLiteQueue, FILOSQLiteQueue
from persistqueue import Empty


def task_done_if_required(queue):
    if not queue.auto_commit:
        queue.task_done()


class SQLite3QueueTest(unittest.TestCase):
    def setUp(self):
        self.path = tempfile.mkdtemp(suffix='sqlqueue')
        self.auto_commit = False

    def tearDown(self):
        shutil.rmtree(self.path, ignore_errors=True)

    def test_raise_empty(self):
        q = SQLiteQueue(self.path, auto_commit=self.auto_commit)

        q.put('first')
        task_done_if_required(q)
        d = q.get()
        self.assertEqual('first', d)
        self.assertRaises(Empty, q.get, block=True)

    def test_open_close_single(self):
        """Write 1 item, close, reopen checking if same item is there"""

        q = SQLiteQueue(self.path, auto_commit=self.auto_commit)
        q.put(b'var1')
        task_done_if_required(q)
        del q
        q = SQLiteQueue(self.path)
        self.assertEqual(1, q.qsize())
        self.assertEqual(b'var1', q.get())

    def test_open_close_1000(self):
        """Write 1000 items, close, reopen checking if all items are there"""

        q = SQLiteQueue(self.path, auto_commit=self.auto_commit)
        for i in range(1000):
            q.put('var%d' % i)

        task_done_if_required(q)

        self.assertEqual(1000, q.qsize())
        del q
        q = SQLiteQueue(self.path)
        self.assertEqual(1000, q.qsize())
        for i in range(1000):
            data = q.get()
            self.assertEqual('var%d' % i, data)
        # assert adding another one still works
        q.put('foobar')
        data = q.get()
        self.assertEqual('foobar', data)

    def test_random_read_write(self):
        """Test random read/write"""

        q = SQLiteQueue(self.path, auto_commit=self.auto_commit)
        n = 0
        for i in range(1000):
            if random.random() < 0.5:
                if n > 0:
                    q.get()
                    n -= 1
                else:
                    self.assertEqual(None, q.get())
            else:
                q.put('var%d' % random.getrandbits(16))
                task_done_if_required(q)
                n += 1

    def test_multi_threaded_parallel(self):
        """Create consumer and producer threads, check parallelism"""

        # self.skipTest("Not supported multi-thread.")

        m_queue = SQLiteQueue(path=self.path, multithreading=True,
                              auto_commit=self.auto_commit)

        def producer():
            for i in range(1000):
                m_queue.put('var%d' % i)

            task_done_if_required(m_queue)

        def consumer():
            for i in range(1000):
                x = m_queue.get(block=True)
                self.assertEqual('var%d' % i, x)

        c = Thread(target=consumer)
        c.start()
        p = Thread(target=producer)
        p.start()
        p.join()
        c.join()
        self.assertEqual(0, m_queue.size)
        self.assertEqual(0, len(m_queue))
        self.assertIsNone(m_queue.get(block=False))

    def test_multi_threaded_multi_producer(self):
        """Test sqlqueue can be used by multiple producers."""
        queue = SQLiteQueue(path=self.path, multithreading=True,
                            auto_commit=self.auto_commit)

        def producer(seq):
            for i in range(10):
                queue.put('var%d' % (i + (seq * 10)))

            task_done_if_required(queue)

        def consumer():
            for i in range(100):
                data = queue.get(block=True)
                self.assertTrue('var' in data)

        c = Thread(target=consumer)
        c.start()
        producers = []
        for seq in range(10):
            t = Thread(target=producer, args=(seq,))
            t.start()
            producers.append(t)

        for t in producers:
            t.join()

        c.join()

    def test_multiple_consumers(self):
        """Test sqlqueue can be used by multiple consumers."""

        queue = SQLiteQueue(path=self.path, multithreading=True,
                            auto_commit=self.auto_commit)

        def producer():
            for x in range(1000):
                queue.put('var%d' % x)
                task_done_if_required(queue)

        def consumer():
            for _ in range(100):
                data = queue.get(block=True)
                self.assertTrue('var' in data)

        p = Thread(target=producer)
        p.start()
        consumers = []
        for _ in range(10):
            t = Thread(target=consumer)
            t.start()
            consumers.append(t)

        for t in consumers:
            t.join()

        self.assertEqual(0, queue.qsize())


class SQLite3QueueAutoCommitTest(SQLite3QueueTest):
    def setUp(self):
        self.path = tempfile.mkdtemp(suffix='sqlqueue_auto_commit')
        self.auto_commit = True


class FILOSQLite3QueueTest(unittest.TestCase):
    def setUp(self):
        self.path = tempfile.mkdtemp(suffix='filo_sqlqueue')
        self.auto_commit = False

    def tearDown(self):
        shutil.rmtree(self.path, ignore_errors=True)

    def test_open_close_1000(self):
        """Write 1000 items, close, reopen checking if all items are there"""

        q = FILOSQLiteQueue(self.path, auto_commit=self.auto_commit)
        for i in range(1000):
            q.put('var%d' % i)
        task_done_if_required(q)
        self.assertEqual(1000, q.qsize())
        del q
        q = FILOSQLiteQueue(self.path)
        self.assertEqual(1000, q.qsize())
        for i in range(1000):
            data = q.get()
            self.assertEqual('var%d' % (999 - i), data)
        # assert adding another one still works
        q.put('foobar')
        data = q.get()
        self.assertEqual('foobar', data)


class FILOSQLite3QueueAutoCommitTest(FILOSQLite3QueueTest):
    def setUp(self):
        self.path = tempfile.mkdtemp(suffix='filo_sqlqueue_auto_commit')
        self.auto_commit = True
