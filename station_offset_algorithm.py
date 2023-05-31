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
__date__ = '2023-05-17'
__copyright__ = '(C) 2023 by Tailwater Limited'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsProcessing,
                       QgsFeatureSink,
                       QgsProcessingAlgorithm,
                       QgsProcessingFeedback,
                       QgsProcessingParameters,
                       QgsProcessingParameterField,
                       QgsProcessingParameterFileDestination,
                       QgsProcessingParameterNumber,
                       QgsGeometryUtils,
                       QgsPoint,
                       QgsPointXY,
                       QgsGeometry,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFeatureSink)
from station_offset.station_offset_calc import (calcDistance,
                                                projectPoint)
import math

class StationOffsetAlgorithm(QgsProcessingAlgorithm):
    """
    This algorithm creates a csv file containing the station and offset
    associated with points and polylines.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    OUTPUT = 'OUTPUT'
    INPUTLINE = 'INPUT_LINE'
    INPUTLINENAMEFIELD = 'INPUT_LINENAMEFIELD'
    INPUTPOINTS = 'INPUT_POINTS'
    INPUTPOINTNUMBERFIELD = 'INPUT_POINTNUMBERFIELD'
    INPUTPOINTDESCRIPTIONFIELD = 'INPUT_POINTDESCRIPTIONFIELD'
    INPUTPOINTELEVATIONFIELD = 'INPUT_POINTELEVATIONFIELD'
    INPUTMAXOFFSET = 'INPUT_MAXOFFSET'
    
    def initAlgorithm(self, config):
        """
        There are 8 inputs created by the processing tools. The first is the Alignment (polyline feature) followed by the attribute field containing the alignment name.
        Next is the point feature followed by attribute fields for description, point number, and elevation
        Followed by the desired offset to evaluate  default value is 99999
        and last is the output file name.
        """

        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUTLINE,
                self.tr('Alignment Lines'),
                types=[QgsProcessing.TypeVectorLine],
                defaultValue=None))

        self.addParameter(QgsProcessingParameterField(
            self.INPUTLINENAMEFIELD,
            self.tr('Attribute with Alignment Name'),
            defaultValue=None,
            parentLayerParameterName=self.INPUTLINE,
            type=QgsProcessingParameterField.String,
            allowMultiple=False))

        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUTPOINTS,
                self.tr('Survey Points'),
                types=[QgsProcessing.TypeVectorPoint],
                defaultValue=None))
        
        self.addParameter(
            QgsProcessingParameterField(
                self.INPUTPOINTDESCRIPTIONFIELD,
                self.tr('Attribute with Point Description'),
                defaultValue=None,
                parentLayerParameterName=self.INPUTPOINTS,
                type=QgsProcessingParameterField.String,
                allowMultiple=False))

        self.addParameter(
            QgsProcessingParameterField(
                self.INPUTPOINTNUMBERFIELD,
                self.tr('Attribute with Point Number'),
                defaultValue=None,
                parentLayerParameterName=self.INPUTPOINTS,
                type=QgsProcessingParameterField.Numeric,
                allowMultiple=False))
        
        self.addParameter(QgsProcessingParameterField(
            self.INPUTPOINTELEVATIONFIELD,
            self.tr('Attribute with Elevation'),
            defaultValue=None,
            parentLayerParameterName=self.INPUTPOINTS,
            type=QgsProcessingParameterField.Numeric,
            allowMultiple=False))
        
        self.addParameter(
            QgsProcessingParameterNumber(
                self.INPUTMAXOFFSET,
                'Maximum offset',
                defaultValue=99999,
                type=QgsProcessingParameterNumber.Double,
                minValue=0))
        

        # We add a feature sink in which to store our processed features (this
        # usually takes the form of a newly created vector layer when the
        # algorithm is run in QGIS).
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT,
                self.tr('Output Filename'),
                'CSV files (*.csv)'))

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        The lines and points are loaded and csv file created to generate output.
        
        This algorithm makes no changes to any of the input features.
        """

        pointLayer = self.parameterAsVectorLayer(parameters,self.INPUTPOINTS,context)
        
        lineLayer = self.parameterAsVectorLayer(parameters,self.INPUTLINE,context)
        lineFeatures = lineLayer.getFeatures()
        
        nameAttributeField= self.parameterAsString(parameters, self.INPUTLINENAMEFIELD,context)
        descriptionAttributeField= self.parameterAsString(parameters, self.INPUTPOINTDESCRIPTIONFIELD,context)
        pnAttributeField = self.parameterAsString(parameters, self.INPUTPOINTNUMBERFIELD,context)
        eleAttributeField = self.parameterAsString(parameters, self.INPUTPOINTELEVATIONFIELD, context)

        maxOffset = self.parameterAsDouble(parameters, self.INPUTMAXOFFSET, context)
        
        outfileName = self.parameterAsString(parameters, self.OUTPUT, context)
        
        #get the name for the output file.
        #console.show_console()
        try:
            outfile = open(outfileName,"w")
        except OSError:
            print("Could not open outfile", outfile)
            return {}
        outfile.write("Alignment, Point Number, Station, Offset, Elevation, Description \n")
        for lineFeature in lineFeatures:
            #If cancel is pressed exit
            if feedback.isCanceled():
                break
            lineGeom = QgsGeometry(lineFeature.geometry())
            lineName = lineFeature.attribute(nameAttributeField)
            if(lineGeom.isMultipart()):
                verticies = lineGeom.asMultiPolyline()[0]
                #model_feedback.pushInfo("Multipart geometry detected using first part in multipart geometry. Additional parts will be ignored")
            else:
                verticies = lineGeom.asPolyline()
            vertex_m = [] #Create an empty list for this
            n = len(verticies)
            print("vertex count " + str(n))
            vertex_m.append(0) #Add the first virtex
            if(n<2):
                continue
            i = 1
            for i in range(1,n):
                St = verticies[i-1]
                Ed = verticies[i]
                distance = math.sqrt((Ed.x()-St.x())**2+(Ed.y()-St.y())**2)
                vertex_m.append(vertex_m[i-1] + distance)
            pointFeatures = pointLayer.getFeatures()
            for pointFeature in pointFeatures:
                pointDescription = pointFeature.attribute(descriptionAttributeField)
                pn = pointFeature.attribute(pnAttributeField)
                elevation = pointFeature.attribute(eleAttributeField)
                #Calulate the distance
                pointGeometry = pointFeature.geometry().asPoint()
                offset, p, segment = projectPoint(verticies, pointGeometry, maxOffset, feedback)
                
                #point, vertex index before, vertex index after, sqrDistance
                if offset is None:
                    outfile.write(lineName + ", " + str(pn) + ", " + "Out of Range" + ", " + "Out of Range" + ", " + str(elevation) + ", " + pointDescription + "\n")
                else:
                    dist = calcDistance(verticies[segment],p)
                    station = vertex_m[segment] + dist
                    outfile.write(lineName + ", " + str(pn) + ", " + str(station) + ", " + str(offset) + ", " + str(elevation) + ", " + pointDescription + "\n")
            verticies.clear()
            vertex_m.clear()
            n = 0
            
        outfile.close()
        return {self.OUTPUT: outfileName}

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'stationOffset'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr(self.name())

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
        return StationOffsetAlgorithm()
