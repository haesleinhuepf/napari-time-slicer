
__version__ = "0.3.3"





from ._function import napari_experimental_provide_function

from napari.types import ImageData, LabelsData
import napari
import warnings
import numpy as np
from toolz import curry
from typing import Callable
from functools import wraps
import inspect
from qtpy.QtCore import QTimer
from ._workflow import WorkflowManager, CURRENT_TIME_FRAME_DATA, _get_layer_from_data, _break_down_4d_to_2d_kwargs, _viewer_has_layer
import time

from functools import partial
from magicgui import magicgui


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
            #print("No viewer provided, cannot read current time point.")
        else:
            workflow_manager = WorkflowManager.install(viewer)

            # in case of 4D-data (timelapse) crop out the current 3D timepoint
            if len(viewer.dims.current_step) == 4:
                current_timepoint = viewer.dims.current_step[0]
                _break_down_4d_to_2d_kwargs(bound.arguments, current_timepoint, viewer)

            # setup an updater which refreshes the view once the viewer dims have changed
            #currstep_event = viewer.dims.events.current_step
            #def update(event):
            #    currstep_event.disconnect(update)
            #    worker_function(*args, **kwargs)
            #if hasattr(function, 'updater'):
            #    currstep_event.disconnect(function.updater)
            #function.updater = update
            #currstep_event.connect(update)

            #print("Extracting a time step took", time.time() - start_time)
        start_time = time.time()

        # call the decorated function
        result = function(*bound.args, **bound.kwargs)
        #print("Computing result took", time.time() - start_time)

        start_time = time.time()
        if viewer is not None and result is not None:
            new_name = function.__name__ + " result"
            if hasattr(function, 'target_layer') and _viewer_has_layer(viewer, function.target_layer.name):
                function.target_layer.data = result
                result = None
            elif sig.return_annotation in [ImageData, "napari.types.ImageData"]:
                function.target_layer = viewer.add_image(result, name=new_name)
                result = None
            elif sig.return_annotation in [LabelsData, "napari.types.LabelsData"]:
                function.target_layer = viewer.add_labels(result, name=new_name)
                result = None
            else:
                print("Function has no target layer")

            print("Showing result took", time.time() - start_time)

            if result is None:
                start_time = time.time()

                workflow_manager.update(function.target_layer, function, *bound.args, **bound.kwargs)

                print("Storing workflow step", time.time() - start_time)


        return result

    return worker_function

