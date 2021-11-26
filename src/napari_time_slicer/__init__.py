
__version__ = "0.1.4"





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


class Workflow():

    def __init__(self):
        self.tasks = {}

    def set(self, name, func_or_data, *args, **kwargs):
        if name in self.tasks.keys():
            warnings.warn("Overwriting {}".format(name))
        if not callable(func_or_data):
            self.tasks[name] = func_or_data
            return

        sig = inspect.signature(func_or_data)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()

        self.tasks[name] = tuple([func_or_data] + [value for key, value in bound.arguments.items()])

    def get(self, name):
        ## Actually, all this should work with dask. But I don't manage.
        return dask_get(self.tasks, name)

    def __str__(self):
        out = ""
        for result, task in self.tasks.items():
            out = out + result + " <- "+ str(task) + "\n"
        return out



class WorkflowManager():

    @classmethod
    def install(cls, viewer: napari.Viewer):
        if not hasattr(WorkflowManager, "viewers_managers"):
            WorkflowManager.viewers_managers = {}

        if not viewer in WorkflowManager.viewers_managers.keys():
           WorkflowManager.viewers_managers[viewer] = WorkflowManager(viewer)
        return WorkflowManager.viewers_managers[viewer]

    def __init__(self, viewer: napari.Viewer):
        self.viewer = viewer
        self.workflow = Workflow()

        self.register_events_to_viewer(viewer)

    def register_events_to_viewer(self, viewer: napari.Viewer):
        viewer.dims.events.current_step.connect(self.slider_updated)

        viewer.layers.events.inserted.connect(self.layer_added)
        viewer.layers.events.removed.connect(self.layer_removed)
        viewer.layers.selection.events.changed.connect(self.layer_selection_changed)

    def update(self, target_layer, function, *args, **kwargs):
        print("Target:", target_layer)
        print("function:", function)

        def _layer_name_or_value(value, viewer):
            for l in viewer.layers:
                if l.data is value:
                    return l.name
            return value

        args = list(args)
        for i in range(len(args)):
            args[i] = _layer_name_or_value(args[i], self.viewer)
        if self.viewer in args:
            args.remove(self.viewer)
        args = tuple(args)

        self.workflow.set(target_layer.name, function, *args, **kwargs)
        print(self.workflow)

    def register_events_to_layer(self, layer):
        layer.events.data.connect(self.layer_data_updated)

    def layer_data_updated(self, event):
        print("Layer data updated", event.value, type(event.value))

    def layer_added(self, event):
        print("Layer added", event.value, type(event.value))

    def layer_removed(self, event):
        print("Layer removed", event.value, type(event.value))

    def slider_updated(self, event):
        pass
        #print("Slider updated", event.value, type(event.value))

    def layer_selection_changed(self, event):
        pass
        #print("Layer selection changed", event)

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

        if viewer is None:
            warnings.warn("No viewer provided, cannot read current time point.")
        else:
            workflow_manager = WorkflowManager.install(viewer)

            # in case of 4D-data (timelapse) crop out the current 3D timepoint
            if len(viewer.dims.current_step) == 4:
                current_timepoint = viewer.dims.current_step[0]
                for i, (key, value) in enumerate(bound.arguments.items()):
                    if isinstance(value, np.ndarray) or str(type(value)) in ["<class 'cupy._core.core.ndarray'>", "<class 'dask.array.core.Array'>"]:
                        if len(value.shape) == 4:
                            new_value = value[current_timepoint]
                            if new_value.shape[0] == 1:
                                new_value = new_value[0]
                            bound.arguments[key] = new_value

                        # setup an event that update computation in case the input-data changes
                        layer = _get_layer_from_data(viewer, value)
                        if hasattr(function, "updater_" + key):
                            layer.events.data.disconnect(getattr(function, "updater_" + key))
                        if layer is not None:
                            updater = _invoke_later_layer_update(layer, key, worker_function, i, args, kwargs)
                            setattr(function, "updater_" + key, updater)

            # setup an updater which refreshes the view once the viewer dims have changed
            currstep_event = viewer.dims.events.current_step
            def update(event):
                currstep_event.disconnect(update)
                worker_function(*args, **kwargs)
            if hasattr(function, 'updater'):
                currstep_event.disconnect(function.updater)
            function.updater = update
            currstep_event.connect(update)

        # call the decorated function
        result = function(*bound.args, **bound.kwargs)
        print("Re-executing")
        if viewer is not None and result is not None:
            print("Viewer exists", function)
            new_name = function.__name__ + " result"
            if hasattr(function, 'target_layer'):
                function.target_layer.data = result
                result = None
            elif sig.return_annotation in [ImageData]:
                print("Returning Image!")
                function.target_layer = viewer.add_image(result, name=new_name)
                result = None
            elif sig.return_annotation in [LabelsData]:
                print("Returning Labels!")
                function.target_layer = viewer.add_labels(result, name=new_name)
                result = None

            if result is None:
                workflow_manager.update(function.target_layer, function, *bound.args, **bound.kwargs)

            # after the result has been added to napari, we will go through
            # napari's layers and find out in which layer the result was stored
            #if hasattr(function, 'target_layer'):
            #    print("Target:" + function.target_layer)
            #    if function.target_layer in viewer.layers:
            #        function.target_layer.data = result
            #def later():
            #    print("Doing later")
            #    for layer in viewer.layers:
            #        print("Checking", layer)
            #        if layer.data is result:
            #            print("Setting target_layer")
            #            function.target_layer = layer
            #        print("Wtf")
            #QTimer.singleShot(400, later)

        return result

    return worker_function

def _get_layer_from_data(viewer, data):
    """
    Returns the layer in viewer that has the given data
    """
    for layer in viewer.layers:
        if layer.data is data:
            return layer
    return None

def _invoke_later_layer_update(layer, key, worker_function, arg_index, args, kwargs):
    """
    Set up a updater when given layer was changed.
    """
    def update_layer(event):
        value = layer.data
        if arg_index < len(args):
            args[arg_index] = value
        else:
            kwargs[key] = value
        worker_function(*args, *kwargs)

    layer.events.data.connect(update_layer)
    return update_layer
