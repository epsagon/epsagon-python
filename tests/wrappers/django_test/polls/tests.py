"""
Django wrapper tests
"""

import threading
import time
from django.test import TestCase
from django.test import Client

ANSWER_A = b'This is A'
ANSWER_B = b'This is B'


class MultipleRequestsTestCase(TestCase):
    def thread_a(self):
        time.sleep(2)
        c = Client()
        response = c.get("/polls/a")
        self.assertEqual(response.content, ANSWER_A)

    def thread_b(self):
        time.sleep(2)
        c = Client()
        response = c.get("/polls/b")
        self.assertEqual(response.content, ANSWER_B)

    def test_multiple_requests(self):
        """Animals that can speak are correctly identified"""
        c = Client()
        a = threading.Thread(target=self.thread_a, args=(1,))
        a.start()

        b = threading.Thread(target=self.thread_b, args=(1,))
        b.start()

        a.join()
        b.join()
