import argparse
from pathlib import Path

import pcbnew

from make_trimmer import box, shape


ROOT = Path(__file__).resolve().parent.parent
NAME = "RP2040-Zero_Headers_P2.54mm"
LIBRARY = ROOT / "LocalModels" / "WSPRAmp.pretty"
MODULE_MODEL = "${KIPRJMOD}/LocalModels/3d_model/RP2040_Zero.stp"
HEADER_MODEL = "${KIPRJMOD}/LocalModels/3d_model/RP2040_Zero_Headers_Preview.wrl"
HEADER_HEIGHT = 4


def point(horizontal, vertical):
    return pcbnew.VECTOR2I(pcbnew.FromMM(horizontal), pcbnew.FromMM(vertical))


def convert(footprint):
    position = footprint.GetPosition()
    angle = footprint.GetOrientationDegrees()
    footprint.SetOrientationDegrees(0)
    footprint.SetPosition(point(0, 0))
    footprint.SetFPID(pcbnew.LIB_ID("WSPRAmp", NAME))
    footprint.SetAttributes(pcbnew.FP_THROUGH_HOLE)
    footprint.SetLibDescription(
        "Waveshare RP2040-Zero header carrier: 23 perimeter pins, 2.54 mm pitch, "
        "15.24 mm side-row spacing, 1.0 mm drills, 1.8 mm pads. "
        f"18 x 23.5 mm module. Preview assumes {HEADER_HEIGHT} mm header height; verify underside clearance. "
        "https://www.waveshare.com/wiki/RP2040-Zero"
    )
    for pad in footprint.Pads():
        number = int(pad.GetNumber())
        if 10 <= number <= 14:
            pad.SetPosition(point((16 - number) * 2.54, -2.54))
        pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
        pad.SetShape(pcbnew.PAD_SHAPE_RECT if number == 1 else pcbnew.PAD_SHAPE_CIRCLE)
        pad.SetOffset(point(0, 0))
        pad.SetSize(point(1.8, 1.8))
        pad.SetDrillSize(point(1, 1))
        layers = pcbnew.LSET.AllCuMask()
        layers.AddLayer(pcbnew.F_Mask)
        layers.AddLayer(pcbnew.B_Mask)
        pad.SetLayerSet(layers)
    footprint.Models().clear()
    model = pcbnew.FP_3DMODEL()
    model.m_Filename = MODULE_MODEL
    model.m_Offset.x = 1.25
    model.m_Offset.y = 0.875
    model.m_Offset.z = HEADER_HEIGHT + 1
    footprint.Add3DModel(model)
    headers = pcbnew.FP_3DMODEL()
    headers.m_Filename = HEADER_MODEL
    footprint.Add3DModel(headers)
    footprint.SetOrientationDegrees(angle)
    footprint.SetPosition(position)


def validate(footprint):
    assert footprint.GetPadCount() == 23
    assert len(footprint.Models()) == 2
    for pad in footprint.Pads():
        assert pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH
        assert pad.GetDrillSize() == point(1, 1)
        assert pad.GetSize() == point(1.8, 1.8)
        assert pad.GetOffset() == point(0, 0)
        assert not pad.IsOnLayer(pcbnew.F_Paste)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--update-board", action="store_true")
    args = parser.parse_args()
    footprint = pcbnew.FootprintLoad(str(ROOT / "LocalModels" / "rp2040-zero.pretty"), "RP2040-Zero")
    assert footprint is not None
    convert(footprint)
    validate(footprint)
    pads = {pad.GetNumber(): pad.GetPosition() for pad in footprint.Pads()}
    assert pads["1"].x - pads["23"].x == pcbnew.FromMM(15.24)
    assert all(pads[str(number)].y == pcbnew.FromMM(-2.54) for number in range(9, 16))
    pcbnew.PCB_IO_MGR.FindPlugin(pcbnew.PCB_IO_MGR.KICAD_SEXP).FootprintSave(str(LIBRARY), footprint)
    meshes = []
    for center, size in [
        ((2.54, 12.7, HEADER_HEIGHT / 2), (2.5, 22.86, HEADER_HEIGHT)),
        ((17.78, 12.7, HEADER_HEIGHT / 2), (2.5, 22.86, HEADER_HEIGHT)),
        ((10.16, 2.54, HEADER_HEIGHT / 2), (12.7, 2.5, HEADER_HEIGHT)),
    ]:
        meshes.append(shape(box(center, size), (0.08, 0.08, 0.09)))
    for position in pads.values():
        center = (pcbnew.ToMM(position.x), -pcbnew.ToMM(position.y), (HEADER_HEIGHT - 1) / 2)
        meshes.append(shape(box(center, (0.64, 0.64, HEADER_HEIGHT + 5)), (0.72, 0.65, 0.37)))
    (ROOT / "LocalModels" / "3d_model" / "RP2040_Zero_Headers_Preview.wrl").write_text(
        '#VRML V2.0 utf8\nWorldInfo { title "RP2040-Zero headers" '
        f'info ["Illustrative {HEADER_HEIGHT}mm headers; verify underside clearance."] }}\n'
        + "".join(meshes), encoding="ascii"
    )
    if args.update_board:
        path = ROOT / "WSPRAmp-layout.kicad_pcb"
        board = pcbnew.LoadBoard(str(path))
        module = next(item for item in board.GetFootprints() if item.GetReference() == "RZ1")
        nets = {pad.GetNumber(): pad.GetNetname() for pad in module.Pads()}
        other_pads = {pad.m_Uuid.AsString(): (pad.GetPosition().x, pad.GetPosition().y,
                     pad.GetSize().x, pad.GetSize().y, pad.GetDrillSize().x, pad.GetDrillSize().y,
                     pad.GetNetname()) for item in board.GetFootprints() if item != module for pad in item.Pads()}
        convert(module)
        validate(module)
        assert nets == {pad.GetNumber(): pad.GetNetname() for pad in module.Pads()}
        assert other_pads == {pad.m_Uuid.AsString(): (pad.GetPosition().x, pad.GetPosition().y,
                              pad.GetSize().x, pad.GetSize().y, pad.GetDrillSize().x, pad.GetDrillSize().y,
                              pad.GetNetname()) for item in board.GetFootprints() if item != module for pad in item.Pads()}
        pcbnew.SaveBoard(str(path), board)
    print("Validated RP2040-Zero: 23 plated 1mm holes, 2.54mm pitch, 15.24mm row spacing; two preview models")


if __name__ == "__main__":
    main()