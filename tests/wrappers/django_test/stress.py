import time
import requests
import threading

ANSWER_A = b'This is A'
ANSWER_B = b'This is B'

def threadA(name):
    time.sleep(2)
    response = requests.get("http://127.0.0.1:8000/polls/a")
    if response.content != ANSWER_A:
    	print("Bad answer in A!")
    	print(response.content)

def threadB(name):
    time.sleep(2)
    response = requests.get("http://127.0.0.1:8000/polls/b")
    if response.content != ANSWER_B:
    	print("Bad answer in B!")
    	print(response.content)

def main():
    a = threading.Thread(target=threadA, args=(1,))
    a.start()

    b = threading.Thread(target=threadB, args=(1,))
    b.start()

if __name__ == "__main__":
	main()
