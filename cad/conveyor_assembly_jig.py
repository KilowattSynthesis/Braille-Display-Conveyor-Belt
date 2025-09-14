import itertools
from dataclasses import dataclass
from pathlib import Path

import build123d as bd
import build123d_ease as bde
from build123d_ease import show
from loguru import logger


@dataclass
class Spec:
    """Specification for conveyor_assembly_jig."""

    magnet_d: float = 2.1
    magnet_h: float = 1.2

    # MARK: Braille specs.
    dot_pitch_x: float = 2.5
    dot_pitch_y: float = 2.5
    cell_pitch_x: float = 6.0
    cell_pitch_y: float = 10.0
    cell_count_x: int = 4
    cell_count_y: int = 2

    # MARK: Body specs.
    total_z: float = 5.0

    arm_width_on_long_side: float = 5.0
    arm_width_along_short_gap: float = 4.0
    arm_gap_width: float = 6.0

    def __post_init__(self) -> None:
        """Post initialization checks."""

    @property
    def total_x(self) -> float:
        """Total X dimension."""
        return (
            (self.cell_count_x * self.cell_pitch_x)
            + (2 * 5.0)
            + (2 * self.arm_width_on_long_side + 2 * self.arm_gap_width)
        )

    @property
    def total_y(self) -> float:
        """Total Y dimension."""
        return (self.cell_count_y * self.cell_pitch_y) + (2 * 5.0)


# MARK: conveyor_assembly_jig
def conveyor_assembly_jig(spec: Spec) -> bd.Part | bd.Compound:
    """Create a CAD model of conveyor_assembly_jig."""
    p = bd.Part(None)

    p += bd.Box(
        spec.total_x, spec.total_y, spec.total_z, align=bde.align.ANCHOR_BOTTOM
    )

    # Remove the grid of magnets.
    for cell_center_x, cell_center_y in itertools.product(
        bde.evenly_space_with_center(
            count=spec.cell_count_x, spacing=spec.cell_pitch_x
        ),
        bde.evenly_space_with_center(
            count=spec.cell_count_y, spacing=spec.cell_pitch_y
        ),
    ):
        for dot_x, dot_y in itertools.product(
            bde.evenly_space_with_center(
                count=2, spacing=spec.dot_pitch_x, center=cell_center_x
            ),
            bde.evenly_space_with_center(
                count=3, spacing=spec.dot_pitch_y, center=cell_center_y
            ),
        ):
            p -= bd.Cylinder(
                spec.magnet_d / 2,
                spec.magnet_h,
                align=bde.align.ANCHOR_TOP,
            ).translate((dot_x, dot_y, spec.total_z))

    # Remove the arm gaps.
    for x_sign in (1, -1):
        p -= bd.Pos(
            X=(
                x_sign
                * (
                    spec.total_x / 2
                    - spec.arm_width_on_long_side
                    - spec.arm_gap_width / 2
                )
            )
        ) * bd.Box(
            spec.arm_gap_width,
            spec.total_y - 2 * spec.arm_width_along_short_gap,
            spec.total_z,
            align=bde.align.ANCHOR_BOTTOM,
        )

    return p


if __name__ == "__main__":
    parts = {
        "conveyor_assembly_jig": show(conveyor_assembly_jig(Spec())),
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
