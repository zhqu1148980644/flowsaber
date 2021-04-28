import httpimport

import flowsaber
from flowsaber import *


def test_remote_import():
    url = "https://gist.githubusercontent.com/zhqu1148980644/" \
          "2eafbe8d25883919ecf11a729f1fdb9a/raw/742c8ada5f70589dd6ec83641462f88aa36a6b27"
    with httpimport.remote_repo(['testtask'], url):
        from testtask import task1, task2

    @flow
    def myflow(name):
        return task2(task1(name), name)

    names = Channel.values("qwe", 'asd', 'zxcx', 'hhh')

    workflow = myflow(names)
    consumer = Consumer.from_channels(workflow._output)
    asyncio.run(flowsaber.run(workflow))

    results = []
    for data in consumer:
        results.append(data)
    print("Results are: ")
    for res in results:
        print(res, type(res))


if __name__ == "__main__":
    test_remote_import()