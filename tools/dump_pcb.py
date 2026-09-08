import sys
import pcbnew

board = pcbnew.LoadBoard(sys.argv[1])
bb = board.GetBoardEdgesBoundingBox()
print("Board edges bbox (mm):", bb.GetLeft()/1e6, bb.GetTop()/1e6, bb.GetRight()/1e6, bb.GetBottom()/1e6)
print("Layers:", board.GetCopperLayerCount())
print("\n=== Footprints ===")
for fp in board.GetFootprints():
    p = fp.GetPosition()
    print(f"{fp.GetReference():6s} {fp.GetValue():24s} {fp.GetFPID().GetLibItemName()!s:40s} "
          f"pos=({p.x/1e6:.2f},{p.y/1e6:.2f}) rot={fp.GetOrientationDegrees():.0f} "
          f"layer={board.GetLayerName(fp.GetLayer())} pads={fp.GetPadCount()}")
    for pad in fp.Pads():
        pp = pad.GetPosition()
        print(f"        pad {pad.GetNumber():4s} net={pad.GetNetname():20s} at ({pp.x/1e6:.2f},{pp.y/1e6:.2f}) sz=({pad.GetSize().x/1e6:.2f},{pad.GetSize().y/1e6:.2f}) smd={pad.GetAttribute()==pcbnew.PAD_ATTRIB_SMD}")

print("\n=== Nets ===")
for code, net in board.GetNetsByNetcode().items():
    if code == 0:
        continue
    pads = [f"{p.GetParentFootprint().GetReference()}.{p.GetNumber()}" for p in board.GetPads() if p.GetNetCode() == code]
    print(f"{code:3d} {net.GetNetname():24s} {pads}")

print("\n=== Tracks/Vias ===", len(board.GetTracks()))
for t in board.GetTracks():
    s, e = t.GetStart(), t.GetEnd()
    print(f"  {t.GetClass():8s} net={t.GetNetname():18s} L={board.GetLayerName(t.GetLayer()):5s} ({s.x/1e6:.2f},{s.y/1e6:.2f})->({e.x/1e6:.2f},{e.y/1e6:.2f}) w={t.GetWidth()/1e6:.2f}")
print("=== Zones ===", len(board.Zones()))
for z in board.Zones():
    print("  zone net", z.GetNetname(), "layer", board.GetLayerName(z.GetFirstLayer()))
print("=== Drawings ===")
for d in board.GetDrawings():
    extra = ""
    if hasattr(d, "GetShapeStr"):
        s, e = d.GetStart(), d.GetEnd()
        extra = f"{d.GetShapeStr()} ({s.x/1e6:.2f},{s.y/1e6:.2f})->({e.x/1e6:.2f},{e.y/1e6:.2f})"
    print("  ", d.GetClass(), board.GetLayerName(d.GetLayer()), extra)
ds = board.GetDesignSettings()
print("\nDefault track width:", ds.GetCurrentTrackWidth()/1e6, " clearance:", ds.GetDefault().GetClearance()/1e6)
print("Netclasses:", [str(n) for n in ds.m_NetSettings.GetNetclasses().keys()] if hasattr(ds.m_NetSettings, "GetNetclasses") else "n/a")
