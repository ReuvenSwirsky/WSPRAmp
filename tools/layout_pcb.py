from pathlib import Path

import pcbnew


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "WSPRAmp-layout.kicad_pcb"
board = pcbnew.LoadBoard(str(ROOT / "WSPRAmp.kicad_pcb"))
footprints = {footprint.GetReference(): footprint for footprint in board.GetFootprints()}


def point(horizontal, vertical):
    return pcbnew.VECTOR2I(pcbnew.FromMM(horizontal), pcbnew.FromMM(vertical))


def rectangle(parent, layer, left, top, right, bottom, width=0.05):
    shape = pcbnew.PCB_SHAPE(parent)
    shape.SetShape(pcbnew.SHAPE_T_RECT)
    shape.SetLayer(layer)
    shape.SetStart(point(left, top))
    shape.SetEnd(point(right, bottom))
    shape.SetWidth(pcbnew.FromMM(width))
    parent.Add(shape)
    return shape


removed_items = list(board.GetTracks()) + list(board.Zones()) + list(board.GetDrawings())
for item in removed_items:
    board.Remove(item)
ground = board.FindNet("GND")
for footprint in footprints.values():
    for pad in footprint.Pads():
        if pad.GetNetname() == "0":
            pad.SetNet(ground)

placements = {
    "J2": (44, 38, 90),
    "RZ1": (66, 80, 90),
    "C1": (65, 55, 0),
    "U3": (78, 55, 180),
    "R1": (70, 60, -90),
    "RV1": (79, 83, -90),
    "L1": (61, 40, 0),
    "LP1": (77, 49, 180),
    "C2": (82, 65, 90),
    "LS1": (87, 58, 90),
    "C3": (94, 84, 0),
    "R3": (104, 79, 90),
    "C4": (95, 47, 90),
    "L2": (94, 69.24, 90),
    "C5": (103, 68, 90),
    "L3": (111, 54, -90),
    "C6": (119, 51, -90),
    "J1": (127.46, 46, 0),
}
assert set(placements) == set(footprints)
for reference, (horizontal, vertical, angle) in placements.items():
    footprint = footprints[reference]
    footprint.SetOrientationDegrees(angle)
    footprint.SetPosition(point(horizontal, vertical))
    footprint.Value().SetVisible(False)
    footprint.Reference().SetTextAngle(pcbnew.EDA_ANGLE(0, pcbnew.DEGREES_T))
    footprint.Reference().SetTextSize(point(1, 1))
    footprint.Reference().SetTextThickness(pcbnew.FromMM(0.15))

rectangle(board, pcbnew.Edge_Cuts, 40, 35, 130, 95)
header = footprints["J2"]
header_shapes = list(header.GraphicalItems())
for shape in header_shapes:
    if shape.GetLayer() == pcbnew.F_CrtYd:
        header.Remove(shape)
rectangle(header, pcbnew.F_CrtYd, 41, 36, 58, 55)
rectangle(header, pcbnew.F_Fab, 42.58, 38, 55.58, 53, 0.1)
rectangle(board, pcbnew.Dwgs_User, 41, 36, 58, 55, 0.15)
label = pcbnew.PCB_TEXT(board)
label.SetText("GPS 13 x 15 mm\n17 x 19 mm reserved")
label.SetPosition(point(49.5, 48))
label.SetTextSize(point(0.85, 0.85))
label.SetTextThickness(pcbnew.FromMM(0.12))
label.SetLayer(pcbnew.Dwgs_User)
board.Add(label)

for reference, footprint in footprints.items():
    if reference == "J2":
        continue
    bounds = footprint.GetBoundingBox(False, False)
    overlaps_gps = (
        bounds.GetLeft() < pcbnew.FromMM(58)
        and bounds.GetRight() > pcbnew.FromMM(41)
        and bounds.GetTop() < pcbnew.FromMM(55)
        and bounds.GetBottom() > pcbnew.FromMM(36)
    )
    assert not overlaps_gps, f"{reference} intrudes into GPS envelope"

board.BuildConnectivity()
pcbnew.SaveBoard(str(OUTPUT), board)
print(f"Saved {OUTPUT.name}: 90 x 60 mm; GPS envelope 17 x 19 mm clear of other parts")