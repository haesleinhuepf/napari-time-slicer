# from napari_time_slicer import threshold, image_arithmetic

# add your tests here...


def test_something(make_napari_viewer):
    viewer = make_napari_viewer()

    import numpy as np
    image = np.random.random((2, 2, 100, 100))
    layer = viewer.add_image(image)

    from napari_time_slicer._function import convert_to_2d_timelapse
    convert_to_2d_timelapse(layer)

def test_time_slicer(make_napari_viewer):
    import napari
    from napari_time_slicer import time_slicer

    @time_slicer
    def func(image, viewer:napari.Viewer):
        return image.shape

    viewer = make_napari_viewer()

    import numpy as np
    image = np.random.random((2, 2, 100, 100))
    layer = viewer.add_image(image)

    shape = func(image, viewer)

    assert len(shape) == 3


def test_slice_by_slice(make_napari_viewer):
    import napari
    from napari_time_slicer import slice_by_slice

    @slice_by_slice
    def func(image, viewer:napari.Viewer):
        assert len(image.shape) == 2
        return image

    viewer = make_napari_viewer()

    import numpy as np
    image = np.random.random((2, 100, 100))
    layer = viewer.add_image(image)

    image = func(image, viewer)

    assert len(image.shape) == 3


