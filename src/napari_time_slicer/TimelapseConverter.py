import numpy as np
from napari.layers import Points, Surface, Image, Labels, Vectors

class TimelapseConverter:
    """
    This class allows converting napari 4D layer data between different formats.
    """
    def __init__(self):

        # Supported LayerData types
        self.data_to_list_conversion_functions = {
            'napari.types.PointsData': self._points_to_list_of_points,
            'napari.types.SurfaceData': self._surface_to_list_of_surfaces,
            'napari.types.ImageData': self._image_to_list_of_images,
            'napari.types.LabelsData': self._image_to_list_of_images,
            'napari.types.VectorsData': self._vectors_to_list_of_vectors}

    # Supported list data types
        self.list_to_data_conversion_functions = {
            'napari.types.PointsData': self._list_of_points_to_points,
            'napari.types.SurfaceData': self._list_of_surfaces_to_surface,
            'napari.types.ImageData': self._list_of_images_to_image,
            'napari.types.LabelsData': self._list_of_images_to_image,
            'napari.types.VectorsData': self._list_of_vectors_to_vectors}

        # This list of aliases allows to map LayerDataTuples to the correct napari.types
        self.tuple_aliases = {
            'points': 'napari.types.PointsData',
            'surface': 'napari.types.SurfaceData',
            'image': 'napari.types.ImageData',
            'labels': 'napari.types.LabelsData',
            'vectors': 'napari.types.VectorsData',
            Points: 'napari.types.PointsData',
            Surface: 'napari.types.SurfaceData',
            Image: 'napari.types.ImageData',
            Labels: 'napari.types.LabelsData',
            Vectors: 'napari.types.VectorsData'}

        self.supported_4d_data = list(self.list_to_data_conversion_functions.keys())
        self.supported_list_data = list(self.data_to_list_conversion_functions.keys())

    def convert_4d_data_to_list(self, data, layertype: type) -> list:
        """
        Convert 4D data into a list of 3D data frames

        Parameters
        ----------
        data : 4D data to be converted
        layertype : layerdata type. Can be any of 'PointsData', `SurfaceData`,
        `ImageData`, `LabelsData` or `List[LayerDataTuple]`

        Raises
        ------
        TypeError
            Error to indicate that the converter does not support the passed
            layertype

        Returns
        -------
        list: List of 3D objects of type `layertype`

        """
        if layertype not in self.supported_4d_data:
            raise TypeError(f'{layertype} data to list conversion currently not supported.')

        conversion_function = self.data_to_list_conversion_functions[layertype]
        return conversion_function(data)

    def convert_list_to_4d_data(self, data, layertype: type) -> list:
        """
        Function to convert a list of 3D frames into 4D data.

        Parameters
        ----------
        data : list of 3D data (time)frames
        layertype : layerdata type. Can be any of 'PointsData', `SurfaceData`,
        `ImageData`, `LabelsData` or `List[LayerDataTuple]`

        Raises
        ------
        TypeError
            Error to indicate that the converter does not support the passed
            layertype

        Returns
        -------
        4D data of type `layertype`

        """
        if layertype not in self.supported_list_data:
            raise TypeError(f'{layertype} list to data conversion currently not supported.')
        conversion_function = self.list_to_data_conversion_functions[layertype]
        return conversion_function(data)

    # =============================================================================
    # Images
    # =============================================================================

    def _image_to_list_of_images(self, image: 'napari.types.ImageData') -> list:
        """Convert 4D image to list of images"""
        while len(image.shape) < 4:
            image = image[np.newaxis, :]
        return list(image)

    def _list_of_images_to_image(self, images: list) -> 'napari.types.ImageData':
        """Convert a list of 3D image data to single 4D image data."""
        while len(images[0].shape) < 3:
            images = [image[np.newaxis, :] for image in images]
        return np.stack(images)

    # =============================================================================
    # Points
    # =============================================================================

    def _list_of_points_to_points(self, points: list) -> np.ndarray:
        """Convert list of 3D point data to single 4D point data."""
        import pandas as pd

        # create dataframe for each set of points
        dataframes = [pd.DataFrame(frame, columns=['z', 'y', 'x']) for frame in points]

        # add frame column as first column to each dataframe
        for idx, df in enumerate(dataframes):
            df.insert(0, 't', idx)

        # concatenate dataframes and return as numpy array
        points_out = pd.concat(dataframes).values

        return points_out

    def _points_to_list_of_points(self, points: 'napari.types.PointsData') -> list:
        """Convert a 4D point array to list of 3D points"""
        import pandas as pd

        while points.shape[1] < 4:
            t = np.zeros(len(points), dtype=points.dtype)
            points = np.insert(points, 0, t, axis=1)

        # create dataframe with point coordinates and frame index
        df = pd.DataFrame(points, columns=['t', 'z', 'y', 'x'])

        # group by frame index and return list of points using groupby
        points_out = [group[['z', 'y', 'x']].values for _, group in df.groupby('t')]

        return points_out

    # =============================================================================
    # Vectors
    # =============================================================================

    def _vectors_to_list_of_vectors(self, vectors: 'napari.types.VectorsData') -> list:
        base_points = vectors[:, 0]
        vectors = vectors[:, 1]

        # the vectors and points should abide to the same dimensions
        point_list = self._points_to_list_of_points(base_points)
        vector_list = self._points_to_list_of_points(vectors)

        output_vectors = [
            np.stack([pt, vec]).transpose((1, 0, 2)) for pt, vec in zip(point_list, vector_list)]
        return output_vectors

    def _list_of_vectors_to_vectors(self, vectors: list) -> 'napari.types.VectorsData':
        base_points = [v[:, 0] for v in vectors]
        directions = [v[:, 1] for v in vectors]

        base_points = self._list_of_points_to_points(base_points)
        directions = self._list_of_points_to_points(directions)

        vectors = np.stack([base_points, directions]).transpose((1, 0, 2))
        return vectors

    # =============================================================================
    # Surfaces
    # =============================================================================

    def _surface_to_list_of_surfaces(self, surface: 'napari.types.SurfaceData') -> list:
        """Convert a 4D surface to list of 3D surfaces"""
        import pandas as pd

        points = surface[0]
        faces = np.asarray(surface[1], dtype=int)

        # Check if values were assigned to the surface
        has_values = False
        if len(surface) == 3:
            has_values = True
            values = surface[2]

        while points.shape[1] < 4:
            t = np.zeros(len(points), dtype=points.dtype)
            points = np.insert(points, 0, t, axis=1)

        # put points in dataframe and group by frame index
        # return list of points using groupby
        df_points = pd.DataFrame(points, columns=['t', 'z', 'y', 'x'])
        points_out = [group[['z', 'y', 'x']].values for _, group in df_points.groupby('t')]

        # put faces in dataframe and determine frame for each face
        df_faces = pd.DataFrame(faces, columns=['p1', 'p2', 'p3'])
        df_faces['t'] = df_points['t'].iloc[df_faces['p1']].values

        # group by frame index and return list of faces using groupby
        # subtract minimum point index from faces to make sure they start at 0
        faces_out = [group[['p1', 'p2', 'p3']].values for _, group in df_faces.groupby('t')]
        faces_out = [f - f.min() for f in faces_out]

        # if values were assigned to the surface, put them in dataframe and
        # group by frame index. Return list of values using groupby
        if has_values:
            df_values = pd.DataFrame(values, columns=['values'])
            df_values['t'] = df_points['t'].iloc[df_values.index].values
            values_out = [group['values'].values for _, group in df_values.groupby('t')]

        # put together points, faces and values (if available) for each frame
        # and return list of surfaces
        if has_values:
            surfaces_out = [(p, f, v) for p, f, v in zip(points_out, faces_out, values_out)]
        else:
            surfaces_out = [(p, f) for p, f in zip(points_out, faces_out)]

        return surfaces_out

    def _list_of_surfaces_to_surface(self, surfaces: list) -> tuple:
        """
        Convert list of 3D surfaces to single 4D surface.
        """
        # Put vertices, faces and values into separate lists
        # The original array is tuple (vertices, faces, values)
        vertices = [surface[0] for surface in surfaces]  # retrieve vertices
        faces = [surface[1] for surface in surfaces]  # retrieve faces

        # Surfaces do not necessarily have values - check if this is the case
        if len(surfaces[0]) == 3:
            values = np.concatenate([surface[2] for surface in surfaces])  # retrieve values if existant
        else:
            values = None

        vertices = self._list_of_points_to_points(vertices)

        n_vertices = 0
        for idx, surface in enumerate(surfaces):

            # Offset indices in faces list by previous amount of points
            faces[idx] = n_vertices + np.array(faces[idx])

            # Add number of vertices in current surface to n_vertices
            n_vertices += surface[0].shape[0]

        faces = np.vstack(faces)

        if values is None:
            return (vertices, faces)
        else:
            return (vertices, faces, values)