import sys
import pcbnew

board = pcbnew.LoadBoard(sys.argv[1])
for fp in board.GetFootprints():
    # normalise to rotation 0 at origin for geometry study
    fp.SetOrientationDegrees(0)
    fp.SetPosition(pcbnew.VECTOR2I(0, 0))
    bb = fp.GetBoundingBox(False, False)  # no text, no invisible
    cy = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
    print(f"{fp.GetReference():5s} {fp.GetFPID().GetLibItemName()!s}")
    print(f"      body bbox x[{bb.GetLeft()/1e6:.2f},{bb.GetRight()/1e6:.2f}] y[{bb.GetTop()/1e6:.2f},{bb.GetBottom()/1e6:.2f}]"
          f"  courtyard x[{cy.GetLeft()/1e6:.2f},{cy.GetRight()/1e6:.2f}] y[{cy.GetTop()/1e6:.2f},{cy.GetBottom()/1e6:.2f}]")
    for pad in fp.Pads():
        p = pad.GetPosition()
        print(f"      pad {pad.GetNumber():3s} ({p.x/1e6:.2f},{p.y/1e6:.2f}) drill={pad.GetDrillSize().x/1e6:.2f}")
    for d in fp.GraphicalItems():
        if board.GetLayerName(d.GetLayer()) in ("F.Fab", "Edge.Cuts") and hasattr(d, "GetShapeStr"):
            s, e = d.GetStart(), d.GetEnd()
            print(f"      {board.GetLayerName(d.GetLayer())} {d.GetShapeStr()} ({s.x/1e6:.2f},{s.y/1e6:.2f})->({e.x/1e6:.2f},{e.y/1e6:.2f})")
