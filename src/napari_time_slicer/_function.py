from typing import TYPE_CHECKING

from enum import Enum
import numpy as np
from typing_extensions import Annotated
from napari_plugin_engine import napari_hook_implementation
from napari.layers import Image, Labels, Layer
from napari_tools_menu import register_function, register_action
import napari
import tempfile

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

@register_function(menu="Utilities > Convert on-the-fly processed timelapse to 4D stack (time-slicer)")
def convert_to_stack4d(layer : LayerInput, viewer: napari.Viewer) -> Layer:
    """
    Go through time (by moving the time-slider in napari) and copy 3D frames of a given layer
    and store them in a new 4D layer in napari.
    """
    # in case of 4D-data (timelapse) crop out the current 3D timepoint
    if len(viewer.dims.current_step) != 4:
        raise NotImplementedError("Processing all frames only supports 4D-data")
    if len(layer.data.shape) >= 4:
        raise NotImplementedError("Processing all frames only supports on-the-fly processed 2D and 3D data")

    current_timepoint = viewer.dims.current_step[0]
    max_time = int(viewer.dims.range[-4][1])

    result = None

    for f in range(max_time):
        print("Processing frame", f)

        # go to a specific time point
        _set_timepoint(viewer, f)

        # get the layer data at a specific time point
        result_single_frame = np.asarray(layer.data).copy()

        if len(result_single_frame.shape) == 2:
            result_single_frame = np.asarray([result_single_frame])

        if result is None:
            result = [result_single_frame]
        else:
            result.append(result_single_frame)

    output_data = np.asarray(result)
    print("Output:", output_data.shape)

    # go back to the time point selected before
    _set_timepoint(viewer, current_timepoint)

    if isinstance(layer, Labels):
        return Labels(output_data, name="Stack 4D " + layer.name)
    else:
        return Image(output_data, name="Stack 4D " + layer.name)



@register_function(menu="Utilities > Convert to file-backed timelapse data (time-slicer)",
                      folder_name = dict(widget_type='FileEdit', mode='d'))
def convert_to_file_backed_timelapse(layer : LayerInput,
                                     folder_name: "magicgui.types.PathLike" = "",
                                     viewer: napari.Viewer = None) -> Layer:
    """
    Save a 4D stack to disk and create a new layer that reads only the current timepoint from disk
    """
    if len(viewer.dims.current_step) != 4:
        raise NotImplementedError("Convert to file-backed timelapse data only supports 4D-data")

    from skimage.io import imsave
    import os

    folder_name = str(folder_name)
    if len(folder_name) == 0 or folder_name == ".":

        folder_name = tempfile.TemporaryDirectory().name.replace("\\", "/") + "/"

    folder_name = str(folder_name).replace("\\", "/")
    if not folder_name.endswith("/"):
        folder_name = folder_name + "/"

    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    print("Writing to ", folder_name)

    if len(layer.data.shape) < 4: # presumably on-the-fly-processed
        print("Presumably found an on-the-fly-processed timelapse dataset. Computing frames...")
        # layer = convert_to_stack4d(layer, viewer)

        current_timepoint = viewer.dims.current_step[0]
        max_time = int(viewer.dims.range[-4][1])

        for f in range(max_time):
            print("Processing frame", f)

            # go to a specific time point
            _set_timepoint(viewer, f)

            # get the layer data at a specific time point
            data = np.asarray(layer.data).copy()

            if len(data.shape) == 2:
                data = np.asarray([data])

            filename = str(folder_name) + "%02d" % (f,) + ".tif"
            imsave(filename, data)

        # go back to the time point selected before
        _set_timepoint(viewer, current_timepoint)

    else:
        max_time = layer.data.shape[0]
        for f in range(max_time):
            # save to disk
            data = layer.data[f]
            filename = str(folder_name) + "%02d" % (f,) + ".tif"
            imsave(filename, data)

    return load_file_backed_timelapse(folder_name, isinstance(layer, Labels), "File-backed " + layer.name, viewer)

@register_function(menu="Utilities > Load file-backed timelapse data (time-slicer)",
                      folder_name = dict(widget_type='FileEdit', mode='d'))
def load_file_backed_timelapse(folder_name: "magicgui.types.PathLike" = "",
                                is_labels:bool = False,
                                name:str = "",
                                viewer: napari.Viewer = None) -> Layer:
    """
    Load a folder of tif-images where every tif-file corresponds to a frame in a 4D stack.
    """
    import os
    from skimage.io import imsave
    from functools import partial
    import dask.array as da
    from dask import delayed
    list_of_loaders = []

    folder_name = str(folder_name).replace("\\", "/")
    if not folder_name.endswith("/"):
        folder_name = folder_name + "/"

    file_list = os.listdir(folder_name)
    file_list = sorted(file_list)
    file_list = [file for file in file_list if file.endswith(".tif")]

    data = None
    for filename in file_list:
        if data is None:
            # read first frame to determine size and type
            data = _potentially_add_dimension_imread(folder_name + filename)

        # create delayed loader
        loader = da.from_delayed(delayed(partial(_potentially_add_dimension_imread, folder_name + filename))(), shape=data.shape, dtype=data.dtype)
        list_of_loaders.append(loader)

    # Stack into one large dask.array
    stack = da.stack(
        list_of_loaders,
        axis=0)

    if name is None or len(name) == 0:
        name = "File-backed " + folder_name.split("/")[-2]

    if is_labels:
        return Labels(stack, name=name)
    else:
        return Image(stack, name=name)

def _potentially_add_dimension_imread(filename):
    from skimage.io import imread

    data = imread(filename)
    if len(data.shape) == 2:
        data = np.asarray([data])
    return data

def _set_timepoint(viewer, current_timepoint):
    variable_timepoint = list(viewer.dims.current_step)
    variable_timepoint[0] = current_timepoint
    viewer.dims.current_step = variable_timepoint
    _refresh_viewer(viewer)

# from: https://github.com/haesleinhuepf/napari-skimage-regionprops/blob/b08ac8e5558fe72529378bf076489671c837571f/napari_skimage_regionprops/_all_frames.py#L132
def _refresh_viewer(viewer):
    if viewer is None:
        return

    from napari_workflows import WorkflowManager
    wm = WorkflowManager.install(viewer)
    w = wm.workflow

    while(wm._search_first_invalid_layer (w.roots()) is not None):
        wm._update_invalid_layer()
