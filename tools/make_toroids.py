import math
from pathlib import Path

import pcbnew


ROOT = Path(__file__).resolve().parent.parent
LIBRARY = ROOT / "LocalModels" / "WSPRAmp.pretty"
MODELS = ROOT / "LocalModels" / "3d_model"
SOURCE = "https://www.amidoncorp.com/ft-37-43/"
OUTER_DIAMETER = 0.375 * 25.4
INNER_DIAMETER = 0.187 * 25.4
THICKNESS = 0.125 * 25.4
PITCH = 15.24


def point(horizontal, vertical):
    return pcbnew.VECTOR2I(pcbnew.FromMM(horizontal), pcbnew.FromMM(vertical))


def rectangle(footprint, layer, left, top, right, bottom, width):
    shape = pcbnew.PCB_SHAPE(footprint)
    shape.SetShape(pcbnew.SHAPE_T_RECT)
    shape.SetLayer(layer)
    shape.SetStart(point(left, top))
    shape.SetEnd(point(right, bottom))
    shape.SetWidth(pcbnew.FromMM(width))
    footprint.Add(shape)


def make_footprint(name, role):
    footprint = pcbnew.FOOTPRINT(None)
    footprint.SetFPID(pcbnew.LIB_ID("WSPRAmp", name))
    footprint.SetReference("REF**")
    footprint.SetValue(name)
    footprint.SetAttributes(pcbnew.FP_THROUGH_HOLE)
    footprint.SetLibDescription(
        f"FT37-43 upright {role}; bare core OD 9.525 ID 4.7498 thickness 3.175 mm; "
        f"wound envelope 11.5 x 5.0 mm; 15.24 mm hand-formed lead pitch, 0.8 mm drills. {SOURCE}. "
        "3D model is bare core only. Transformer Primary/Secondary footprints form ONE assembly, "
        "opposed at 6.5 mm row spacing; primary owns shared body and model. Verify winding polarity."
    )
    footprint.Reference().SetPosition(point(PITCH / 2, -4))
    footprint.Reference().SetTextSize(point(1, 1))
    footprint.Reference().SetTextThickness(pcbnew.FromMM(0.15))
    footprint.Value().SetVisible(False)
    for number, horizontal in [("1", 0), ("2", PITCH)]:
        pad = pcbnew.PAD(footprint)
        pad.SetNumber(number)
        pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
        pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
        pad.SetPosition(point(horizontal, 0))
        pad.SetSize(point(2, 2))
        pad.SetDrillSize(point(0.8, 0.8))
        pad.SetLayerSet(pcbnew.LSET.AllCuMask())
        layers = pad.GetLayerSet()
        layers.AddLayer(pcbnew.F_Mask)
        layers.AddLayer(pcbnew.B_Mask)
        pad.SetLayerSet(layers)
        footprint.Add(pad)
    if role == "inductor":
        rectangle(footprint, pcbnew.F_CrtYd, -1.5, -3, 16.74, 3, 0.05)
    else:
        rectangle(footprint, pcbnew.F_CrtYd, -1.5, -3.2, 16.74, 1.5, 0.05)
    if role != "secondary":
        center_y = -3.25 if role == "primary" else 0
        rectangle(footprint, pcbnew.F_Fab, 1.87, center_y - 2.5, 13.37, center_y + 2.5, 0.1)
        rectangle(footprint, pcbnew.F_SilkS, 1.75, center_y - 2.62, 13.49, center_y + 2.62, 0.12)
        model = pcbnew.FP_3DMODEL()
        model.m_Filename = "${KIPRJMOD}/LocalModels/3d_model/FT37-43_BareCore_Upright.wrl"
        model.m_Offset.x = PITCH / 2
        model.m_Offset.y = -center_y
        footprint.Add3DModel(model)
    writer = pcbnew.PCB_IO_MGR.FindPlugin(pcbnew.PCB_IO_MGR.KICAD_SEXP)
    writer.FootprintSave(str(LIBRARY), footprint)
    return footprint


def make_core_model():
    segments = 96
    vertices = []
    for radius, depth in [
        (OUTER_DIAMETER / 2, -THICKNESS / 2),
        (OUTER_DIAMETER / 2, THICKNESS / 2),
        (INNER_DIAMETER / 2, -THICKNESS / 2),
        (INNER_DIAMETER / 2, THICKNESS / 2),
    ]:
        for index in range(segments):
            angle = 2 * math.pi * index / segments
            vertices.append((radius * math.cos(angle), depth, 1 + OUTER_DIAMETER / 2 + radius * math.sin(angle)))
    faces = []
    for index in range(segments):
        following = (index + 1) % segments
        faces.extend([
            (index, following, segments + following, segments + index),
            (2 * segments + index, 3 * segments + index, 3 * segments + following, 2 * segments + following),
            (index, 2 * segments + index, 2 * segments + following, following),
            (segments + index, segments + following, 3 * segments + following, 3 * segments + index),
        ])
    coordinates = ",\n".join(" ".join(f"{value / 2.54:.8f}" for value in vertex) for vertex in vertices)
    indices = ",\n".join(", ".join(str(index) for index in face) + ", -1" for face in faces)
    content = (
        '#VRML V2.0 utf8\n'
        f'WorldInfo {{ title "FT37-43 bare core upright" info ["{SOURCE}", '
        '"OD 9.525 ID 4.7498 thickness 3.175 mm; 1 mm standoff; no winding geometry", '
        '"KiCad VRML unit = 2.54 mm"] }\n'
        'Shape { appearance Appearance { material Material { diffuseColor 0.12 0.12 0.13 '
        'specularColor 0.25 0.25 0.25 shininess 0.25 } }\n'
        'geometry IndexedFaceSet { solid FALSE creaseAngle 0.4\n'
        f'coord Coordinate {{ point [\n{coordinates}\n] }}\ncoordIndex [\n{indices}\n] }} }}\n'
    )
    (MODELS / "FT37-43_BareCore_Upright.wrl").write_text(content, encoding="ascii")
    assert abs(max(vertex[0] for vertex in vertices) - min(vertex[0] for vertex in vertices) - OUTER_DIAMETER) < 1e-6
    assert abs(max(vertex[1] for vertex in vertices) - min(vertex[1] for vertex in vertices) - THICKNESS) < 1e-6
    assert abs(min(vertex[2] for vertex in vertices) - 1) < 1e-6


def main():
    LIBRARY.mkdir(parents=True, exist_ok=True)
    MODELS.mkdir(parents=True, exist_ok=True)
    make_core_model()
    for name, role in [
        ("FT37-43_Upright_Inductor_P15.24mm", "inductor"),
        ("FT37-43_Upright_Bifilar_Primary", "primary"),
        ("FT37-43_Upright_Bifilar_Secondary", "secondary"),
    ]:
        make_footprint(name, role)
        loaded = pcbnew.FootprintLoad(str(LIBRARY), name)
        assert loaded is not None and loaded.GetPadCount() == 2
        assert len(loaded.Models()) == (0 if role == "secondary" else 1)
    print("Validated three footprints and dimensioned FT37-43 upright bare-core model")


if __name__ == "__main__":
    main()