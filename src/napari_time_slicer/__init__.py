
__version__ = "0.0.1"





from ._function import napari_experimental_provide_function

import napari
import warnings
import numpy as np
from toolz import curry
from typing import Callable
from functools import wraps
import inspect
from qtpy.QtCore import QTimer


@curry
def time_slicer(function: Callable) -> Callable:
    @wraps(function)
    def worker_function(*args, **kwargs):
        args = list(args)
        print("Worker called")
        sig = inspect.signature(function)
        # create mapping from position and keyword arguments to parameters
        # will raise a TypeError if the provided arguments do not match the signature
        # https://docs.python.org/3/library/inspect.html#inspect.Signature.bind
        bound = sig.bind(*args, **kwargs)
        # set default values for missing arguments
        # https://docs.python.org/3/library/inspect.html#inspect.BoundArguments.apply_defaults
        bound.apply_defaults()

        viewer = None
        for key, value in bound.arguments.items():
            if isinstance(value, napari.Viewer):
                viewer = value

        print("checking viewer")
        if viewer is None:
            warnings.warn("No viewer provided, cannot read current time point.")
        else:
            print("checking dims")
            if len(viewer.dims.current_step) == 4:
                current_timepoint = viewer.dims.current_step[0]

                # copy images to GPU, and create output array if necessary
                for i, (key, value) in enumerate(bound.arguments.items()):
                    if isinstance(value, np.ndarray) or str(type(value)) in ["<class 'cupy._core.core.ndarray'>", "<class 'dask.array.core.Array'>"]:
                        print("checking data", value.shape)
                        if len(value.shape) == 4:
                            print("slicing time")
                            bound.arguments[key] = value[current_timepoint]
                        layer = get_layer_from_data(viewer, value)
                        if layer is not None:
                            if hasattr(function, "updater_" + key):
                                layer.events.data.disconnect(getattr(function, "updater_" + key))
                            updater = invoke_later_layer_update(layer, key, worker_function, i, args, kwargs)
                            setattr(function, "updater_" + key, updater)

            # refresh the view once the viewer dims have changed
            # we assume that the call order is the same as we build the workflow step by step
            # todo: it might be necessary to check which downstream plugins should be refreshed...
            currstep_event = viewer.dims.events.current_step

            def update(event):
                print("updating")
                currstep_event.disconnect(update)
                worker_function(*args, **kwargs)

            if hasattr(function, 'updater'):
                currstep_event.disconnect(function.updater)

            function.updater = update

            currstep_event.connect(update)

        # call the decorated function
        result = function(*bound.args, **bound.kwargs)

        if viewer is not None:
            if hasattr(function, 'target_layer'):
                if function.target_layer in viewer.layers:
                    function.target_layer.data = result

            def later():
                for layer in viewer.layers:
                    if layer.data is result:
                        function.target_layer = layer

            QTimer.singleShot(200, later)

        return result

    return worker_function

def get_layer_from_data(viewer, data):
    for layer in viewer.layers:
        if layer.data is data:
            return layer
    return None

def invoke_later_layer_update(layer, key, worker_function, arg_index, args, kwargs):
    def update_layer(event):
        value = layer.data
        if arg_index < len(args):
            args[arg_index] = value
        else:
            kwargs[key] = value
        worker_function(*args, *kwargs)

    layer.events.data.connect(update_layer)
    return update_layer


