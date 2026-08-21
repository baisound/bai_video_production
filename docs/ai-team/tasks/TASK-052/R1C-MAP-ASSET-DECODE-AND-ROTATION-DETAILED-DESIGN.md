# TASK-052 R1C — Map Asset Decode and Rotation Detailed Design

Status: `DESIGN_BOUND`
Profile: `DEV-3 HIGH ASSURANCE`
Defects: `DBD-HA-052-001`, `DBD-HA-052-002`

## Boundary

Image identity is determined from bounded content bytes, not filename suffix. Source
downloads remain immutable. Rotation is a `0/90/180/270` view transform persisted in
the existing `MapRecord.orientation` contract.

## Content inspection

The asset inspector recognizes PNG, JPEG, GIF, WebP, BMP, TIFF and SVG magic/XML. It
records detected format, MIME, byte length, checksum, dimensions where cheaply
available and a bounded diagnostic reason. SVG containing DTD/entity declarations,
active content or external resource references is rejected before rasterization.

Current read-only Owner inventory shows the opaque `.img` sample family contains SVG
bytes. The suffix is therefore not the decode failure. Raster bytes stored under `.img`
must decode normally; SVG requires an available safe rasterizer and otherwise fails
visibly as `SVG_RASTERIZER_UNAVAILABLE`.

## Preview and normalization

Raster preview opens a bounded byte stream with Pillow, never dispatches by suffix,
loads pixels before the source closes, rotates clockwise deterministically, thumbnails
and returns a detached RGBA image. SVG may use CairoSVG only when already available;
R1C does not install a new runtime. Optional PNG normalization is atomic and stores the
original checksum/format in its report; it never overwrites the source.

Training Studio owns a strong `PhotoImage` reference and displays detected format plus
bounded failure reason instead of a generic unavailable state.

Collector cache extension is selected from sniffed bytes. An SVG response is stored as
`.svg`, even when the server MIME is generic; a raster response receives its actual
safe suffix.

## Acceptance

1. PNG bytes under `.img` inspect as PNG with correct dimensions;
2. SVG bytes under `.img` inspect as SVG and never fail merely as an unknown suffix;
3. unsafe SVG fails closed;
4. byte-sniffed collector extension matches content;
5. clockwise rotations accept only 0/90/180/270 and MapRecord persistence survives reopen;
6. UI source keeps strong refs and renders format/reason on failure;
7. source/affected tests PASS; packaged Windows real-asset rotation remains R9.
