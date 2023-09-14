# -*- coding: utf-8 -*-

"""
/***************************************************************************
 StationOffset
                                 A QGIS plugin
 This plugin computes the station and offset of points along polylines and exports those values to csv for other applications
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2023-05-17
        copyright            : (C) 2023 by Tailwater Limited
        email                : applications@tailwaterlimited.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

__author__ = 'Tailwater Limited'
__date__ = '2023-09-13'
__copyright__ = '(C) 2023 by Tailwater Limited'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtCore import QUrlQuery

from qgis.core import (QgsProcessing,
                       QgsProcessingAlgorithm,
                       QgsProcessingFeedback,
                       QgsProcessingParameters,
                       QgsProcessingParameterFile,
                       QgsProcessingParameterCrs,
                       QgsVectorLayer,
                       QgsProcessingOutputVectorLayer,
                       QgsProject,
                       QgsCoordinateReferenceSystem
                       )

import math

class PNEZDAlgorithm(QgsProcessingAlgorithm):
    """
    This algorithm imports a PNEZD file
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    CRSINPUT = 'EPSG:4326'
    INPUTFILE = 'INPUT_FILE'
    OUTPUT = 'OUTPUT'
    
    def initAlgorithm(self, config):
        """
        There is 1 input file for this algorithm the PNEZD text file. This file is formatted as a comma separated file in Point Number, Northing,
        Easting, Elevation, Description format.
        """

        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUTFILE,
                self.tr('PNEZD File (csv, txt)'),
                behavior = QgsProcessingParameterFile.File,
                fileFilter='PNEZD (*.csv)',
                defaultValue=None))

        self.addParameter(
             QgsProcessingParameterCrs(
                 self.CRSINPUT,
                 self.tr('Coordinate System'),
                 defaultValue='EPSG:6529'))

        self.addOutput(
            QgsProcessingOutputVectorLayer(self.OUTPUT,
            self.tr('Vector Layer'),
            type = QgsProcessing.TypeVectorAnyGeometry))

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        
        """
        results = {}
        outputs = {}

        crs = self.parameterAsCrs(parameters, self.CRSINPUT, context)
        csvfileName = self.parameterAsString(parameters, self.INPUTFILE, context)
  

        url = QUrl.fromLocalFile(csvfileName)
        query = QUrlQuery() 
        query.addQueryItem('crs', crs.authid())
        query.addQueryItem('index', 'yes')
        query.addQueryItem('type', 'csv')
        query.addQueryItem('xField', 'field_3')
        query.addQueryItem('yField', 'field_2')
        query.addQueryItem('geomType','point')
        query.addQueryItem('useHeader', 'no')
        query.addQueryItem('detectTypes', 'yes')
        query.addQueryItem('spatialIndex', 'yes')
        url.setQuery(query)

        uri = url.toString()
        layer = QgsVectorLayer(uri, "Survey Points",'delimitedtext')
        layer.setFieldAlias(0, 'PN')
        layer.setFieldAlias(1, 'Northing')
        layer.setFieldAlias(2, 'Easting')
        layer.setFieldAlias(3, 'Elevation')
        layer.setFieldAlias(4, 'Description')

        QgsProject.instance().addMapLayer(layer)

        return {self.OUTPUT : layer }


    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'importPNEZD'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return 'Create Delimited Text Layer from PNEZD File'

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr('Stream Tools')

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'streamtools'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return PNEZDAlgorithm()