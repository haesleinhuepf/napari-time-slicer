
__version__ = "0.4.0"

from ._function import napari_experimental_provide_function

import napari
from toolz import curry
from typing import Callable
from functools import wraps
import time
import inspect
# most imports here are just for backwards compatbility
from ._workflow import WorkflowManager, CURRENT_TIME_FRAME_DATA, _get_layer_from_data, _break_down_4d_to_2d_kwargs, _viewer_has_layer


@curry
def time_slicer(function: Callable) -> Callable:

    @wraps(function)
    def worker_function(*args, **kwargs):
        args = list(args)
        sig = inspect.signature(function)
        # create mapping from position and keyword arguments to parameters
        # will raise a TypeError if the provided arguments do not match the signature
        # https://docs.python.org/3/library/inspect.html#inspect.Signature.bind
        bound = sig.bind(*args, **kwargs)
        # set default values for missing arguments
        # https://docs.python.org/3/library/inspect.html#inspect.BoundArguments.apply_defaults
        bound.apply_defaults()

        # Retrieve the viewer parameter so that we can know which current timepoint is selected
        viewer = None
        for key, value in bound.arguments.items():
            if isinstance(value, napari.Viewer):
                viewer = value

        start_time = time.time()

        if viewer is None:
            pass
        else:
            # in case of 4D-data (timelapse) crop out the current 3D timepoint
            if len(viewer.dims.current_step) == 4:
                current_timepoint = viewer.dims.current_step[0]
                _break_down_4d_to_2d_kwargs(bound.arguments, current_timepoint, viewer)

        # call the decorated function
        result = function(*bound.args, **bound.kwargs)
        return result

    return worker_function

