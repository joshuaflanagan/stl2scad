#!/usr/bin/python
# -*- coding: utf-8 -*-

""" STL to SCAD converter.

This code is based on Riham javascript code.
See http://www.thingiverse.com/thing:62666

Ascii STL file:

solid _40x10
    facet normal 0.000000e+000 0.000000e+000 1.000000e+000
        outer loop
            vertex 1.286803e+001 2.957990e+001 1.200000e+001
            vertex 1.173648e+001 2.984808e+001 1.200000e+001
            vertex 1.115715e+001 2.953001e+001 1.200000e+001
        endloop
    endfacet
    facet normal 0.000000e+000 0.000000e+000 1.000000e+000
        outer loop
            vertex 1.115715e+001 2.953001e+001 1.200000e+001
            vertex 1.173648e+001 2.984808e+001 1.200000e+001
            vertex 1.058145e+001 2.998308e+001 1.200000e+001
        endloop
    endfacet
    ...
ensolid

Binary STL file:

"""

import re
import sys
import struct
import os.path
import argparse
import numpy

def parseAscii(inputFile):
    """
    """
    inputFile.seek(0)
    inputStr = inputFile.read()

    modules = []

    solidName = None
    vertices = None
    faces = None
    face = None

    for solidStr in re.findall(r"solid\s(.*?)endsolid", inputStr, re.S):
        solidName = re.match(r"^(.*)$", solidStr, re.M).group(0)
        print ("Processing object %s..." % solidName)
        vertices = []
        faces = []
        for facetStr in re.findall(r"facet\s(.*?)endfacet", solidStr, re.S):
            for outerLoopStr in re.findall(r"outer\sloop(.*?)endloop", facetStr, re.S):
                face = []
                for vertexStr in re.findall(r"vertex\s(.*)$", outerLoopStr, re.M):
                    vertex = [float(coord) for coord in vertexStr.split()]
                    try:
                        face.append(vertices.index(vertex))
                    except ValueError:
                        vertices.append(vertex)
                        face.append(len(vertices) - 1)
            face[1], face[2] = face[2], face[1]
            faces.append(str(face))
        modules.append((solidName, vertices, faces))

        return modules


def parseBinary(inputFile, solidName="stl2scad"):
    """
    """

    # Skip header
    inputFile.seek(80)

    nbTriangles = struct.unpack("<I", inputFile.read(4))[0]
    print ("found %d faces" % nbTriangles)

    modules = []
    vertices = []
    faces = []

    face = None

    # Iterate over faces
    for i in range(nbTriangles):
        face = []

        # Skip normal vector (3x uint32)
        inputFile.seek(3*4, 1)

        # Iterate over vertices
        for j in range(3):
            vertex = struct.unpack("<fff", inputFile.read(3*4))
            #print repr(s), repr(vertex)
            try:
                face.append(vertices.index(vertex))
            except ValueError:
                vertices.append(list(vertex))
                face.append(len(vertices) - 1)

        face[1], face[2] = face[2], face[1]
        faces.append(str(face))

        # Skip byte count
        inputFile.seek(2, 1)

    modules.append((solidName, vertices, faces))

    return modules


def convert(outputFile, modules, backCompat, boundingBox):
    """
    """
    for solidName, vertices, faces in modules:
        points_ = ",\n\t\t\t".join(map(str,vertices))
        faces_ = ",\n\t\t\t".join(faces)
        if backCompat:
            facesArg = "triangles"
        else:
            facesArg = "faces"
        npAry = numpy.array(vertices)
        mins = npAry.min(0)
        maxs = npAry.max(0)
        diffs = maxs - mins

        if boundingBox:
            boundingBox = ("\n\ttranslate([%s])\n\t\t%%cube([%s]);\n" %
                    (
                        ", ".join(map(str, mins)),
                        ", ".join(map(str, diffs))
                        )
                    )
        else:
            boundingBox = ""

        module = ("module %s() {%s\n\tpolyhedron(\n\t\tpoints=[\n\t\t\t%s\n\t\t],\n\t\t%s=[\n\t\t\t%s\n\t\t]\n\t);\n}\n\n\n%s();\n" %
                 (solidName, boundingBox, points_, facesArg, faces_, solidName))
        outputFile.write(module)

    outputFile.close()


def main():
    parser = argparse.ArgumentParser(description='Convert an .stl file to an OpenSCAD .scad file')
    parser.add_argument("stl_file", help="The .stl file to convert")
    parser.add_argument("-B", "--bounding-box", action='store_true', help="include a non-rendered bounding-box around the model")
    parser.add_argument("-C", "--scad-version", choices=['2014.03', 'current'],
            default='current', help="specify an older version of OpenSCAD, for backward compatibility")
    args = parser.parse_args()
    print (args.scad_version)
    inputFileName = args.stl_file
    with open(inputFileName, 'rb') as testFile:
        isACII = (testFile.read(5) == b'solid')

    if isACII:
        inputFile = open(inputFileName)
        modules = parseAscii(inputFile)
    else:
        inputFile = open(inputFileName, 'rb')
        modules = parseBinary(inputFile)

    outputFileName = "%s%s%s" % (os.path.splitext(inputFileName)[0], os.path.extsep, "scad")

    outputFile = open(outputFileName, "w")
    convert(outputFile, modules, args.scad_version == '2014.03', args.bounding_box)

    print ("%s saved" % outputFileName)


if __name__ == "__main__":
    main()
