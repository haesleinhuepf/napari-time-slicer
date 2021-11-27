

from ._function import napari_experimental_provide_function
from ._dock_widget import napari_experimental_provide_dock_widget

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

    def roots(self):
        origins = []
        for result, task in self.tasks.items():
            for source in task:
                if isinstance(source, str):
                    if not source in list(self.tasks.keys()):
                        if source not in origins:
                            origins.append(source)
        return origins

    def followers_of(self, item):
        followers = []
        for result, task in self.tasks.items():
            for source in task:
                if isinstance(source, str):
                    if source == item:
                        if result not in followers:
                            followers.append(result)
        return followers

    def sources_of(self, item):
        if item not in self.tasks.keys():
            return []
        task = self.tasks[item]
        return [i for i in task if isinstance(i, str)]

    def leafs(self):
        return [l for l in self.tasks.keys() if len(self.followers_of(l)) == 0]

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
