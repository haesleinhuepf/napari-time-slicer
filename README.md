# napari-time-slicer

[![License](https://img.shields.io/pypi/l/napari-time-slicer.svg?color=green)](https://github.com/haesleinhuepf/napari-time-slicer/raw/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/napari-time-slicer.svg?color=green)](https://pypi.org/project/napari-time-slicer)
[![Python Version](https://img.shields.io/pypi/pyversions/napari-time-slicer.svg?color=green)](https://python.org)
[![tests](https://github.com/haesleinhuepf/napari-time-slicer/workflows/tests/badge.svg)](https://github.com/haesleinhuepf/napari-time-slicer/actions)
[![codecov](https://codecov.io/gh/haesleinhuepf/napari-time-slicer/branch/main/graph/badge.svg)](https://codecov.io/gh/haesleinhuepf/napari-time-slicer)
[![napari hub](https://img.shields.io/endpoint?url=https://api.napari-hub.org/shields/napari-time-slicer)](https://napari-hub.org/plugins/napari-time-slicer)

A meta plugin for processing timelapse data timepoint by timepoint. It 
enables a list of napari plugins to process 2D+t or 3D+t data step by step when the user goes 
through the timelapse. Currently, these plugins are using `napari-time-slicer`:
* [napari-segment-blobs-and-things-with-membranes](https://www.napari-hub.org/plugins/napari-segment-blobs-and-things-with-membranes)
* [napari-cupy-image-processing](https://www.napari-hub.org/plugins/napari-cupy-image-processing)
* [napari-pyclesperanto-assistant](https://www.napari-hub.org/plugins/napari-pyclesperanto-assistant)
* [napari-accelerated-pixel-and-object-classification](https://www.napari-hub.org/plugins/napari-accelerated-pixel-and-object-classification)
* [napari-mahotas-image-processing](https://www.napari-hub.org/plugins/napari-mahotas-image-processing)
* [napari-simpleitk-image-processing](https://www.napari-hub.org/plugins/napari-simpleitk-image-processing)

`napari-time-slicer` enables inter-plugin communication, e.g. allowing to combine the plugins listed above in 
one image processing workflow for segmenting a timelapse dataset:

![](https://github.com/haesleinhuepf/napari-time-slicer/raw/main/images/screencast1.gif)

The workflow can then also be exported as a script. The 'Generate Code' button can be found in the [Workflow Inspector](https://www.napari-hub.org/plugins/napari-workflow-inspector)


If you want to convert a 3D dataset into a 2D + time dataset, use the 
menu `Tools > Utilities > Convert 3D stack to 2D timelapse (time-slicer)`. It will turn the 3D dataset to a 4D datset
where the Z-dimension (index 1) has only 1 element, which will in napari be displayed with a time-slider. Note: It is 
recommended to remove the original 3D dataset after this conversion.

## Usage for plugin developers

Plugins which implement the `napari_experimental_provide_function` hook can make use of the `@time_slicer`. At the moment,
only functions which take `napari.types.ImageData`, `napari.types.LabelsData` and basic python types such as `int` 
and `float` are supported. If you annotate such a function with `@time_slicer` it will internally convert any 4D dataset
to a 3D dataset according to the timepoint currently selected in napari. Furthermore, when the napari user changes the
current timepoint or the input data of the function changes, a re-computation is invoked. Thus, it is recommended to 
only use the `time_slicer` for functions which can provide [almost] real-time performance. Another constraint is that 
these annotated functions have to have a `viewer` parameter. This is necessary to read the current timepoint from the 
viewer when invoking the re-computions.

Example
```python
import napari
from napari_time_slicer import time_slicer

@time_slicer
def threshold_otsu(image:napari.types.ImageData, viewer: napari.Viewer = None) -> napari.types.LabelsData:
    # ...
```

You can see a full implementations of this concept in the napari plugins listed above.

----------------------------------

This [napari] plugin was generated with [Cookiecutter] using [@napari]'s [cookiecutter-napari-plugin] template.

## Installation

You can install `napari-time-slicer` via [pip]:

    pip install napari-time-slicer



To install latest development version :

    pip install git+https://github.com/haesleinhuepf/napari-time-slicer.git


## Contributing

Contributions are very welcome. Tests can be run with [tox], please ensure
the coverage at least stays the same before you submit a pull request.

## License

Distributed under the terms of the [BSD-3] license,
"napari-time-slicer" is free and open source software

## Issues

If you encounter any problems, please [file an issue] along with a detailed description.

[napari]: https://github.com/napari/napari
[Cookiecutter]: https://github.com/audreyr/cookiecutter
[@napari]: https://github.com/napari
[MIT]: http://opensource.org/licenses/MIT
[BSD-3]: http://opensource.org/licenses/BSD-3-Clause
[GNU GPL v3.0]: http://www.gnu.org/licenses/gpl-3.0.txt
[GNU LGPL v3.0]: http://www.gnu.org/licenses/lgpl-3.0.txt
[Apache Software License 2.0]: http://www.apache.org/licenses/LICENSE-2.0
[Mozilla Public License 2.0]: https://www.mozilla.org/media/MPL/2.0/index.txt
[cookiecutter-napari-plugin]: https://github.com/napari/cookiecutter-napari-plugin

[file an issue]: https://github.com/haesleinhuepf/napari-time-slicer/issues

[napari]: https://github.com/napari/napari
[tox]: https://tox.readthedocs.io/en/latest/
[pip]: https://pypi.org/project/pip/
[PyPI]: https://pypi.org/
