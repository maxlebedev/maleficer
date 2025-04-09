import enum

import esper


PHASES = dict()


class Phase(enum.Enum):
    menu = enum.auto()
    level = enum.auto()
    target = enum.auto()




def to_phase(phase: Phase, start_proc: type[esper.Processor] | None = None):
    """We dynamically add and remove processors when moving between phases. Each phase has it s own proc loop."""
    for proc in esper._processors:
        esper.remove_processor(type(proc))
    esper._processors = []

    proc_list = PHASES[phase]
    if start_proc:
        while start_proc and not isinstance(proc_list[0], start_proc):
            proc_list.append(proc_list.pop(0))

    proc_list = list(reversed(proc_list))
    for i, proc in enumerate(proc_list):
        esper.add_processor(proc, priority=i)


def oneshot(proctype: type[esper.Processor]):
    proc_instance = esper.get_processor(proctype)
    if proc_instance:
        proc_instance.process()
