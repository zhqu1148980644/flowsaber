import asyncio
from collections import abc
from queue import SimpleQueue
from typing import Union, Sequence, Optional, List

import flowsaber
from flowsaber.core.utils.target import END, End
from flowsaber.server.models import ChannelInput
from flowsaber.utility.logtool import get_logger

logger = get_logger(__name__)


class Fetcher(object):
    def __aiter__(self):
        return self

    async def __anext__(self):
        value = await self.get()
        if isinstance(value, End):
            raise StopAsyncIteration
        else:
            return value

    def __iter__(self):
        return self

    def __next__(self):
        value = self.get_nowait()
        if isinstance(value, End):
            raise StopIteration
        else:
            return value

    async def get(self):
        return self.get_nowait()

    def get_nowait(self):
        raise NotImplementedError


class ConstantQueue(object):
    """constant value can only be settled once by using put_nowait or put"""
    NOTSET = object()

    def __init__(self):
        self.value = self.NOTSET
        self.has_value = asyncio.Event()

    def put_nowait(self, item):
        if not self.has_value.is_set():
            self.has_value.set()
        self.value = item

    async def put(self, item):
        self.put_nowait(item)

    def get_nowait(self):
        if self.value is self.NOTSET:
            raise RuntimeError("The ConstantQueue is not initialized, please use ch.put/ch.put_nowait "
                               "to set the initial value")
        return self.value

    async def get(self):
        await self.has_value.wait()
        return self.get_nowait()

    def empty(self):
        return self.value is not self.NOTSET


class LazyAsyncQueue(Fetcher):
    def __init__(self, ch, queue_factory, **kwargs):
        super().__init__(**kwargs)
        self.ch: Channel = ch
        self.queue_factory = queue_factory
        self.queue: Optional[Union[asyncio.Queue, ConstantQueue]] = None

    def initialize_queue(self):
        if self.queue is None:
            self.queue = self.queue_factory()

    async def get(self):
        self.initialize_queue()
        if not self.ch.initialized:
            self.ch.initialize()
        return await self.queue.get()

    def get_nowait(self):
        self.initialize_queue()
        return self.queue.get_nowait()

    def put_nowait(self, item):
        self.initialize_queue()
        return self.queue.put_nowait(item)

    async def put(self, item):
        self.initialize_queue()
        if not self.ch.initialized:
            self.ch.initialize()
        return await self.queue.put(item)

    def empty(self):
        return self.queue.empty()


class ChannelBase(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            if not hasattr(self, k):
                setattr(self, k, v)

    def put_nowait(self, item):
        raise NotImplementedError

    async def put(self, item):
        return self.put_nowait(item)

    def create_queue(self) -> LazyAsyncQueue:
        raise NotImplementedError

    def __lshift__(self, other):
        """
        ch << 1 == ch.put_nowait(1)
        """
        self.put_nowait(other)
        return self

    def __rshift__(self, tasks) -> Union['Channel', Sequence['Channel']]:
        """
        ch >> task                   -> task(ch)
        ch >> [task1, _tasks, task3]  -> [task1(ch), task2(ch), task3(ch)]
        """
        if not isinstance(tasks, abc.Sequence):
            return tasks(self)

        outputs = [task(self) for task in tasks]
        if isinstance(tasks, tuple):
            outputs = tuple(tasks)
        return outputs

    def __or__(self, tasks) -> Union['Channel', Sequence['Channel']]:
        """
        ch | [a, b, c, d] equals to ch >> [a, b, c, d]
        """
        return self >> tasks

    @staticmethod
    def value(value, **kwargs):
        """
        Channel._output(1)
        """
        if callable(value):
            raise ValueError("You has passed a callable object as inputs, "
                             "you should explicitly specify the argument name like:"
                             "`ch.map(by=lambda x : x)`.")
        ch = ConstantChannel(**kwargs)
        ch.put_nowait(value)
        return ch

    @staticmethod
    def end():
        return ConstantChannel()

    @staticmethod
    def values(*args):
        """
        Channel.values(1, 2, 3, 4, 5)
        QueueChannel created by this method will always include a END signal
        """
        ch = Channel()
        for item in args:
            ch.put_nowait(item)
        ch.put_nowait(END)
        return ch

    @staticmethod
    def from_list(items: Sequence):
        """
        Channel.from_list([1, 2, 3, 4, 5])
        QueueChannel created by this method will always include a END signal
        """
        return Channel.values(*items)


class Channel(ChannelBase):

    def __init__(self, queue_factory: type = asyncio.Queue, **kwargs):
        super().__init__(**kwargs)
        self.buffer = SimpleQueue()
        self.initialized = False
        self.queues: List[LazyAsyncQueue] = []
        self.queue_factory = queue_factory
        self.id = flowsaber.context.random_id
        self.task_id = flowsaber.context.get('task_id')
        self.flow_id = flowsaber.context.get('flow_id')

    def serialize(self) -> ChannelInput:
        return ChannelInput(
            id=self.id,
            task_id=self.task_id,
            flow_id=self.flow_id
        )

    def initialize(self):
        if not self.initialized:
            self.initialized = True
            if self.buffer.qsize():
                # always put a END
                self.buffer.put(END)
                while not self.buffer.empty():
                    self.put_nowait(self.buffer.get())

    def put_nowait(self, item):
        if self.initialized:
            for q in self.queues:
                q.put_nowait(item)
        else:
            self.buffer.put(item)

    async def put(self, item):
        self.initialize()
        for q in self.queues:
            await q.put(item)

    def create_queue(self):
        q = LazyAsyncQueue(ch=self, queue_factory=self.queue_factory)
        self.queues.append(q)
        return q


class ConstantChannel(Channel):
    def __init__(self, **kwargs):
        super().__init__(queue_factory=ConstantQueue, **kwargs)


class Consumer(Fetcher):
    def __init__(self, *queues: LazyAsyncQueue, **kwargs):
        super().__init__(**kwargs)
        self.queues: List[LazyAsyncQueue] = list(queues)
        assert all(isinstance(q, LazyAsyncQueue) for q in self.queues)
        self.num_emitted = 0

    @property
    def empty(self):
        return len(self.queues) == 0

    @property
    def single(self):
        return len(self.queues) == 1

    def __len__(self):
        return len(self.queues)

    async def get(self):
        # make sure empty inputs only emit once
        if self.empty and self.num_emitted >= 1:
            return END
        values = []
        for q in self.queues:
            value = await q.get()
            if isinstance(value, End):
                return END
            values.append(value)
        self.num_emitted += 1
        # emit single input without tuple
        res = tuple(values) if not self.single else values[0]
        return res

    def get_nowait(self):
        # make sure empty inputs only emit once
        if self.empty and self.num_emitted >= 1:
            return END
        values = []
        for q in self.queues:
            value = q.get_nowait()
            if isinstance(value, End):
                return END
            values.append(value)
        self.num_emitted += 1
        # emit single input without tuple
        return tuple(values) if not self.single else values[0]

    @classmethod
    def from_channels(cls, *channels: Sequence[Union[Channel, object]], **kwargs) -> 'Consumer':
        channels = list(channels)
        for i, ch in enumerate(channels):
            if not isinstance(ch, Channel):
                if isinstance(ch, (tuple, list)) and any(isinstance(v, Channel) for v in ch):
                    raise ValueError(f"The _input: {ch} is a list/tuple of channels, "
                                     f"please unwrap it before pass into a Task/Flow")
                else:
                    channels[i] = Channel.value(ch)
            else:
                if ch.initialized:
                    raise ValueError("Can not create consumer from activated Channel, try to create"
                                     " the consumer before _running the flow.")
        queues = [ch.create_queue() for ch in channels]
        return cls(*queues, **kwargs)
