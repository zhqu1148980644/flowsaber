# this default context will only work in the build time
# during the flow/task run, will use context in flow/task as the initial context
DEFAULT_CONTEXT = {
    'default_flow_config': {
        'check_cancellation_interval': 5,
        'test__': {
            'test__': [1, 2, 3]
        },
        'log_stdout': True,
        'log_stderr': True,
    },
    'default_task_config': {
        'executor_type': 'dask',
        'test__': {
            'test__': [1, 2, 3]
        },
        'timeout': 0,
        'log_stdout': True,
        'log_stderr': True,
    },
    # logging options can be flow/task specific, here we treat it as global options for simplicity
    'logging': {
        'fmt': "[{levelname}] [{filename}:{lineno}-{funcName}()] "
               "task:{task_full_name} taskrun:{taskrun_id: <10} {message}",
        'datefmt': "%Y-%m-%d %H:%M:%S",
        'style': '{',
        'level': 'INFO',
        'buffer_size': 10,
        'context_attrs': [
            'flow_id',
            'task_id',
            'flow_name',
            'task_name',
            'flow_full_name',
            'task_full_name',
            'agent_id',
            'id',
            'taskrun_id',
        ]
    },
    'caches': [
        {
            'cache_type': 'local'
        },
        {
            'cache_type': 'cloud',
            'address': 'xxxx',
            'cache_kwargs': None
        }
    ],
    'executors': [
        {
            'executor_type': 'local'
        },
        {
            'executor_type': 'dask',
            'address': None,
            'cluster_class': None,
            'cluster_kwargs': None,
            # TODO for best performance, use threads as worker, however, there may be bugs related to context and CWD
            # 'cluster_kwargs': {'threads_per_worker': 1},
            'adapt_kwargs': None,
            'client_kwargs': None,
            'debug': False
        }
    ]
}