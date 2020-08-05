import time
import requests
import threading

ANSWER_A = b'This is A'
ANSWER_B = b'This is B'

def threadA():
    time.sleep(2)
    response = requests.get("http://127.0.0.1:8000/polls/a")
    if response.content != ANSWER_A:
        print("Bad answer in A!")
        print(response.content)

def threadB():
    time.sleep(2)
    response = requests.get("http://127.0.0.1:8000/polls/b")
    if response.content != ANSWER_B:
        print("Bad answer in B!")
        print(response.content)

def main():
    a_threads = [threading.Thread(target=threadA) for _ in range(20)]
    b_threads = [threading.Thread(target=threadB) for _ in range(20)]
    for a, b in zip(a_threads, b_threads):
        a.start()
        b.start()

if __name__ == "__main__":
    main()
