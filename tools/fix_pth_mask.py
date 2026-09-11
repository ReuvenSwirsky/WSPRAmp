import argparse
import re
import shutil
import tempfile
from pathlib import Path

import pcbnew


MASK_CLEARANCE_MM = 0.05


def restore_pth_mask(board):
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
                layers = pad.GetLayerSet()
                layers.AddLayer(pcbnew.F_Mask)
                layers.AddLayer(pcbnew.B_Mask)
                pad.SetLayerSet(layers)
                pad.SetLocalSolderMaskMargin(pcbnew.FromMM(MASK_CLEARANCE_MM))


def validate_pth_mask(board):
    count = 0
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            if pad.GetAttribute() != pcbnew.PAD_ATTRIB_PTH:
                continue
            identity = f"{footprint.GetReference()}.{pad.GetNumber()}"
            assert pad.IsOnLayer(pcbnew.F_Mask), f"{identity}: missing front mask"
            assert pad.IsOnLayer(pcbnew.B_Mask), f"{identity}: missing back mask"
            for layer in (pcbnew.F_Mask, pcbnew.B_Mask):
                assert pad.GetSolderMaskExpansion(layer) == pcbnew.FromMM(MASK_CLEARANCE_MM), identity
            count += 1
    assert count, "No PTH pads found"
    return count


def without_mask_settings(text):
    text = text.replace(' "*.Mask"', '').replace(' "F.Mask"', '').replace(' "B.Mask"', '')
    return re.sub(r'^\s*\(solder_mask_margin 0\.05\)\n', '', text, flags=re.MULTILINE)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board", type=Path)
    parser.add_argument("--check-only", action="store_true")
    arguments = parser.parse_args()
    board = pcbnew.LoadBoard(str(arguments.board.resolve()))
    if not arguments.check_only:
        with tempfile.TemporaryDirectory() as directory:
            before = Path(directory) / "before.kicad_pcb"
            after = Path(directory) / "after.kicad_pcb"
            pcbnew.SaveBoard(str(before), board)
            restore_pth_mask(board)
            pcbnew.SaveBoard(str(after), board)
            assert without_mask_settings(before.read_text(encoding="utf-8")) == without_mask_settings(
                after.read_text(encoding="utf-8")
            ), "Refusing to save: non-mask board data changed"
            validate_pth_mask(pcbnew.LoadBoard(str(after)))
            shutil.copyfile(after, arguments.board)
        print("Verified: serialized board data unchanged except mask layers/clearance")
    count = validate_pth_mask(pcbnew.LoadBoard(str(arguments.board.resolve())))
    print(f"PASS: {count} PTH pads have both mask openings and {MASK_CLEARANCE_MM} mm clearance")


if __name__ == "__main__":
    main()