"""Project-local Matplotlib export using only public Matplotlib/Pillow APIs."""
from pathlib import Path
import math


def export_figure(fig, basename, formats=("png", "svg"), dpi=300,
                  size_inches=None, tight=False, grayscale_preview=False):
    if not math.isfinite(float(dpi)) or dpi <= 0:
        raise ValueError("dpi must be positive and finite")
    if size_inches is not None:
        if len(size_inches) != 2 or any(not math.isfinite(float(x)) or x <= 0
                                         for x in size_inches):
            raise ValueError("size_inches must contain two positive finite values")
        fig.set_size_inches(*size_inches)
    base = Path(basename)
    base.parent.mkdir(parents=True, exist_ok=True)
    written = {}
    for extension in formats:
        extension = extension.lower().lstrip(".")
        if extension not in {"png", "svg", "pdf"}:
            raise ValueError(f"unsupported output format: {extension}")
        target = base.parent / f"{base.name}.{extension}"
        options = {"dpi": dpi, "format": extension, "facecolor": "white",
                   "bbox_inches": "tight" if tight else None}
        if extension == "svg":
            options["metadata"] = {"Date": None}
        if extension == "pdf":
            options["metadata"] = {"CreationDate": None, "ModDate": None}
        fig.savefig(target, **options)
        written[extension] = str(target)
    if grayscale_preview:
        from PIL import Image
        if "png" not in written:
            raise ValueError("grayscale preview requires a PNG output")
        target = base.parent / f"{base.name}_grayscale.png"
        with Image.open(written["png"]) as color:
            color.convert("L").save(target, dpi=(dpi, dpi))
        written["grayscale"] = str(target)
    return written
