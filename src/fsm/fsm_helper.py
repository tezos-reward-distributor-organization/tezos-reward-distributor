from enum import Enum


def to_name(state):
    if isinstance(state, Enum):
        return state.name

    return state


def to_list(item):
    if isinstance(item, set):
        return list(item)

    if isinstance(item, list):
        return item

    return [item]
