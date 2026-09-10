import math
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "LocalModels" / "3d_model" / "Trimmer_Horizontal_Triangle_P5_H5_Preview.wrl"
PIN_CENTERS = ((0, 0), (5, -2.5), (0, -5))
BLUE = (0.025, 0.20, 0.48)
DIAL = (0.86, 0.87, 0.80)
METAL = (0.65, 0.67, 0.69)
SLOT = (0.16, 0.17, 0.15)


def prism(outline, bottom, top):
    count = len(outline)
    vertices = [(horizontal, vertical, height)
                for height in (bottom, top) for horizontal, vertical in outline]
    faces = [tuple(reversed(range(count))), tuple(range(count, 2 * count))]
    faces.extend((index, (index + 1) % count, (index + 1) % count + count, index + count)
                 for index in range(count))
    return vertices, faces


def box(center, size):
    horizontal, vertical, height = center
    width, depth, thickness = size
    return prism([
        (horizontal - width / 2, vertical - depth / 2),
        (horizontal + width / 2, vertical - depth / 2),
        (horizontal + width / 2, vertical + depth / 2),
        (horizontal - width / 2, vertical + depth / 2),
    ], height - thickness / 2, height + thickness / 2)


def disk(center, radius, thickness):
    horizontal, vertical, height = center
    outline = [(horizontal + radius * math.cos(index * math.tau / 64),
                vertical + radius * math.sin(index * math.tau / 64))
               for index in range(64)]
    return prism(outline, height - thickness / 2, height + thickness / 2)


def shape(mesh, color):
    vertices, faces = mesh
    assert all(math.isfinite(value) for vertex in vertices for value in vertex)
    assert all(0 <= index < len(vertices) for face in faces for index in face)
    coordinates = ",\n".join(" ".join(f"{value / 2.54:.8f}" for value in vertex)
                              for vertex in vertices)
    indices = ",\n".join(" ".join(str(index) for index in face) + " -1" for face in faces)
    diffuse = " ".join(str(value) for value in color)
    shine = 0.8 if color == METAL else 0.2
    return (
        "Shape { appearance Appearance { material Material { "
        f"diffuseColor {diffuse} specularColor {shine} {shine} {shine} shininess {shine} "
        "} } geometry IndexedFaceSet { solid FALSE creaseAngle 0.4\n"
        f"coord Coordinate {{ point [\n{coordinates}\n] }}\n"
        f"coordIndex [\n{indices}\n] }} }}\n"
    )


def main():
    parts = [
        (prism([(-1, -6), (5.2, -6), (6, -5.2), (6, 0.2), (5.2, 1), (-1, 1)],
               0.8, 1.9), BLUE),
        (disk((2.5, -2.5, 0.68), 1.8, 0.24), METAL),
        (disk((2.4, -2.5, 2.45), 3.05, 1.1), DIAL),
        (box((2.4, -2.5, 3.012), (0.52, 4.5, 0.024)), SLOT),
        (box((2.4, -2.5, 3.027), (2.2, 0.48, 0.024)), SLOT),
        (box((2.4, -2.5, 3.043), (0.24, 1.7, 0.016)), METAL),
    ]
    for horizontal, vertical in PIN_CENTERS:
        lead = box((horizontal, vertical, -0.7), (0.45, 0.55, 3.8))
        vertices, _ = lead
        assert abs(sum(vertex[0] for vertex in vertices) / len(vertices) - horizontal) < 1e-9
        assert abs(sum(vertex[1] for vertex in vertices) / len(vertices) - vertical) < 1e-9
        parts.append((lead, METAL))
    for horizontal, vertical in ((-0.5, 0), (-0.5, -5), (5.35, -2.5)):
        parts.append((box((horizontal, vertical, 1.94), (1.05, 0.65, 0.28)), METAL))
    for horizontal, vertical in ((-0.75, 0), (-0.75, -5), (5.75, -2.5)):
        parts.append((box((horizontal, vertical, 1.1), (0.22, 0.65, 1.5)), METAL))
    assert PIN_CENTERS[0][0] == PIN_CENTERS[2][0]
    assert abs(PIN_CENTERS[0][1] - PIN_CENTERS[2][1]) == 5
    assert PIN_CENTERS[1] == (5, (PIN_CENTERS[0][1] + PIN_CENTERS[2][1]) / 2)
    header = (
        '#VRML V2.0 utf8\n'
        'WorldInfo { title "Horizontal triangular-pin trimmer preview" info [\n'
        '"Generic photo-based preview; not a manufacturer model or clearance reference.",\n'
        '"Confirmed footprint pin centers in mm: (0,0), (5,2.5), (0,5).",\n'
        '"Approximate body 7 x 7 mm, top 3.1 mm above PCB; lead width 0.45 mm.",\n'
        '"KiCad VRML coordinates = mm / 2.54; Y inverted from footprint coordinates."\n'
        '] }\n'
    )
    OUTPUT.write_text(header + "".join(shape(mesh, color) for mesh, color in parts), encoding="ascii")
    print(f"Created {OUTPUT.name}: {len(parts)} meshes; verified 5 x 5 mm triangular lead centers")


if __name__ == "__main__":
    main()