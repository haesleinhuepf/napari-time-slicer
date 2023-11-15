import numpy as np
import pytest
from napari_time_slicer import TimelapseConverter

converter = TimelapseConverter()

# create a fixture for 4D points
@pytest.fixture
def points_4d():
    return np.array(
        [
            [0, 1, 2, 3],
            [0, 2, 3, 4],
            [0, 3, 4, 5],
            [1, 3, 4, 5],
            [1, 4, 5, 6],
            [1, 5, 6, 7],
            ]
        )


def test_image_conversion():
    # Create mock 4D data
    img_4d = np.random.rand(5, 10, 10, 10)

    # Convert 4D data to list
    img_list = converter.convert_4d_data_to_list(img_4d, 'napari.types.ImageData')

    # Convert list back to 4D data
    img_4d_converted = converter.convert_list_to_4d_data(img_list, 'napari.types.ImageData')

    # Assert equality
    assert np.array_equal(img_4d, img_4d_converted)


def test_points_conversion(points_4d):
    # Convert 4D data to list
    points_list = converter.convert_4d_data_to_list(points_4d, 'napari.types.PointsData')
    assert len(points_list) == 2

    # Convert list back to 4D data
    points_4d_converted = converter.convert_list_to_4d_data(points_list, 'napari.types.PointsData')

    # Assert equality
    assert np.array_equal(points_4d, points_4d_converted)


def test_vectors_conversion(points_4d):

    vectors_4d = np.array([points_4d, points_4d]).transpose(1, 0, 2)

    # Convert 4D data to list
    vectors_list = converter.convert_4d_data_to_list(vectors_4d, 'napari.types.VectorsData')
    assert len(vectors_list) == 2

    # Convert list back to 4D data
    vectors_4d_converted = converter.convert_list_to_4d_data(vectors_list, 'napari.types.VectorsData')

    # Assert equality
    assert np.array_equal(vectors_4d, vectors_4d_converted)


def test_surface_to_list_of_surfaces(points_4d):
    faces = np.array([[0, 1, 2], [3, 4, 5]])
    values = np.arange(len(points_4d))
    surfaces_4d = (points_4d, faces, values)
    surfaces_list = converter._surface_to_list_of_surfaces(surfaces_4d)
    assert len(surfaces_list) == 2  # Since we have two distinct timepoints


def test_list_of_surfaces_to_surface(points_4d):
    # Sample data with 2 time points and corresponding 3D surfaces
    # We will use the points_4d fixture to extract two separate time point data for our sample surfaces_list
    points_time_0 = points_4d[points_4d[:, 0] == 0][:, 1:]
    points_time_1 = points_4d[points_4d[:, 0] == 1][:, 1:]
    faces = np.array([[0, 1, 2]])
    surfaces_list = [(points_time_0, faces, np.array([10])),
                     (points_time_1, faces, np.array([20]))]
    surface_4d = converter._list_of_surfaces_to_surface(surfaces_list)
    assert len(surface_4d) == 3  # Ensure points, faces, and values are returned

    # Optionally, validate the content/structure of surface_4d
    assert np.array_equal(surface_4d[0], points_4d)  # The 4D points data should match


def test_layer_conversion(points_4d, make_napari_viewer):
    from napari.layers import Points, Layer

    list_of_points = converter.convert_4d_data_to_list(points_4d, 'napari.types.PointsData')

    layer_list = []
    for points in list_of_points:
        new_layer = Points(points, features={
            'feature_1': np.random.rand(len(points)),
        })
        layer_list.append(new_layer)

    # Convert list back to 4D data
    layer_4d = converter.convert_list_to_4d_data(layer_list, layertype=Layer)

    viewer = make_napari_viewer()
    viewer.add_layer(layer_4d)

    assert len(viewer.layers) == 1
