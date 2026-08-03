# MBDGeometrySignature.py

import math
import FreeCAD


def vector_tuple(v):
    return (round(v.x, 6), round(v.y, 6), round(v.z, 6))


def face_signature(face):
    surf = face.Surface

    sig = {
        "ShapeType": "FACE",
        "Area": round(face.Area, 6),
        "CenterOfMass": vector_tuple(face.CenterOfMass),
        "BoundBox": (
            round(face.BoundBox.XMin, 6),
            round(face.BoundBox.YMin, 6),
            round(face.BoundBox.ZMin, 6),
            round(face.BoundBox.XMax, 6),
            round(face.BoundBox.YMax, 6),
            round(face.BoundBox.ZMax, 6),
        ),
        "SurfaceType": type(surf).__name__,
    }

    try:
        u = (face.ParameterRange[0] + face.ParameterRange[1]) / 2
        v = (face.ParameterRange[2] + face.ParameterRange[3]) / 2
        normal = face.normalAt(u, v)
        sig["Normal"] = vector_tuple(normal)
    except Exception:
        sig["Normal"] = None

    if hasattr(surf, "Radius"):
        sig["Radius"] = round(surf.Radius, 6)

    if hasattr(surf, "Axis"):
        sig["Axis"] = vector_tuple(surf.Axis)

    return sig


def compare_signatures(old, new):
    warnings = []

    if old.get("SurfaceType") != new.get("SurfaceType"):
        warnings.append(
            "Surface type changed: {} -> {}".format(
                old.get("SurfaceType"),
                new.get("SurfaceType")
            )
        )

    old_area = old.get("Area")
    new_area = new.get("Area")
    if old_area and new_area:
        pct = abs(new_area - old_area) / old_area * 100.0
        if pct > 5.0:
            warnings.append(
                "Area changed by {:.1f}%: {} -> {}".format(
                    pct,
                    old_area,
                    new_area
                )
            )

    old_com = old.get("CenterOfMass")
    new_com = new.get("CenterOfMass")
    if old_com and new_com:
        dist = math.sqrt(sum((new_com[i] - old_com[i]) ** 2 for i in range(3)))
        if dist > 0.5:
            warnings.append(
                "Center of mass moved {:.3f} mm".format(dist)
            )

    old_radius = old.get("Radius")
    new_radius = new.get("Radius")
    if old_radius and new_radius:
        if abs(new_radius - old_radius) > 0.05:
            warnings.append(
                "Radius changed: {} -> {}".format(
                    old_radius,
                    new_radius
                )
            )

    return warnings