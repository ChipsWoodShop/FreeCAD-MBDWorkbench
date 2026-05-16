# MBDDatum.py

import FreeCAD


class MBDDatumFeature:
    """
    Semantic datum feature object.

    This is not merely construction geometry.
    It represents an MBD datum feature attached to model geometry.
    """

    def __init__(self, obj):
        obj.Proxy = self

        obj.addProperty(
            "App::PropertyString",
            "DatumLabel",
            "MBD",
            "Datum label, such as A, B, or C"
        )
        obj.DatumLabel = "A"

        obj.addProperty(
            "App::PropertyLink",
            "ReferencedObject",
            "MBD",
            "FreeCAD object containing the referenced geometry"
        )

        obj.addProperty(
            "App::PropertyString",
            "ReferencedSubelement",
            "MBD",
            "Referenced subelement name, such as Face3, Edge2, or Vertex1"
        )

        obj.addProperty(
            "App::PropertyEnumeration",
            "DatumType",
            "MBD",
            "Type of semantic datum feature"
        )
        obj.DatumType = ["Plane", "Axis", "Point", "Feature"]

        obj.addProperty(
            "App::PropertyString",
            "Standard",
            "MBD",
            "GD&T standard basis"
        )
        obj.Standard = "ASME Y14.5"

        obj.addProperty(
            "App::PropertyBool",
            "IsSemanticPMI",
            "MBD",
            "Marks this object as semantic PMI"
        )
        obj.IsSemanticPMI = True
        
        obj.addProperty(
            "App::PropertyVector",
            "CenterOfMass",
            "GeometrySignature",
            "Center of mass of referenced geometry"
        )

        obj.addProperty(
            "App::PropertyFloat",
            "Area",
            "GeometrySignature",
            "Area of referenced face"
        )

        obj.addProperty(
            "App::PropertyFloat",
            "FacePerimeter",
            "GeometrySignature",
            "Perimeter of referenced face"
        )

        obj.addProperty(
            "App::PropertyFloat",
            "EdgeLength",
            "GeometrySignature",
            "Length of referenced edge"
        )

        obj.addProperty(
            "App::PropertyString",
            "GeometryType",
            "GeometrySignature",
            "Underlying geometry type"
        )
    def execute(self, obj):
        pass


class ViewProviderMBDDatumFeature:
    def __init__(self, vobj):
        vobj.Proxy = self

    def getIcon(self):
        return ""

    def attach(self, vobj):
        pass

    def updateData(self, obj, prop):
        pass

    def onChanged(self, vobj, prop):
        pass

    def getDisplayModes(self, obj):
        return []

    def getDefaultDisplayMode(self):
        return "Flat Lines"

    def setDisplayMode(self, mode):
	    return mode

def update_geometry_signature(obj):

    if not obj.ReferencedObject:
        return

    shape = obj.ReferencedObject.Shape
    sub = obj.ReferencedSubelement

    target = None

    if sub.startswith("Face"):
        idx = int(sub[4:]) - 1
        target = shape.Faces[idx]

    elif sub.startswith("Edge"):
        idx = int(sub[4:]) - 1
        target = shape.Edges[idx]

    elif sub.startswith("Vertex"):
        idx = int(sub[6:]) - 1
        target = shape.Vertexes[idx]

    if target is None:
        return

    try:
        obj.CenterOfMass = target.CenterOfMass
    except:
        pass

    try:
        obj.Area = target.Area
    except:
        pass

    try:
        if sub.startswith("Face"):
            obj.FacePerimeter = target.Length
        elif sub.startswith("Edge"):
            obj.EdgeLength = target.Length
    except:
        pass

    try:
        surf = target.Surface
        obj.GeometryType = surf.__class__.__name__
    except:
        try:
            curve = target.Curve
            obj.GeometryType = curve.__class__.__name__
        except:
            obj.GeometryType = "Unknown"