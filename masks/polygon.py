import numpy

from .mask import Mask


class PolygonMask(Mask):
    """
    A mask that is defined by the corners of a polygon
    """

    def __init__(self, corners):
        self.corners = corners

    @property
    def lowerleft(self):
        return numpy.min(self.corners, axis=0).astype(int)

    @property
    def upperright(self):
        return numpy.max(self.corners, axis=0).astype(int) + 1

    @property
    def weights(self):
        """Generate the weight mask of the rectangular area covering the given polygon."""
        # shift the polygon such that ll is the new origin
        spoly = self.corners - self.lowerleft

        # width and height of roi
        W, H = (self.upperright - self.lowerleft)

        from PIL import Image, ImageDraw
        mimg = Image.new('I', (W * 10, H * 10), 0)
        l = [(r[0] * 10, r[1] * 10) for r in spoly]
        ImageDraw.Draw(mimg).polygon(xy=l, outline=False, fill=1)

        # create a numpy array of the image where the extra resolution pixels are wrapped into extra dimensions
        mimg = numpy.array(mimg).reshape((H, 10, W, 10))

        return mimg.sum(axis=1).sum(axis=-1).astype(float) / 100.

    def __call__(self, data, mask=None):
        # get the rectangular fov that fully covers a polygon
        rowslice = slice(max(self.lowerleft[1], 0), min(self.upperright[1], data.shape[0]))
        colslice = slice(max(self.lowerleft[0], 0), min(self.upperright[0], data.shape[1]))
        # get a view on the data of interest
        dataview = data[rowslice, colslice]
        Cs, Rs = (self.upperright - self.lowerleft)
        Cl, Rl = self.lowerleft
        weightmask = self.weights[max(-Rl, 0):min(Rs, data.shape[0] - Rl), max(-Cl, 0):min(Cs, data.shape[1] - Cl)]

        if mask is None:
            doi = weightmask[..., numpy.newaxis] * dataview
            weight = weightmask.sum()
        else:
            mask = mask[rowslice, colslice]
            doi = weightmask[..., numpy.newaxis] * mask[..., numpy.newaxis] * dataview
            weight = (weightmask * mask).sum()

        return doi.sum(axis=0).sum(axis=0) / weight