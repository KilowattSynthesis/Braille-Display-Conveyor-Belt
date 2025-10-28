import itertools
import json
import math
from dataclasses import dataclass
from pathlib import Path

import build123d as bd
import build123d_ease as bde
from build123d_ease import show
from loguru import logger


@dataclass
class Spec:
    """Specification for magnetic_pulley."""

    magnet_d: float = 2.0
    magnet_h: float = 0.6

    # MARK: Braille specs.
    dot_pitch_x: float = 2.5
    dot_pitch_y: float = 2.5
    cell_pitch_x: float = 6.0
    cell_pitch_y: float = 10.0
    cell_count_around_circumference: int = 3
    # cell_count_y: int = 1  # Assumed.

    # MARK: Pulley specs.
    pulley_body_length: float = 8.5  # Width of tape.
    flange_lip_height: float = 1.2

    center_hole_d: float = 2.0

    def __post_init__(self) -> None:
        """Post initialization checks."""
        data = {
            "pulley_body_circumference": self.pulley_body_circumference,
            "pulley_body_od": round(self.pulley_body_od, 3),
        }
        logger.info(f"Pulley data: {json.dumps(data, indent=2)}")

    @property
    def pulley_body_circumference(self) -> float:
        """Total circumference of the pulley body (where the tape rides)."""
        return self.cell_count_around_circumference * self.cell_pitch_x

    @property
    def pulley_body_od(self) -> float:
        """Pulley outer diameter."""
        return self.pulley_body_circumference / math.pi

    def circumference_mm_to_angle(self, mm: float) -> float:
        """Convert a distance along the circumference to an angle (deg)."""
        return (mm / self.pulley_body_circumference) * 360.0


# MARK: magnetic_pulley
def magnetic_pulley(spec: Spec) -> bd.Part | bd.Compound:
    """Create a CAD model of magnetic_pulley.

    The pulley's axle is along the Z axis.
    """
    p = bd.Part(None)

    p += bd.Cylinder(
        radius=(spec.pulley_body_od / 2),
        height=spec.pulley_body_length,
    )

    # Remove the grid of magnets (around pulley body circumference).
    for cell_idx in range(spec.cell_count_around_circumference):
        for dot_pos_around_circumference, dot_z in itertools.product(
            bde.evenly_space_with_center(count=2, spacing=spec.dot_pitch_x),
            bde.evenly_space_with_center(count=3, spacing=spec.dot_pitch_y),
        ):
            dot_angle_pos = (
                cell_idx * 360 / spec.cell_count_around_circumference
            ) + (spec.circumference_mm_to_angle(dot_pos_around_circumference))

            p -= (
                bd.extrude(
                    bd.RegularPolygon(
                        radius=spec.magnet_d / 2 - 0.1,
                        side_count=6,
                        major_radius=False,  # Across the flats.
                    ),
                    5,  # Must extend out far!
                    dir=(0, 0, 1),
                )
                .rotate(axis=bd.Axis.Y, angle=90)  # Point in +X.
                .translate((spec.pulley_body_od / 2 - spec.magnet_h, 0, dot_z))
                .rotate(axis=bd.Axis.Z, angle=dot_angle_pos)
            )

    # Add the flanges.
    for align, z_sign in (
        (bde.align.ANCHOR_BOTTOM, 1),
        (bde.align.ANCHOR_TOP, -1),
    ):
        p += bd.Pos(Z=z_sign * spec.pulley_body_length / 2) * bd.Cylinder(
            radius=(spec.pulley_body_od / 2 + spec.flange_lip_height),
            height=spec.flange_lip_height,
            align=align,
        )

    # Cut out the center hole.
    p -= bd.Cylinder(
        radius=(spec.center_hole_d / 2),
        height=spec.pulley_body_length + 2 * spec.flange_lip_height,
        align=bde.align.ANCHOR_CENTER,
    )

    return p


if __name__ == "__main__":
    parts = {
        # "magnetic_pulley": show(magnetic_pulley(Spec())),
        "magnetic_pulley_3_cells": show(
            magnetic_pulley(Spec(cell_count_around_circumference=3))
        ),
        "magnetic_pulley_4_cells": show(
            magnetic_pulley(Spec(cell_count_around_circumference=4))
        ),
    }

    logger.info("Showing CAD model(s)")

    export_folder = (
        Path(__file__).parent.parent / "build" / (Path(__file__).stem)
    )
    export_folder.mkdir(exist_ok=True, parents=True)
    for name, part in parts.items():
        assert isinstance(part, bd.Part | bd.Solid | bd.Compound), (
            f"{name} is not an expected type ({type(part)})"
        )
        if not part.is_manifold:
            logger.warning(f'Part "{name}" is not manifold')

        bd.export_stl(part, str(export_folder / f"{name}.stl"))
        bd.export_step(part, str(export_folder / f"{name}.step"))
