from typing import TYPE_CHECKING

from enum import Enum
import numpy as np
from typing_extensions import Annotated
from napari_plugin_engine import napari_hook_implementation
from napari.layers import Image, Labels, Layer
from napari_tools_menu import register_function, register_action

LayerInput = Annotated[Layer, {"label": "Image"}]

@napari_hook_implementation
def napari_experimental_provide_function():
    return [convert_to_2d_timelapse]

@register_function(menu="Utilities > Convert 3D stack to 2D timelapse (time-slicer)")
def convert_to_2d_timelapse(layer : LayerInput) -> Layer:
    if isinstance(layer, Labels):
        return Labels(np.expand_dims(layer.data, axis=1), name="2d+t " + layer.name)
    else:
        return Image(np.expand_dims(layer.data, axis=1), name="2d+t " + layer.name)

