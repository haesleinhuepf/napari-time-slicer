from typing import TYPE_CHECKING

from enum import Enum
import numpy as np
from typing_extensions import Annotated
from napari_plugin_engine import napari_hook_implementation
from napari.layers import Image, Labels, Layer
from napari_tools_menu import register_function, register_action
import napari

LayerInput = Annotated[Layer, {"label": "Image"}]

@napari_hook_implementation
def napari_experimental_provide_function():
    return [convert_to_2d_timelapse]

@register_function(menu="Utilities > Convert 3D stack to 2D timelapse (time-slicer)")
def convert_to_2d_timelapse(layer : LayerInput, viewer:napari.Viewer = None) -> Layer:
    if isinstance(layer, Labels):
        result = Labels(layer.data[:,np.newaxis,:,:], name="2d+t " + layer.name)
    else:
        result = Image(layer.data[:,np.newaxis,:,:], name="2d+t " + layer.name)

    if viewer is not None:
        step = viewer.dims.current_step
        step = (step[0], 0, step[1], step[2])
        viewer.dims.current_step = step
    return result

@register_function(menu="Utilities > Convert on-the-fly processed timelapse to 4D stack")
def convert_to_stack4d(layer : LayerInput, viewer: napari.Viewer) -> Layer:
    """
    Go through time (by moving the time-slider in napari) and copy 3D frames of a given layer
    and store them in a new 4D layer in napari.
    """
    # in case of 4D-data (timelapse) crop out the current 3D timepoint
    if len(viewer.dims.current_step) != 4:
        raise NotImplementedError("Processing all frames only supports 4D-data")

    variable_timepoint = list(viewer.dims.current_step)
    current_timepoint = variable_timepoint[0]
    max_time = int(viewer.dims.range[-4][1])

    result = None

    for f in range(max_time):
        print("Processing frame", f)

        # go to a specific time point
        variable_timepoint[0] = f
        viewer.dims.current_step = variable_timepoint
        _refresh_viewer(viewer)

        # get the layer data at a specific time point
        result_single_frame = np.asarray(layer.data).copy()

        if result is None:
            result = [result_single_frame]
        else:
            result.append(result_single_frame)

    output_data = np.asarray(result)
    print("Output:", output_data.shape)

    # go back to the time point selected before
    variable_timepoint[0] = current_timepoint
    viewer.dims.current_step = variable_timepoint
    _refresh_viewer(viewer)

    if isinstance(layer, Labels):
        return Labels(output_data, name="Stack 4D " + layer.name)
    else:
        return Image(output_data, name="Stack 4D " + layer.name)

# from: https://github.com/haesleinhuepf/napari-skimage-regionprops/blob/b08ac8e5558fe72529378bf076489671c837571f/napari_skimage_regionprops/_all_frames.py#L132
def _refresh_viewer(viewer):
    if viewer is None:
        return

    from napari_workflows import WorkflowManager
    wm = WorkflowManager.install(viewer)
    w = wm.workflow

    while(wm._search_first_invalid_layer (w.roots()) is not None):
        wm._update_invalid_layer()
