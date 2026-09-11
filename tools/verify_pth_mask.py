import hashlib
import json
import math
import subprocess
from pathlib import Path

from gerbonara import ExcellonFile, GerberFile
from gerbonara.apertures import ApertureMacroInstance, CircleAperture, RectangleAperture
from gerbonara.graphic_objects import Flash
from gerbonara.utils import MM
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent.parent
BOARD = ROOT / "WSPRAmp-layout.kicad_pcb"
OUTPUT = ROOT / "pcbway_production/W819020AS1M2-mask-revised"
INSPECTION = ROOT / "tools/copper-inspection"
BASELINE = INSPECTION / "mask-baseline-gerbers"
KICAD_PYTHON = "C:/Program Files/KiCad/10.0/bin/python.exe"
TOLERANCE = 0.000002
NATIVE_FACTS = """
import json
import sys
import pcbnew
board = pcbnew.LoadBoard(sys.argv[1])
pads = []
for footprint in board.GetFootprints():
    for pad in footprint.Pads():
        if pad.GetAttribute() != pcbnew.PAD_ATTRIB_PTH:
            continue
        assert pad.GetShape() in (pcbnew.PAD_SHAPE_CIRCLE, pcbnew.PAD_SHAPE_RECT)
        assert pad.GetSize().x == pad.GetSize().y
        assert pad.GetDrillSize().x == pad.GetDrillSize().y
        assert pad.GetOffset().x == pad.GetOffset().y == 0
        assert pad.IsOnLayer(pcbnew.F_Mask) and pad.IsOnLayer(pcbnew.B_Mask)
        assert pad.GetSolderMaskExpansion(pcbnew.F_Mask) == pcbnew.FromMM(0.05)
        assert pad.GetSolderMaskExpansion(pcbnew.B_Mask) == pcbnew.FromMM(0.05)
        pads.append(dict(reference=footprint.GetReference(), number=pad.GetNumber(),
            x=pcbnew.ToMM(pad.GetPosition().x), y=-pcbnew.ToMM(pad.GetPosition().y),
            size=pcbnew.ToMM(pad.GetSize().x), drill=pcbnew.ToMM(pad.GetDrillSize().x),
            shape='circle' if pad.GetShape() == pcbnew.PAD_SHAPE_CIRCLE else 'square'))
print(json.dumps(pads))
"""


def fabrication_data(path):
    return "\n".join(
        line for line in path.read_text(encoding="utf-8").splitlines()
        if not any(marker in line for marker in (
            "TF.CreationDate", "TF.ProjectId", "Created by KiCad", "; DRILL file KiCad"
        ))
    )


def rounded_box(flash):
    assert isinstance(flash, Flash) and flash.polarity_dark
    bounds = flash.bounding_box(unit=MM)
    width = bounds[1][0] - bounds[0][0]
    height = bounds[1][1] - bounds[0][1]
    if isinstance(flash.aperture, CircleAperture):
        radius = flash.aperture.diameter / 2
    elif isinstance(flash.aperture, RectangleAperture):
        radius = 0
    else:
        assert isinstance(flash.aperture, ApertureMacroInstance)
        assert flash.aperture.macro.name == "RoundRect"
        radius = flash.aperture.parameters[0]
        assert math.isclose(radius, 0.05, abs_tol=TOLERANCE)
    return width / 2 - radius, height / 2 - radius, radius


def mask_gap(first, second):
    first_width, first_height, first_radius = rounded_box(first)
    second_width, second_height, second_radius = rounded_box(second)
    horizontal = max(abs(first.x - second.x) - first_width - second_width, 0)
    vertical = max(abs(first.y - second.y) - first_height - second_height, 0)
    return math.hypot(horizontal, vertical) - first_radius - second_radius


def render_mask(mask, drills, side):
    scale = 12
    image = Image.new("RGB", (1260, 870), "#183b30")
    drawing = ImageDraw.Draw(image)

    def pixel(horizontal, vertical):
        return ((horizontal - 39) * scale, (-vertical - 32) * scale + 25)

    drawing.text((15, 10), f"{side} mask: openings gold, drilled holes black (top-view coordinates)", fill="white")
    for flash in mask.objects:
        lower, upper = flash.bounding_box(unit=MM)
        bounds = (*pixel(lower[0], upper[1]), *pixel(upper[0], lower[1]))
        radius = rounded_box(flash)[2]
        drawing.rounded_rectangle(bounds, radius=radius * scale, fill="#efc85d")
    for drill in drills.objects:
        lower, upper = drill.bounding_box(unit=MM)
        drawing.ellipse((*pixel(lower[0], upper[1]), *pixel(upper[0], lower[1])), fill="#080b09")
    image.save(INSPECTION / f"mask-{side.lower()}-verified.png")
    (INSPECTION / f"mask-{side.lower()}-verified.svg").write_text(str(mask.to_svg()), encoding="utf-8")


def main():
    pads = json.loads(subprocess.check_output(
        [KICAD_PYTHON, "-c", NATIVE_FACTS, str(BOARD)], text=True
    ))
    assert len(pads) == 60
    unchanged = []
    for suffix in ("F_Cu.gbr", "B_Cu.gbr", "F_Paste.gbr", "B_Paste.gbr",
                   "F_Silkscreen.gbr", "B_Silkscreen.gbr", "Edge_Cuts.gbr", "PTH.drl", "NPTH.drl"):
        assert fabrication_data(BASELINE / f"mask-before-{suffix}") == fabrication_data(
            OUTPUT / f"WSPRAmp-layout-{suffix}"
        ), f"Non-mask fabrication data changed: {suffix}"
        unchanged.append(suffix)
    drills = ExcellonFile.open(OUTPUT / "WSPRAmp-layout-PTH.drl")
    for pad in pads:
        matches = [drill for drill in drills.objects
                   if math.isclose(drill.x, pad["x"], abs_tol=TOLERANCE)
                   and math.isclose(drill.y, pad["y"], abs_tol=TOLERANCE)
                   and math.isclose(drill.aperture.diameter, pad["drill"], abs_tol=TOLERANCE)]
        assert len(matches) == 1, f"Missing/mismatched drill for {pad}"
    checks = {}
    for side, expected_count in (("F", 63), ("B", 62)):
        mask = GerberFile.open(OUTPUT / f"WSPRAmp-layout-{side}_Mask.gbr")
        assert len(mask.objects) == expected_count
        matched = set()
        for pad in pads:
            matches = [(index, flash) for index, flash in enumerate(mask.objects)
                       if isinstance(flash, Flash)
                       and flash.attrs.get(".C") == (pad["reference"],)
                       and math.isclose(flash.x, pad["x"], abs_tol=TOLERANCE)
                       and math.isclose(flash.y, pad["y"], abs_tol=TOLERANCE)]
            assert len(matches) == 1, f"Wrong {side} aperture count for {pad}"
            index, flash = matches[0]
            assert index not in matched
            matched.add(index)
            assert flash.polarity_dark
            lower, upper = flash.bounding_box(unit=MM)
            for extent in (upper[0] - lower[0], upper[1] - lower[1]):
                assert math.isclose(extent, pad["size"] + 0.1, abs_tol=TOLERANCE), pad
            if pad["shape"] == "circle":
                assert isinstance(flash.aperture, CircleAperture), pad
            else:
                assert isinstance(flash.aperture, ApertureMacroInstance), pad
                assert math.isclose(rounded_box(flash)[2], 0.05, abs_tol=TOLERANCE), pad
        original = GerberFile.open(BASELINE / f"mask-before-{side}_Mask.gbr")
        remaining = [flash for index, flash in enumerate(mask.objects) if index not in matched]
        assert all(flash.attrs.get(".C") == ("J1",) for flash in remaining)
        assert [list(flash.to_primitives(unit=MM)) for flash in remaining] == [
            list(flash.to_primitives(unit=MM)) for flash in original.objects
        ], "Existing J1 mask openings changed"
        gaps = [(mask_gap(first, second), first.attrs.get(".C"), second.attrs.get(".C"))
                for index, first in enumerate(mask.objects) for second in mask.objects[index + 1:]]
        smallest = min(gaps, key=lambda item: item[0])
        assert smallest[0] >= 0.1 - TOLERANCE, f"Mask web below 0.1 mm: {smallest}"
        checks[side] = dict(total_openings=len(mask.objects), pth_openings=len(matched),
                            minimum_mask_web_mm=smallest[0], closest_components=smallest[1:])
        render_mask(mask, drills, side)
    for report_name in ("mask-after-drc.json", "mask-refilled-drc.json"):
        drc = json.loads((INSPECTION / report_name).read_text(encoding="utf-8"))
        assert not drc["unconnected_items"]
        assert all(item["severity"] == "warning" and item["type"] == "lib_footprint_mismatch"
                   for item in drc["violations"]), report_name
    report = dict(board=str(BOARD), board_sha256=hashlib.sha256(BOARD.read_bytes()).hexdigest(),
                  pth_pads=len(pads), mask_clearance_mm=0.05, masks=checks,
                  unchanged_fabrication_files=unchanged, plated_drill_hits=len(drills.objects),
                  drc_errors=0, refilled_drc_errors=0, unconnected_items=0,
                  library_mismatch_warnings=len(drc["violations"]),
                  files={path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                         for path in sorted(OUTPUT.iterdir()) if path.suffix in (".gbr", ".drl", ".gbrjob")})
    (INSPECTION / "mask-verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()