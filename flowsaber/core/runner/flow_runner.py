import asyncio

from flowsaber.core.runner.runner import *
from flowsaber.core.scheduler import TaskScheduler
from flowsaber.core.utility.state import *
from flowsaber.server.database.models import FlowRunInput


class FlowRunner(Runner):
    def __init__(self, flow, **kwargs):
        super().__init__(**kwargs)
        assert flow.initialized
        self.flow = flow

    @property
    def context(self):
        return self.flow.context

    def serialize(self, old_state: State, new_state: State) -> RunInput:
        flowrun_input = FlowRunInput(id=self.id, state=new_state.to_dict())
        if isinstance(old_state, Scheduled) and isinstance(new_state, Pending):
            flowrun_input.__dict__.update({
                'task_id': flowsaber.context.get('task_id'),
                'flow_id': flowsaber.context.get('flow_id'),
                'agent_id': flowsaber.context.get('agent_id'),
                'name': flowsaber.context.get('flow_name'),
                'labels': flowsaber.context.get('flow_labels'),
                'inputs': {},
                'context': flowsaber.context.to_dict()
            })

        return flowrun_input

    # @run_within_context,  Now context is not merged with server supplied context
    @call_state_change_handlers
    @catch_to_failure
    def run(self, state: State, **kwargs) -> State:
        state = self.initialize_run(state)
        state = self.set_state(state, Pending)
        state = self.set_state(state, Running)
        state = self.run_flow(state, **kwargs)

        return state

    @call_state_change_handlers
    @catch_to_failure
    def run_flow(self, state, **kwargs):
        res = asyncio.run(self.async_run_flow(**kwargs))
        state = Success.copy(state)
        state.result = res
        return state

    async def async_run_flow(self, **kwargs):
        async with TaskScheduler().start() as scheduler:
            res = await self.flow.start(scheduler=scheduler, **kwargs)
        return res
