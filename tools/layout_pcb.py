from pathlib import Path

import pcbnew


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "WSPRAmp-layout.kicad_pcb"
board = pcbnew.LoadBoard(str(ROOT / "WSPRAmp.kicad_pcb"))
footprints = {footprint.GetReference(): footprint for footprint in board.GetFootprints()}

TOROID_FOOTPRINTS = {
    "L2": "FT37-43_Upright_Inductor_P15.24mm",
    "L3": "FT37-43_Upright_Inductor_P15.24mm",
    "LP1": "FT37-43_Upright_Bifilar_Primary",
    "LS1": "FT37-43_Upright_Bifilar_Secondary",
}
replaced_footprints = []
for reference, name in TOROID_FOOTPRINTS.items():
    original = footprints[reference]
    replacement = pcbnew.FootprintLoad(str(ROOT / "LocalModels" / "WSPRAmp.pretty"), name)
    assert replacement is not None, f"Missing local footprint: {name}"
    replacement.SetFPID(pcbnew.LIB_ID("WSPRAmp", name))
    replacement.SetReference(reference)
    replacement.SetValue(original.GetValue())
    replacement.SetPath(original.GetPath())
    replacement.m_Uuid.Clone(original.m_Uuid)
    nets = {pad.GetNumber(): pad.GetNet() for pad in original.Pads()}
    board.Add(replacement)
    for pad in replacement.Pads():
        pad.SetNet(nets[pad.GetNumber()])
    board.Remove(original)
    replaced_footprints.append(original)
    footprints[reference] = replacement


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
    "RZ1": (66, 83, 90),
    "C1": (64, 58, 90),
    "U3": (72, 53, 180),
    "R1": (69, 59, -90),
    "RV1": (86, 88, -90),
    "L1": (61, 88, 0),
    "LP1": (91.24, 46.5, 180),
    "C2": (88, 38, 0),
    "LS1": (76, 53, 0),
    "C3": (99, 73, 90),
    "R3": (86, 75.24, 90),
    "C4": (93, 60, -90),
    "L2": (110.24, 53, 180),
    "C5": (112, 60, -90),
    "L3": (129.24, 53, 180),
    "C6": (131, 60, -90),
    "J1": (138.41, 53, 0),
}
reference_positions = {
    "J2": (49.5, 57.5), "RZ1": (53, 73), "C1": (60, 55.5),
    "U3": (71, 49), "R1": (72.5, 66), "RV1": (86, 97.2),
    "L1": (68.5, 92), "LP1": (83.62, 42.5), "C2": (88, 42.5),
    "LS1": (83.62, 49.75), "C3": (99, 78), "R3": (86, 78.5),
    "C4": (93, 70), "L2": (102.62, 49), "C5": (112, 70),
    "L3": (121.62, 49), "C6": (131, 70), "J1": (137, 46),
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
    footprint.Reference().SetPosition(point(*reference_positions[reference]))

transformer = pcbnew.PCB_GROUP(board)
transformer.SetName("Transformer - LP1 primary and LS1 secondary")
transformer.AddItem(footprints["LP1"])
transformer.AddItem(footprints["LS1"])
board.Add(transformer)

primary_pads = {pad.GetNumber(): pad.GetPosition() for pad in footprints["LP1"].Pads()}
secondary_pads = {pad.GetNumber(): pad.GetPosition() for pad in footprints["LS1"].Pads()}
assert primary_pads["2"].x == secondary_pads["1"].x
assert primary_pads["1"].x == secondary_pads["2"].x
assert secondary_pads["1"].y - primary_pads["2"].y == pcbnew.FromMM(6.5)
assert sum(len(footprints[reference].Models()) for reference in TOROID_FOOTPRINTS) == 3

rectangle(board, pcbnew.Edge_Cuts, 40, 34, 141, 98)
rectangle(board, pcbnew.Dwgs_User, 42.58, 38, 55.58, 53, 0.1)
rectangle(board, pcbnew.Dwgs_User, 41, 36, 58, 55, 0.15)
label = pcbnew.PCB_TEXT(board)
label.SetText("GPS 13 x 15 mm\n17 x 19 mm reserved")
label.SetPosition(point(49.5, 48))
label.SetTextSize(point(0.85, 0.85))
label.SetTextThickness(pcbnew.FromMM(0.12))
label.SetLayer(pcbnew.Dwgs_User)
board.Add(label)

module = footprints["RZ1"]
for shape in module.GraphicalItems():
    if shape.GetLayer() == pcbnew.F_SilkS:
        shape.SetLayer(pcbnew.F_Fab)
rectangle(board, pcbnew.F_SilkS, 40.8, 62.5, 65.7, 82.8, 0.15)

gps_clearance = pcbnew.ZONE(board)
gps_clearance.SetIsRuleArea(True)
gps_clearance.SetLayer(pcbnew.F_Cu)
gps_clearance.SetZoneName("Plug-in GPS body - components only, copper allowed")
gps_clearance.SetDoNotAllowTracks(False)
gps_clearance.SetDoNotAllowVias(False)
gps_clearance.SetDoNotAllowPads(False)
gps_clearance.SetDoNotAllowZoneFills(False)
gps_clearance.SetDoNotAllowFootprints(True)
gps_polygon = gps_clearance.Outline()
gps_polygon.NewOutline()
for horizontal, vertical in [(41, 41), (58, 41), (58, 55), (41, 55)]:
    gps_polygon.Append(pcbnew.FromMM(horizontal), pcbnew.FromMM(vertical))
board.Add(gps_clearance)

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

for index, (reference, footprint) in enumerate(footprints.items()):
    bounds = footprint.GetCourtyard(pcbnew.F_CrtYd).BBox()
    for other_reference, other in list(footprints.items())[index + 1:]:
        other_bounds = other.GetCourtyard(pcbnew.F_CrtYd).BBox()
        overlap = (
            bounds.GetLeft() < other_bounds.GetRight()
            and bounds.GetRight() > other_bounds.GetLeft()
            and bounds.GetTop() < other_bounds.GetBottom()
            and bounds.GetBottom() > other_bounds.GetTop()
        )
        assert not overlap, f"Courtyard overlap: {reference}, {other_reference}"


def get_pad(reference, number):
    return next(pad for pad in footprints[reference].Pads() if pad.GetNumber() == str(number))


def route(start, end, bends=(), width=0.5, layer=pcbnew.F_Cu, end_at=None):
    first = get_pad(*start)
    last = get_pad(*end)
    assert first.GetNetCode() == last.GetNetCode(), (start, end)
    endpoint = last.GetPosition() if end_at is None else point(*end_at)
    vertices = [first.GetPosition(), *(point(*bend) for bend in bends), endpoint]
    for beginning, ending in zip(vertices, vertices[1:]):
        if beginning == ending:
            continue
        track = pcbnew.PCB_TRACK(board)
        track.SetStart(beginning)
        track.SetEnd(ending)
        track.SetWidth(pcbnew.FromMM(width))
        track.SetLayer(layer)
        track.SetNet(first.GetNet())
        board.Add(track)


route(("RZ1", 7), ("C1", 1), [(58.38, 62), (62.38, 58)], width=0.3)
route(("C1", 2), ("U3", 2), [(66, 53), (67.27, 54.27)], width=0.3)
route(("U3", 2), ("R1", 1), [(69, 56)], width=0.3)
route(("U3", 1), ("LS1", 1))
route(("U3", 1), ("LP1", 2), [(72, 50.5)], width=0.5)
route(("LS1", 1), ("R3", 2), [(76, 57), (79, 60)], width=0.5)
route(("LS1", 2), ("L2", 2))
route(("LS1", 2), ("C4", 1), [(93, 53)])
route(("L2", 1), ("L3", 2))
route(("L2", 1), ("C5", 1), [(112, 53)])
route(("L3", 1), ("J1", 1))
route(("L3", 1), ("C6", 1), [(131, 53)])
route(("R3", 1), ("C3", 2), [(91.76, 75.24), (99, 68)], width=0.5)

route(("R1", 2), ("RV1", 2), [(67, 73.7), (67, 92), (69.5, 94.5)], width=0.3)
route(("C3", 1), ("L1", 2), [(99, 78), (95, 82), (83, 82), (77, 88)],
    width=0.6, layer=pcbnew.B_Cu)
route(("LP1", 1), ("C2", 1), [(88, 43.26)], width=0.6)
route(("L1", 2), ("RV1", 1), [(81, 83.24)], width=0.6)
route(("C3", 1), ("LP1", 1), [(102, 70), (102, 51.5), (97, 46.5)],
      width=0.6, layer=pcbnew.B_Cu)
route(("J2", 3), ("RZ1", 2), [(49.08, 57.82), (45.68, 61.22)], width=0.3)
route(("J2", 5), ("RZ1", 3), [(54.16, 55.76), (48.22, 61.7)], width=0.3)
route(("RZ1", 23), ("L1", 1), [(43.14, 85), (58, 85)], width=0.6)


def via_at(horizontal, vertical, net):
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(point(horizontal, vertical))
    via.SetWidth(pcbnew.FromMM(0.8))
    via.SetDrill(pcbnew.FromMM(0.4))
    via.SetViaType(pcbnew.VIATYPE_THROUGH)
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    via.SetNet(net)
    board.Add(via)


def escape(reference, number, horizontal, vertical, layer=pcbnew.F_Cu):
    pad = get_pad(reference, number)
    track = pcbnew.PCB_TRACK(board)
    track.SetStart(pad.GetPosition())
    track.SetEnd(point(horizontal, vertical))
    track.SetWidth(pcbnew.FromMM(0.4))
    track.SetLayer(layer)
    track.SetNet(pad.GetNet())
    board.Add(track)


via_at(48.22, 84, get_pad("RZ1", 21).GetNet())
escape("RZ1", 21, 48.22, 84)
route(("J2", 1), ("RZ1", 21), [(42, 40), (42, 77.78)],
    width=0.4, layer=pcbnew.B_Cu, end_at=(48.22, 84))

ground_vias = [
    (45.68, 83), (91, 78.8), (69.46, 50.5),
    (90.5, 64), (95.5, 64), (109.5, 64), (114.5, 64),
    (128.5, 64), (133.5, 64), (134.5, 48.75), (134.5, 57.25),
    (139, 46), (139, 60), (79, 47), (95.5, 42), (104, 47),
    (117, 47), (130, 47), (57, 39),
]
for horizontal, vertical in ground_vias:
    via_at(horizontal, vertical, ground)
escape("RZ1", 22, 45.68, 83)
escape("RV1", 3, 91, 78.8)
escape("U3", 3, 69.46, 50.5)

for reference in ("U3", "C4", "C5", "C6", "J1"):
    for pad in footprints[reference].Pads():
        if pad.GetNetname() == "GND":
            pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)

for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
    zone = pcbnew.ZONE(board)
    zone.SetLayer(layer)
    zone.SetNet(ground)
    zone.SetLocalClearance(pcbnew.FromMM(0.25))
    zone.SetMinThickness(pcbnew.FromMM(0.2))
    zone.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    zone.SetThermalReliefGap(pcbnew.FromMM(0.3))
    zone.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.3))
    polygon = zone.Outline()
    polygon.NewOutline()
    for horizontal, vertical in [(40.5, 34.5), (140.5, 34.5), (140.5, 97.5), (40.5, 97.5)]:
        polygon.Append(pcbnew.FromMM(horizontal), pcbnew.FromMM(vertical))
    board.Add(zone)

board.BuildConnectivity()
requested_nets = {track.m_Uuid.AsString(): track.GetNetCode() for track in board.GetTracks()}
filler = pcbnew.ZONE_FILLER(board)
filler.Fill(board.Zones())
for track in board.GetTracks():
    assert track.GetNetCode() == requested_nets[track.m_Uuid.AsString()], "Fill reassigned a track/via net"
pcbnew.SaveBoard(str(OUTPUT), board)
print(f"Saved {OUTPUT.name}: 101 x 64 mm; courtyards clear; tracks and ground pours added")