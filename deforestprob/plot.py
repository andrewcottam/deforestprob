#!/usr/bin/python

# ==============================================================================
# author          :Ghislain Vieilledent
# email           :ghislain.vieilledent@cirad.fr, ghislainv@gmail.com
# web             :https://ghislainv.github.io
# python_version  :2.7
# license         :GPLv3
# ==============================================================================

# Import
import sys
import os
from glob import glob
from osgeo import gdal, ogr
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Rectangle
from matplotlib.backends.backend_pdf import PdfPages


# Plot vector objects
# (https://github.com/cgarrard/osgeopy-code/blob/master/Chapter13/listing13_3.py)
def plot_polygon(poly, symbol='k-', **kwargs):
    """Plots a polygon using the given symbol."""
    for i in range(poly.GetGeometryCount()):
        subgeom = poly.GetGeometryRef(i)
        x, y = zip(*subgeom.GetPoints())
        plt.plot(x, y, symbol, **kwargs)


# Use this function to fill polygons.
# Uncomment this one and comment out the one above.
# def plot_polygon(poly, symbol='w', **kwargs):
#     """Plots a polygon using the given symbol."""
#     for i in range(poly.GetGeometryCount()):
#         x, y = zip(*poly.GetGeometryRef(i).GetPoints())
#         plt.fill(x, y, symbol, **kwargs)


def plot_line(line, symbol='k-', **kwargs):
    """Plots a line using the given symbol."""
    x, y = zip(*line.GetPoints())
    plt.plot(x, y, symbol, **kwargs)


def plot_point(point, symbol='ko', **kwargs):
    """Plots a point using the given symbol."""
    x, y = point.GetX(), point.GetY()
    plt.plot(x, y, symbol, **kwargs)


def plot_layer(filename, symbol, layer_index=0, **kwargs):
    """Plots an OGR layer using the given symbol."""
    ds = ogr.Open(filename)
    for row in ds.GetLayer(layer_index):
        geom = row.geometry()
        geom_type = geom.GetGeometryType()

        # Polygons
        if geom_type == ogr.wkbPolygon:
            plot_polygon(geom, symbol, **kwargs)

        # Multipolygons
        elif geom_type == ogr.wkbMultiPolygon:
            for i in range(geom.GetGeometryCount()):
                subgeom = geom.GetGeometryRef(i)
                plot_polygon(subgeom, symbol, **kwargs)

        # Lines
        elif geom_type == ogr.wkbLineString:
            plot_line(geom, symbol, **kwargs)

        # Multilines
        elif geom_type == ogr.wkbMultiLineString:
            for i in range(geom.GetGeometryCount()):
                subgeom = geom.GetGeometryRef(i)
                plot_line(subgeom, symbol, **kwargs)

        # Points
        elif geom_type == ogr.wkbPoint:
            plot_point(geom, symbol, **kwargs)

        # Multipoints
        elif geom_type == ogr.wkbMultiPoint:
            for i in range(geom.GetGeometryCount()):
                subgeom = geom.GetGeometryRef(i)
                plot_point(subgeom, symbol, **kwargs)


# plot.correlation
def correlation(y, data,
                output_file="output/correlation.pdf",
                plots_per_page=4,
                figsize=(8.27, 11.69),
                dpi=100):
    """
    Correlation between variables and the probability of deforestation.

    This function plots (i) the histogram of the explicative variables
    and (ii) the probability of deforestation by bins of equal number of
    observations for each explicative variable.

    :param y: a 1D array for the response variable (forest=1, defor=0).
    :param data: a pandas DataFrame with column names.
    :param output_file: path to output file.
    :param plots_per_page: number of plots (lines) per page.
    :param figsize: figure size.
    :param dpi: resolution for output image.
    :return: list of Matplotlib figures.
    """

    # Data
    y = 1 - y  # Transform: defor=1, forest=0
    perc = np.arange(0, 110, 10)
    nperc = len(perc)
    colnames = data.columns.values
    # The PDF document
    pdf_pages = PdfPages(output_file)
    # Generate the pages
    nb_plots = len(colnames)
    nb_plots_per_page = plots_per_page
    #  nb_pages = int(np.ceil(nb_plots / float(nb_plots_per_page)))
    grid_size = (nb_plots_per_page, 2)
    # List of figures to be returned
    figures = []
    # Loop on variables
    for i in range(nb_plots):
        # Create a figure instance (ie. a new page) if needed
        if i % nb_plots_per_page == 0:
            fig = plt.figure(figsize=figsize, dpi=dpi)
        varname = colnames[i]
        theta = np.zeros(nperc - 1)
        se = np.zeros(nperc - 1)
        x = np.zeros(nperc - 1)
        quantiles = np.nanpercentile(data[varname], q=perc)
        # Compute theta and se by bins
        for j in range(nperc - 1):
            inf = quantiles[j]
            sup = quantiles[j + 1]
            x[j] = inf + (sup - inf) / 2
            y_bin = y[(data[varname] > inf) &
                      (data[varname] <= sup)]
            y_bin = np.array(y_bin)  # Transform into np.array to compute sum
            s = float(sum(y_bin == 1))  # success
            n = len(y_bin)  # trials
            if n is not 0:
                theta[j] = s / n
            else:
                theta[j] = np.nan
            ph = (s + 1 / 2) / (n + 1)
            se[j] = np.sqrt(ph * (1 - ph) / (n + 1))
        # Plots
        # Histogram
        plt.subplot2grid(grid_size, (i % nb_plots_per_page, 0))
        Arr = np.array(data[varname])
        Arr = Arr[~np.isnan(Arr)]
        plt.hist(Arr, facecolor="#808080", alpha=0.75)
        plt.xlabel(varname, fontsize=16)
        plt.ylabel("Nb. of observations", fontsize=16)
        # Corelation
        plt.subplot2grid(grid_size, (i % nb_plots_per_page, 1))
        plt.plot(x, theta, color="#000000", marker='o', linestyle='--')
        plt.xlabel(varname, fontsize=16)
        plt.ylabel("Defor. probability", fontsize=16)
        # Close the page if needed
        if (i + 1) % nb_plots_per_page == 0 or (i + 1) == nb_plots:
            plt.tight_layout()
            figures.append(fig)
            pdf_pages.savefig(fig)
    # Write the PDF document to the disk
    pdf_pages.close()
    return (figures)


# plot.forest
def forest(input_forest_raster,
           output_file="output/forest.png",
           borders=None,
           zoom=None,
           col=(255, 0, 0, 255),
           figsize=(11.69, 8.27),
           dpi=200):
    """Plot the forest map.

    This function plots the forest map. Green is the remaining forest
    (value 1), the color specified is for deforestation (value 0).

    :param input_forest_raster: path to forest raster.
    :param output_file: name of the plot file.
    :param borders: vector file to be plotted.
    :param zoom: zoom to region (xmin, xmax, ymin, ymax).
    :param col: rgba color for deforestation.
    :param figsize: figure size in inches.
    :param dpi: resolution for output image.
    :return: a Matplotlib figure of the forest map.

    """

    # Load raster and band
    forestR = gdal.Open(input_forest_raster)
    forestB = forestR.GetRasterBand(1)
    forestND = forestB.GetNoDataValue()
    gt = forestR.GetGeoTransform()
    ncol = forestR.RasterXSize
    nrow = forestR.RasterYSize
    Xmin = gt[0]
    Xmax = gt[0] + gt[1] * ncol
    Ymin = gt[3] + gt[5] * nrow
    Ymax = gt[3]
    extent = [Xmin, Xmax, Ymin, Ymax]

    # Overviews
    if forestB.GetOverviewCount() == 0:
        # Build overviews
        print("Build overview")
        forestR.BuildOverviews("nearest", [8, 16, 32])
    # Get data from finest overview
    ov_band = forestB.GetOverview(0)
    ov_arr = ov_band.ReadAsArray()
    ov_arr[ov_arr == forestND] = 2

    # Colormap
    colors = []
    cmax = 255.0  # float for division
    col = tuple(np.array(col)/cmax)
    colors.append(col)  # default is red
    colors.append((34/cmax, 139/cmax, 34/cmax, 1))  # forest green
    colors.append((0, 0, 0, 0))  # transparent
    color_map = ListedColormap(colors)

    # Plot raster and save
    place = 111 if zoom is None else 121
    fig = plt.figure(figsize=figsize, dpi=dpi)
    ax1 = plt.subplot(place)
    ax1.set_frame_on(False)
    ax1.set_xticks([])
    ax1.set_yticks([])
    plt.imshow(ov_arr, cmap=color_map, extent=extent)
    if borders is not None:
        plot_layer(borders, symbol="k-")
    plt.axis("off")
    if zoom is not None:
        z = Rectangle(
            (zoom[0], zoom[2]),
            zoom[1]-zoom[0],
            zoom[3]-zoom[2],
            fill=False
        )
        ax1.add_patch(z)
        ax2 = plt.subplot(222)
        plt.imshow(ov_arr, cmap=color_map, extent=extent)
        plt.xlim(zoom[0], zoom[1])
        plt.ylim(zoom[2], zoom[3])
        ax2.set_xticks([])
        ax2.set_yticks([])
    plt.close(fig)
    # Save and return figure
    fig.tight_layout()
    fig.savefig(output_file, dpi=dpi, bbox_inches="tight")
    return(fig)


# plot.obs
def obs(sample,
        name_forest_var,
        input_forest_raster,
        output_file="output/obs.png",
        zoom=None,
        s=20,
        figsize=(11.69, 8.27),
        dpi=200):
    """Plot the sample points over the forest map.

    This function plots the sample points over the forest map. Green
    is the remaining forest (value 1), red is the deforestation (value
    0).

    :param sample: pandas DataFrame with observation coordinates (X, Y).
    :param name_forest_var: name of the forest variable in sample DataFrame.
    :param input_forest_raster: path to forest raster.
    :param output_file: name of the plot file.
    :param zoom: zoom to region (xmin, xmax, ymin, ymax).
    :param s: marker size for sample points.
    :param figsize: figure size in inches.
    :param dpi: resolution for output image.
    :return: a Matplotlib figure of the sample points.

    """

    # Load raster and band
    forestR = gdal.Open(input_forest_raster)
    forestB = forestR.GetRasterBand(1)
    forestND = forestB.GetNoDataValue()
    gt = forestR.GetGeoTransform()
    ncol = forestR.RasterXSize
    nrow = forestR.RasterYSize
    Xmin = gt[0]
    Xmax = gt[0] + gt[1] * ncol
    Ymin = gt[3] + gt[5] * nrow
    Ymax = gt[3]
    extent = [Xmin, Xmax, Ymin, Ymax]

    # Overviews
    if forestB.GetOverviewCount() == 0:
        # Build overviews
        print("Build overview")
        forestR.BuildOverviews("nearest", [8, 16, 32])
    # Get data from finest overview
    ov_band = forestB.GetOverview(0)
    ov_arr = ov_band.ReadAsArray()
    ov_arr[ov_arr == forestND] = 2

    # Colormap
    colors = []
    cmax = 255.0  # float for division
    colors.append((1, 0, 0, 1))  # red
    colors.append((34/cmax, 139/cmax, 34/cmax, 1))  # forest green
    colors.append((0, 0, 0, 0))  # transparent
    color_map = ListedColormap(colors)

    # Plot raster and save
    fig = plt.figure(dpi=dpi)
    ax1 = plt.subplot(111)
    # No frame
    ax1.set_frame_on(False)
    ax1.set_xticks([])
    ax1.set_yticks([])
    plt.axis("off")
    # Raster
    plt.imshow(ov_arr, cmap=color_map, extent=extent)
    # Points
    f = name_forest_var
    x_defor = sample[sample[f] == 0]["X"]
    y_defor = sample[sample[f] == 0]["Y"]
    x_for = sample[sample[f] == 1]["X"]
    y_for = sample[sample[f] == 1]["Y"]
    plt.scatter(x_defor, y_defor,
                color="darkred", s=s)
    plt.scatter(x_for, y_for,
                color="darkgreen", s=s)
    if zoom is not None:
        plt.xlim(zoom[0], zoom[1])
        plt.ylim(zoom[2], zoom[3])
    plt.close(fig)
    # Save and return figure
    fig.tight_layout()
    fig.savefig(output_file, dpi=dpi, bbox_inches="tight")
    return(fig)


# plot.var
def var(var_dir,
        output_file="output/var.pdf",
        gridsize=(3, 3),
        figsize=(11.69, 8.27),
        dpi=200):
    """Plot variable maps.

    This function plots variable maps.

    :param var_dir: path to variable directory.
    :param output_file: name of the plot file.
    :param grid_size: grid size per page.
    :param figsize: figure size in inches.
    :param dpi: resolution for output image.
    :return: list of Matplotlib figures.

    """

    # Raster list
    var_tif = var_dir + "/*.tif"
    raster_list = glob(var_tif)
    raster_list.sort()
    nrast = len(raster_list)

    # The PDF document
    pdf_pages = PdfPages(output_file)
    # Generate the pages
    gridsize = gridsize
    ny = gridsize[0]
    nx = gridsize[1]
    nplot_per_page = ny*nx
    # List of figures to be returned
    figures = []

    # Loop on raster files
    for i in range(nrast):

        # Create a figure instance (ie. a new page) if needed
        if i % nplot_per_page == 0:
            fig = plt.figure(figsize=figsize, dpi=dpi)

        # Open raster and get band
        r = gdal.Open(raster_list[i])
        b = r.GetRasterBand(1)
        ND = b.GetNoDataValue()
        if ND is None:
            print("NoData value is not specified \
            for input raster file %s" % raster_list[i])
            sys.exit(1)

        # Raster name
        base_name = os.path.basename(raster_list[i])
        index_dot = base_name.index(".")
        raster_name = base_name[:index_dot]

        # Raster info
        gt = r.GetGeoTransform()
        ncol = r.RasterXSize
        nrow = r.RasterYSize
        Xmin = gt[0]
        Xmax = gt[0] + gt[1] * ncol
        Ymin = gt[3] + gt[5] * nrow
        Ymax = gt[3]
        extent = [Xmin, Xmax, Ymin, Ymax]

        # Overviews
        if b.GetOverviewCount() == 0:
            # Build overviews
            print("Build overview")
            r.BuildOverviews("nearest", [8, 16, 32])
        # Get data from finest overview
        ov_band = b.GetOverview(0)
        ov_arr = ov_band.ReadAsArray()
        mov_arr = np.ma.array(ov_arr, mask=(ov_arr == ND))
        # Plot raster
        ax = plt.subplot2grid(gridsize,
                              ((i % nplot_per_page)/nx, i % nx))
        ax.set_frame_on(False)
        ax.set_xticks([])
        ax.set_yticks([])
        plt.imshow(mov_arr, extent=extent)
        plt.title(raster_name)
        plt.axis("off")

        # Close the page if needed
        if (i + 1) % nplot_per_page == 0 or (i + 1) == nrast:
            plt.tight_layout()
            figures.append(fig)
            pdf_pages.savefig(fig)

    # Write the PDF document to the disk
    pdf_pages.close()
    return (figures)

# End
