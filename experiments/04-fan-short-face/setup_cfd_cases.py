#!/usr/bin/env python3
"""
Generate the OpenFOAM case files (0/, constant/, system/) for experiment 4's
"end_mount" variant, and copy in the matching STL patches from
stl_out/end_mount/.

Run this once (or again after tweaking geometry/physics constants below) and
before run_cfd.sh:
    python3 setup_cfd_cases.py

Physics/BC values are computed here rather than hardcoded in the dict files
so the assumptions are all in one place. Same fan/air/turbulence assumptions
as experiment 1 (unchanged, so the comparison isolates fan/vent placement
only). See generate_geometry_v2.py for the box/fan geometry these numbers
are derived from.
"""

import math
import os
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
STL_OUT = os.path.join(ROOT, "stl_out")

VARIANTS = {
    "end_mount": {
        "case_dir": os.path.join(ROOT, "case-end-mount"),
        "fan_dir": (1.0, 0.0, 0.0),  # fan on -x wall, blows in +x (down the long axis)
    },
}

# ---------------------------------------------------------------------------
# Geometry (copied from generate_geometry_v2.py, kept in sync manually - see
# that script for the source of truth)
# ---------------------------------------------------------------------------
CM = 0.01
BOTTOM_L, BOTTOM_W = 33 * CM, 23 * CM
TOP_L, TOP_W = 39 * CM, 28 * CM
HEIGHT = 29 * CM
FAN_BLADE_DIA = 0.070

# ---------------------------------------------------------------------------
# Flow physics assumptions
# ---------------------------------------------------------------------------
FAN_CFM = 30.0                                   # typical 80mm PC fan free-air rating
FAN_FLOWRATE = FAN_CFM * 0.0004719474             # CFM -> m^3/s
FAN_AREA = math.pi * (FAN_BLADE_DIA / 2) ** 2
FAN_SPEED = FAN_FLOWRATE / FAN_AREA               # m/s, average velocity over blade sweep

NU = 1.5e-05                                      # air kinematic viscosity, m^2/s
TURB_INTENSITY = 0.05
TURB_LENGTH_SCALE = 0.07 * FAN_BLADE_DIA          # ~7% of fan diameter, standard estimate

K_INLET = 1.5 * (FAN_SPEED * TURB_INTENSITY) ** 2
CMU = 0.09
OMEGA_INLET = math.sqrt(K_INLET) / (CMU ** 0.25 * TURB_LENGTH_SCALE)

# small ambient background values used as internalField initial guesses
K_INTERNAL = max(K_INLET * 0.05, 1e-4)
OMEGA_INTERNAL = max(OMEGA_INLET * 0.1, 1.0)

# ---------------------------------------------------------------------------
# Background mesh domain: box bounding box (using the wider TOP dims) + margin
# ---------------------------------------------------------------------------
MARGIN = 0.01
XMIN, XMAX = -(TOP_L / 2 + MARGIN), (TOP_L / 2 + MARGIN)
YMIN, YMAX = -(TOP_W / 2 + MARGIN), (TOP_W / 2 + MARGIN)
ZMIN, ZMAX = -MARGIN, HEIGHT + MARGIN
CELL_SIZE = 0.012  # 12mm background cells

NX = max(round((XMAX - XMIN) / CELL_SIZE), 1)
NY = max(round((YMAX - YMIN) / CELL_SIZE), 1)
NZ = max(round((ZMAX - ZMIN) / CELL_SIZE), 1)

LOCATION_IN_MESH = (0.0, 0.0, HEIGHT * 0.5)  # empty interior point, mid-height/center

# rod refinement box: generous margin around where the rods actually sit
# (ROD_HEIGHT_FRAC * HEIGHT in generate_geometry_v2.py, +/- a chunk of height)
ROD_BOX_MIN = (XMIN + MARGIN, YMIN + MARGIN, HEIGHT * 0.45)
ROD_BOX_MAX = (XMAX - MARGIN, YMAX - MARGIN, HEIGHT * 0.85)


def foam_header(cls, obj, location=None):
    loc_line = f'    location    "{location}";\n' if location else ""
    return f"""FoamFile
{{
    version     2.0;
    format      ascii;
    class       {cls};
{loc_line}    object      {obj};
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

"""


def vec(v):
    return f"({v[0]:.6g} {v[1]:.6g} {v[2]:.6g})"


# ---------------------------------------------------------------------------
# constant/
# ---------------------------------------------------------------------------

def write_constant(case_dir):
    cdir = os.path.join(case_dir, "constant")

    with open(os.path.join(cdir, "transportProperties"), "w") as f:
        f.write(foam_header("dictionary", "transportProperties", "constant"))
        f.write(f"""transportModel  Newtonian;

nu              [0 2 -1 0 0 0 0] {NU:.3e};
""")

    with open(os.path.join(cdir, "turbulenceProperties"), "w") as f:
        f.write(foam_header("dictionary", "turbulenceProperties", "constant"))
        f.write("""simulationType  RAS;

RAS
{
    RASModel        kOmegaSST;
    turbulence      on;
    printCoeffs     on;
}
""")


# ---------------------------------------------------------------------------
# system/
# ---------------------------------------------------------------------------

def write_block_mesh_dict(case_dir):
    path = os.path.join(case_dir, "system", "blockMeshDict")
    with open(path, "w") as f:
        f.write(foam_header("dictionary", "blockMeshDict", "system"))
        f.write(f"""convertToMeters 1;

vertices
(
    ({XMIN:.6g} {YMIN:.6g} {ZMIN:.6g})
    ({XMAX:.6g} {YMIN:.6g} {ZMIN:.6g})
    ({XMAX:.6g} {YMAX:.6g} {ZMIN:.6g})
    ({XMIN:.6g} {YMAX:.6g} {ZMIN:.6g})
    ({XMIN:.6g} {YMIN:.6g} {ZMAX:.6g})
    ({XMAX:.6g} {YMIN:.6g} {ZMAX:.6g})
    ({XMAX:.6g} {YMAX:.6g} {ZMAX:.6g})
    ({XMIN:.6g} {YMAX:.6g} {ZMAX:.6g})
);

blocks
(
    hex (0 1 2 3 4 5 6 7) ({NX} {NY} {NZ}) simpleGrading (1 1 1)
);

edges
(
);

boundary
(
    outerBound
    {{
        type patch;
        faces
        (
            (0 3 2 1)
            (4 5 6 7)
            (0 1 5 4)
            (1 2 6 5)
            (2 3 7 6)
            (3 0 4 7)
        );
    }}
);

mergePatchPairs
(
);
""")


def write_snappy_hex_mesh_dict(case_dir, variant):
    path = os.path.join(case_dir, "system", "snappyHexMeshDict")
    with open(path, "w") as f:
        f.write(foam_header("dictionary", "snappyHexMeshDict", "system"))
        f.write(f"""castellatedMesh true;
snap            true;
addLayers       false;

geometry
{{
    {variant}_walls.stl
    {{
        type triSurfaceMesh;
        name walls;
    }}
    {variant}_fan.stl
    {{
        type triSurfaceMesh;
        name fan;
    }}
    {variant}_outlet.stl
    {{
        type triSurfaceMesh;
        name outlet;
    }}
    {variant}_rods.stl
    {{
        type triSurfaceMesh;
        name rods;
    }}
    rodRefineBox
    {{
        type searchableBox;
        min {vec(ROD_BOX_MIN)};
        max {vec(ROD_BOX_MAX)};
    }}
}}

castellatedMeshControls
{{
    maxLocalCells 2000000;
    maxGlobalCells 4000000;
    minRefinementCells 0;
    maxLoadUnbalance 0.10;
    nCellsBetweenLevels 3;

    features
    (
    );

    refinementSurfaces
    {{
        walls  {{ level (0 0); patchInfo {{ type wall; }} }}
        fan    {{ level (3 3); patchInfo {{ type patch; }} }}
        outlet {{ level (2 2); patchInfo {{ type patch; }} }}
        rods   {{ level (3 3); patchInfo {{ type wall; }} }}
    }}

    resolveFeatureAngle 30;

    refinementRegions
    {{
        rodRefineBox {{ mode inside; levels ((1 2)); }}
    }}

    locationInMesh {vec(LOCATION_IN_MESH)};
    allowFreeStandingZoneFaces true;
}}

snapControls
{{
    nSmoothPatch 3;
    tolerance 2.0;
    nSolveIter 30;
    nRelaxIter 5;
}}

addLayersControls
{{
    relativeSizes true;
    layers {{}}
    expansionRatio 1.2;
    finalLayerThickness 0.3;
    minThickness 0.1;
    nGrow 0;
    featureAngle 60;
    nRelaxIter 3;
    nSmoothSurfaceNormals 1;
    nSmoothNormals 3;
    nSmoothThickness 10;
    maxFaceThicknessRatio 0.5;
    maxThicknessToMedialRatio 0.3;
    minMedialAxisAngle 90;
    nBufferCellsNoExtrude 0;
    nLayerIter 50;
}}

meshQualityControls
{{
    maxNonOrtho 65;
    maxBoundarySkewness 20;
    maxInternalSkewness 4;
    maxConcave 80;
    minVol 1e-13;
    minTetQuality 1e-9;
    minArea -1;
    minTwist 0.02;
    minDeterminant 0.001;
    minFaceWeight 0.02;
    minVolRatio 0.01;
    minTriangleTwist -1;
    nSmoothScale 4;
    errorReduction 0.75;
}}

mergeTolerance 1e-6;
""")


def write_control_dict(case_dir):
    path = os.path.join(case_dir, "system", "controlDict")
    with open(path, "w") as f:
        f.write(foam_header("dictionary", "controlDict", "system"))
        f.write("""application     simpleFoam;

startFrom       latestTime;
startTime       0;

stopAt          endTime;
endTime         500;

deltaT          1;

writeControl    timeStep;
writeInterval   100;

purgeWrite      2;

writeFormat     ascii;
writePrecision  6;
writeCompression off;

timeFormat      general;
timePrecision   6;

runTimeModifiable true;
""")


def write_fv_schemes(case_dir):
    path = os.path.join(case_dir, "system", "fvSchemes")
    with open(path, "w") as f:
        f.write(foam_header("dictionary", "fvSchemes", "system"))
        f.write("""ddtSchemes
{
    default         steadyState;
}

gradSchemes
{
    default         Gauss linear;
}

divSchemes
{
    default             none;
    div(phi,U)          bounded Gauss linearUpwindV grad(U);
    div(phi,k)          bounded Gauss upwind;
    div(phi,omega)      bounded Gauss upwind;
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}

laplacianSchemes
{
    default         Gauss linear corrected;
}

interpolationSchemes
{
    default         linear;
}

snGradSchemes
{
    default         corrected;
}

wallDist
{
    method          meshWave;
}
""")


def write_fv_solution(case_dir):
    path = os.path.join(case_dir, "system", "fvSolution")
    with open(path, "w") as f:
        f.write(foam_header("dictionary", "fvSolution", "system"))
        f.write("""solvers
{
    p
    {
        solver          GAMG;
        tolerance       1e-06;
        relTol          0.05;
        smoother        GaussSeidel;
    }

    "(U|k|omega)"
    {
        solver          smoothSolver;
        smoother        symGaussSeidel;
        tolerance       1e-08;
        relTol          0.1;
    }
}

SIMPLE
{
    nNonOrthogonalCorrectors 2;

    residualControl
    {
        p               1e-4;
        U               1e-4;
        "(k|omega)"     1e-4;
    }
}

relaxationFactors
{
    fields
    {
        p               0.3;
    }
    equations
    {
        U               0.7;
        "(k|omega)"     0.7;
    }
}
""")


# ---------------------------------------------------------------------------
# 0/
# ---------------------------------------------------------------------------

def write_field_files(case_dir, fan_dir):
    fan_u = tuple(FAN_SPEED * c for c in fan_dir)
    zdir = os.path.join(case_dir, "0")

    with open(os.path.join(zdir, "U"), "w") as f:
        f.write(foam_header("volVectorField", "U", "0"))
        f.write(f"""dimensions      [0 1 -1 0 0 0 0];

internalField   uniform (0 0 0);

boundaryField
{{
    walls
    {{
        type            noSlip;
    }}
    rods
    {{
        type            noSlip;
    }}
    fan
    {{
        type            fixedValue;
        value           uniform {vec(fan_u)};
    }}
    outlet
    {{
        type            pressureInletOutletVelocity;
        value           uniform (0 0 0);
    }}
    outerBound
    {{
        type            noSlip;
    }}
}}
""")

    with open(os.path.join(zdir, "p"), "w") as f:
        f.write(foam_header("volScalarField", "p", "0"))
        f.write("""dimensions      [0 2 -2 0 0 0 0];

internalField   uniform 0;

boundaryField
{
    walls
    {
        type            zeroGradient;
    }
    rods
    {
        type            zeroGradient;
    }
    fan
    {
        type            zeroGradient;
    }
    outlet
    {
        type            fixedValue;
        value           uniform 0;
    }
    outerBound
    {
        type            zeroGradient;
    }
}
""")

    with open(os.path.join(zdir, "k"), "w") as f:
        f.write(foam_header("volScalarField", "k", "0"))
        f.write(f"""dimensions      [0 2 -2 0 0 0 0];

internalField   uniform {K_INTERNAL:.6g};

boundaryField
{{
    walls
    {{
        type            kqRWallFunction;
        value           uniform {K_INTERNAL:.6g};
    }}
    rods
    {{
        type            kqRWallFunction;
        value           uniform {K_INTERNAL:.6g};
    }}
    fan
    {{
        type            fixedValue;
        value           uniform {K_INLET:.6g};
    }}
    outlet
    {{
        type            inletOutlet;
        inletValue      uniform {K_INTERNAL:.6g};
        value           uniform {K_INTERNAL:.6g};
    }}
    outerBound
    {{
        type            zeroGradient;
    }}
}}
""")

    with open(os.path.join(zdir, "omega"), "w") as f:
        f.write(foam_header("volScalarField", "omega", "0"))
        f.write(f"""dimensions      [0 0 -1 0 0 0 0];

internalField   uniform {OMEGA_INTERNAL:.6g};

boundaryField
{{
    walls
    {{
        type            omegaWallFunction;
        value           uniform {OMEGA_INTERNAL:.6g};
    }}
    rods
    {{
        type            omegaWallFunction;
        value           uniform {OMEGA_INTERNAL:.6g};
    }}
    fan
    {{
        type            fixedValue;
        value           uniform {OMEGA_INLET:.6g};
    }}
    outlet
    {{
        type            inletOutlet;
        inletValue      uniform {OMEGA_INTERNAL:.6g};
        value           uniform {OMEGA_INTERNAL:.6g};
    }}
    outerBound
    {{
        type            zeroGradient;
    }}
}}
""")

    with open(os.path.join(zdir, "nut"), "w") as f:
        f.write(foam_header("volScalarField", "nut", "0"))
        f.write("""dimensions      [0 2 -1 0 0 0 0];

internalField   uniform 0;

boundaryField
{
    walls
    {
        type            nutkWallFunction;
        value           uniform 0;
    }
    rods
    {
        type            nutkWallFunction;
        value           uniform 0;
    }
    fan
    {
        type            calculated;
        value           uniform 0;
    }
    outlet
    {
        type            calculated;
        value           uniform 0;
    }
    outerBound
    {
        type            calculated;
        value           uniform 0;
    }
}
""")


def copy_stls(variant, case_dir):
    src_dir = os.path.join(STL_OUT, variant)
    dst_dir = os.path.join(case_dir, "constant", "triSurface")
    for part in ("walls", "fan", "outlet", "rods"):
        fname = f"{variant}_{part}.stl"
        shutil.copy2(os.path.join(src_dir, fname), os.path.join(dst_dir, fname))


def main():
    print(f"Fan: {FAN_CFM:.0f} CFM over {FAN_BLADE_DIA*1000:.0f}mm blade dia "
          f"-> inlet speed {FAN_SPEED:.3f} m/s")
    print(f"Turbulence inlet: k={K_INLET:.4g} m2/s2, omega={OMEGA_INLET:.4g} 1/s")
    print(f"Background mesh: {NX} x {NY} x {NZ} = {NX*NY*NZ} cells "
          f"(before snappyHexMesh refinement)")

    for variant, cfg in VARIANTS.items():
        case_dir = cfg["case_dir"]
        print(f"\n--- {variant} -> {os.path.relpath(case_dir, ROOT)} ---")
        for sub in ("0", "constant", "constant/triSurface", "system"):
            os.makedirs(os.path.join(case_dir, sub), exist_ok=True)

        write_constant(case_dir)
        write_block_mesh_dict(case_dir)
        write_snappy_hex_mesh_dict(case_dir, variant)
        write_control_dict(case_dir)
        write_fv_schemes(case_dir)
        write_fv_solution(case_dir)
        write_field_files(case_dir, cfg["fan_dir"])
        copy_stls(variant, case_dir)
        print("  case files + STLs written")

    print("\nDone. Next: ./run_cfd.sh end_mount")


if __name__ == "__main__":
    main()
