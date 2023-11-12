
__version__ = "0.5.0"

from ._function import napari_experimental_provide_function

import napari
from toolz import curry
from typing import Callable
from functools import wraps
import time
import inspect
import numpy as np
# most imports here are just for backwards compatbility
from ._workflow import WorkflowManager, CURRENT_TIME_FRAME_DATA, _get_layer_from_data, _break_down_4d_to_2d_kwargs, _viewer_has_layer


@curry
def time_slicer(function: Callable) -> Callable:
    has_viewer_parameter = False

    @wraps(function)
    def worker_function(*args, **kwargs):
        args = list(args)

        # Retrieve the viewer parameter so that we can know which current timepoint is selected
        viewer = None
        for key, value in kwargs.items():
            if isinstance(value, napari.Viewer):
                viewer = value
        if viewer is None:
            for value in args:
                if isinstance(value, napari.Viewer):
                    viewer = value
                    break

        if not has_viewer_parameter:
            if "viewer" in kwargs.keys():
                kwargs.pop("viewer")

        sig = inspect.signature(function)
        # create mapping from position and keyword arguments to parameters
        # will raise a TypeError if the provided arguments do not match the signature
        # https://docs.python.org/3/library/inspect.html#inspect.Signature.bind
        bound = sig.bind(*args, **kwargs)
        # set default values for missing arguments
        # https://docs.python.org/3/library/inspect.html#inspect.BoundArguments.apply_defaults
        bound.apply_defaults()


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

    # If the function has now "viewer" parameter, we add one so that we can read out the current timepoint later
    import inspect
    sig = inspect.signature(worker_function)
    parameters = []
    for name, value in sig.parameters.items():
        if name == "viewer" or name == "napari_viewer" or "napari.viewer.Viewer" in str(value.annotation):
            has_viewer_parameter = True
        parameters.append(value)
    if not has_viewer_parameter:
        parameters.append(inspect.Parameter("viewer", inspect.Parameter.KEYWORD_ONLY, annotation="napari.viewer.Viewer", default=None))
    worker_function.__signature__ = inspect.Signature(parameters, return_annotation=sig.return_annotation)

    return worker_function


@curry
def slice_by_slice(function: Callable) -> Callable:
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

        # determine the largest z-stack in the parameter list
        max_z = 0
        for key, value in bound.arguments.items():
            if isinstance(value, np.ndarray) or str(type(value)) in ["<class 'cupy._core.core.ndarray'>",
                                                                     "<class 'dask.array.core.Array'>"]:
                if len(value.shape) == 3:
                    max_z = value.shape[0] - 1

        if max_z == 0:  # no stack in parameter list
            # just call the decorated function
            result = function(*bound.args, **bound.kwargs)
        else:
            # in case of 3D-data (stack) crop out the current 2D slice
            slices = []
            bound_arguments_copy = bound.arguments.copy()

            for z in range(max_z + 1):
                # replace 3D images with a given slice
                for key, value in bound_arguments_copy.items():
                    if isinstance(value, np.ndarray) or str(type(value)) in ["<class 'cupy._core.core.ndarray'>",
                                                                             "<class 'dask.array.core.Array'>"]:
                        if len(value.shape) == 3:
                            z_slice = min(z, value.shape[0] - 1)
                            image = value[z_slice]
                            bound.arguments[key] = image

                # call the decorated function
                slices.append(function(*bound.args, **bound.kwargs))
            result = np.asarray(slices)

        return result

    return worker_function


