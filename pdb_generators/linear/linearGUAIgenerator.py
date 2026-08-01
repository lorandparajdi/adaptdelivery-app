#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Linear GUAI polymer generator - corrected H7/H8 join version.

Behavior:
    - the LEFT/GUAI first block is copied from guai1.pdb geometry
    - the middle GUAI blocks are copied from the guai4.pdb middle-block geometry
    - the RIGHT terminal GUAI block is copied from guai4.pdb last-residue geometry
    - blocks are glued linearly through the same C8 -> O4 connection logic used
      by the SYR generator

Result:
    H-[GUAI]_n-H
"""

from __future__ import annotations
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import numpy as np

POLYMER_LABEL = "GUAI"
RESNAME = " GUAI "
DEFAULT_TAIL = "  1.00  0.00      LIG4  "
C8_O4_BOND = 1.454

# Embedded fallback blocks extracted from the uploaded GUAI templates.
# The script first tries to read guai1.pdb/guai4.pdb from the same folder;
# if they are missing, these embedded blocks are used.
EMBEDDED_LEFT_BLOCK: List[Dict] = [{'atom': ' C6 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG1  ',
  'x': -0.912,
  'y': 1.473,
  'z': -1.015},
 {'atom': ' H6 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG1  ',
  'x': -1.979,
  'y': 1.485,
  'z': -1.217},
 {'atom': ' C2 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG1  ',
  'x': 1.093,
  'y': 0.27,
  'z': -0.391},
 {'atom': ' H2 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG1  ',
  'x': 1.559,
  'y': -0.665,
  'z': -0.099},
 {'atom': ' C3 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG1  ',
  'x': 1.835,
  'y': 1.448,
  'z': -0.45},
 {'atom': ' O3 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG1  ',
  'x': 3.171,
  'y': 1.559,
  'z': -0.19},
 {'atom': ' C10',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG1  ',
  'x': 3.83,
  'y': 0.368,
  'z': 0.235},
 {'atom': 'H101',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG1  ',
  'x': 4.861,
  'y': 0.663,
  'z': 0.423},
 {'atom': 'H102',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG1  ',
  'x': 3.382,
  'y': -0.027,
  'z': 1.153},
 {'atom': 'H103',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG1  ',
  'x': 3.804,
  'y': -0.401,
  'z': -0.545},
 {'atom': ' C4 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG1  ',
  'x': 1.195,
  'y': 2.654,
  'z': -0.812},
 {'atom': ' O4 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG1  ',
  'x': 1.985,
  'y': 3.774,
  'z': -0.868},
 {'atom': ' HO4',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG1  ',
  'x': 1.415,
  'y': 4.524,
  'z': -1.114},
 {'atom': ' C5 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG1  ',
  'x': -0.168,
  'y': 2.655,
  'z': -1.089},
 {'atom': ' H5 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG1  ',
  'x': -0.656,
  'y': 3.591,
  'z': -1.362},
 {'atom': ' C1 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG1  ',
  'x': -0.282,
  'y': 0.277,
  'z': -0.673},
 {'atom': ' C7 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG1  ',
  'x': -1.075,
  'y': -1.002,
  'z': -0.557},
 {'atom': ' H7 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG1  ',
  'x': -0.43,
  'y': -1.855,
  'z': -0.824},
 {'atom': ' C8 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG1  ',
  'x': -1.566,
  'y': -1.24,
  'z': 0.865},
 {'atom': ' H8 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG1  ',
  'x': -2.201,
  'y': -0.394,
  'z': 1.168},
 {'atom': ' C9 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG1  ',
  'x': -2.364,
  'y': -2.525,
  'z': 0.988},
 {'atom': ' O9 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG1  ',
  'x': -2.584,
  'y': -2.691,
  'z': 2.397},
 {'atom': ' HO9',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG1  ',
  'x': -2.969,
  'y': -3.572,
  'z': 2.541},
 {'atom': ' H91',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG1  ',
  'x': -3.306,
  'y': -2.451,
  'z': 0.436},
 {'atom': ' H92',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG1  ',
  'x': -1.771,
  'y': -3.357,
  'z': 0.581}]

EMBEDDED_MIDDLE_BLOCK: List[Dict] = [{'atom': ' C6 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': 3.395,
  'y': 4.275,
  'z': 1.77},
 {'atom': ' H6 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': 4.132,
  'y': 4.115,
  'z': 2.552},
 {'atom': ' C2 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': 1.174,
  'y': 3.94,
  'z': 0.87},
 {'atom': ' H2 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': 0.189,
  'y': 3.502,
  'z': 0.978},
 {'atom': ' C3 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': 1.517,
  'y': 4.652,
  'z': -0.278},
 {'atom': ' O3 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': 0.69,
  'y': 4.893,
  'z': -1.337},
 {'atom': ' C10',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': -0.62,
  'y': 4.338,
  'z': -1.251},
 {'atom': 'H101',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': -1.112,
  'y': 4.617,
  'z': -2.183},
 {'atom': 'H102',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': -0.585,
  'y': 3.247,
  'z': -1.161},
 {'atom': 'H103',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': -1.175,
  'y': 4.756,
  'z': -0.403},
 {'atom': ' C4 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': 2.815,
  'y': 5.196,
  'z': -0.397},
 {'atom': ' O4 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': 3.118,
  'y': 5.903,
  'z': -1.55},
 {'atom': ' C5 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': 3.74,
  'y': 4.999,
  'z': 0.621},
 {'atom': ' H5 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': 4.741,
  'y': 5.419,
  'z': 0.523},
 {'atom': ' C1 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': 2.112,
  'y': 3.744,
  'z': 1.899},
 {'atom': ' C7 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': 1.772,
  'y': 2.925,
  'z': 3.141},
 {'atom': ' H7 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': 1.927,
  'y': 1.864,
  'z': 2.914},
 {'atom': ' O7 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': 2.675,
  'y': 3.2,
  'z': 4.225},
 {'atom': ' HO7',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': 2.709,
  'y': 4.169,
  'z': 4.32},
 {'atom': ' C8 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': 0.343,
  'y': 3.073,
  'z': 3.682},
 {'atom': ' H8 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': 0.314,
  'y': 2.562,
  'z': 4.653},
 {'atom': ' C9 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': -0.152,
  'y': 4.494,
  'z': 3.883},
 {'atom': ' O9 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': -1.448,
  'y': 4.48,
  'z': 4.472},
 {'atom': ' HO9',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': -1.986,
  'y': 3.938,
  'z': 3.867},
 {'atom': ' H91',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': 0.503,
  'y': 5.023,
  'z': 4.582},
 {'atom': ' H92',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': -0.15,
  'y': 5.036,
  'z': 2.929}]

EMBEDDED_RIGHT_BLOCK: List[Dict] = [{'atom': ' C6 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': -4.162,
  'y': -7.594,
  'z': 0.771},
 {'atom': ' H6 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': -5.096,
  'y': -8.15,
  'z': 0.741},
 {'atom': ' C2 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': -1.971,
  'y': -7.112,
  'z': -0.132},
 {'atom': ' H2 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': -1.212,
  'y': -7.318,
  'z': -0.878},
 {'atom': ' C3 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': -1.738,
  'y': -6.192,
  'z': 0.888},
 {'atom': ' O3 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': -0.597,
  'y': -5.457,
  'z': 1.047},
 {'atom': ' C10',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': 0.437,
  'y': -5.688,
  'z': 0.094},
 {'atom': 'H101',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': 1.256,
  'y': -5.036,
  'z': 0.396},
 {'atom': 'H102',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': 0.767,
  'y': -6.732,
  'z': 0.11},
 {'atom': 'H103',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': 0.112,
  'y': -5.425,
  'z': -0.919},
 {'atom': ' C4 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': -2.739,
  'y': -5.958,
  'z': 1.856},
 {'atom': ' O4 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': -2.508,
  'y': -5.088,
  'z': 2.902},
 {'atom': ' C5 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': -3.935,
  'y': -6.663,
  'z': 1.792},
 {'atom': ' H5 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': -4.704,
  'y': -6.481,
  'z': 2.543},
 {'atom': ' C1 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': -3.182,
  'y': -7.822,
  'z': -0.194},
 {'atom': ' C7 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': -3.39,
  'y': -8.832,
  'z': -1.3},
 {'atom': ' H7 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': -2.998,
  'y': -8.417,
  'z': -2.242},
 {'atom': ' C8 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': -2.644,
  'y': -10.145,
  'z': -1.071},
 {'atom': ' H8 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': -1.57,
  'y': -9.908,
  'z': -1.014},
 {'atom': ' C9 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': -2.85,
  'y': -11.159,
  'z': -2.177},
 {'atom': ' O9 ',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': -2.116,
  'y': -12.319,
  'z': -1.753},
 {'atom': ' HO9',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': -2.376,
  'y': -13.062,
  'z': -2.323},
 {'atom': ' H91',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': -3.919,
  'y': -11.385,
  'z': -2.268},
 {'atom': ' H92',
  'record': 'ATOM',
  'res': 'GUAIL',
  'tail': '  1.00  0.00      LIG4  ',
  'x': -2.477,
  'y': -10.769,
  'z': -3.132}]

INTRA_BONDS_UNIT_END = [
    ("C1", "C2"), ("C2", "C3"), ("C3", "C4"), ("C4", "C5"), ("C5", "C6"), ("C6", "C1"),
    ("C3", "O3"), ("O3", "C10"),
    ("C4", "O4"),
    ("C1", "C7"), ("C7", "O7"), ("C7", "C8"), ("C8", "C9"), ("C9", "O9"),
    ("C2", "H2"), ("C5", "H5"), ("C6", "H6"), ("C7", "H7"), ("C8", "H8"),
    ("C9", "H91"), ("C9", "H92"), ("O7", "HO7"), ("O9", "HO9"),
    ("C10", "H101"), ("C10", "H102"), ("C10", "H103"),
]

INTRA_BONDS_UNIT_MID = INTRA_BONDS_UNIT_END
INTRA_BONDS_CAP_LEFT_ONLY = INTRA_BONDS_UNIT_MID + [("O4", "HO4")]
INTRA_BONDS_SINGLE = INTRA_BONDS_UNIT_END + [("O4", "HO4")]


def _deepcopy_atoms(atoms: List[Dict]) -> List[Dict]:
    return [dict(a) for a in atoms]


def _find_atom(atoms: List[Dict], atom_name: str) -> Optional[Dict]:
    target = atom_name.strip().upper()
    for a in atoms:
        if a["atom"].strip().upper() == target:
            return a
    return None


def _parse_guai_residues(template_pdb: str) -> Dict[int, List[Dict]]:
    path = Path(template_pdb)
    if not path.exists():
        raise FileNotFoundError(f"Template file not found: {template_pdb}")

    residues: Dict[int, List[Dict]] = {}
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if not line.startswith(("ATOM", "HETATM")):
                continue

            resname = line[17:22].strip().upper()
            if not resname.startswith("GUAI"):
                continue

            try:
                resseq = int(line[22:26])
                x = float(line[30:38])
                y = float(line[38:46])
                z = float(line[46:54])
            except ValueError:
                continue

            residues.setdefault(resseq, []).append({
                "record": line[0:6].strip() or "ATOM",
                "atom": line[12:16],
                "res": line[17:22],
                "tail": line[54:].rstrip("\n"),
                "x": x,
                "y": y,
                "z": z,
            })

    if not residues:
        raise ValueError(f"No GUAI residues found in template: {template_pdb}")

    for label, atoms in residues.items():
        names = {a["atom"].strip().upper() for a in atoms}
        missing = {"O4", "C4", "C8"} - names
        if missing:
            raise ValueError(f"GUAI residue {label} in {template_pdb} misses atoms needed for alignment: {sorted(missing)}")

    return residues


def _copy_atoms_relative_to_anchor(
    dst_atoms: List[Dict],
    src_atoms: List[Dict],
    atom_names: Tuple[str, ...],
    anchor_name: str = "C7",
) -> None:
    """Copy selected atoms from src to dst by keeping the same vector from anchor."""
    dst_anchor = _find_atom(dst_atoms, anchor_name)
    src_anchor = _find_atom(src_atoms, anchor_name)
    if dst_anchor is None or src_anchor is None:
        return

    p_dst_anchor = np.array([dst_anchor["x"], dst_anchor["y"], dst_anchor["z"]], dtype=float)
    p_src_anchor = np.array([src_anchor["x"], src_anchor["y"], src_anchor["z"]], dtype=float)

    for atom_name in atom_names:
        src = _find_atom(src_atoms, atom_name)
        if src is None:
            continue

        p_src = np.array([src["x"], src["y"], src["z"]], dtype=float)
        p_new = p_dst_anchor + (p_src - p_src_anchor)

        dst = _find_atom(dst_atoms, atom_name)
        if dst is None:
            dst = dict(src)
            dst["res"] = dst_anchor.get("res", src.get("res", RESNAME))
            dst_atoms.append(dst)

        dst["x"], dst["y"], dst["z"] = float(p_new[0]), float(p_new[1]), float(p_new[2])


def _remove_atoms(atoms: List[Dict], atom_names: Tuple[str, ...]) -> List[Dict]:
    remove = {name.strip().upper() for name in atom_names}
    return [a for a in atoms if a["atom"].strip().upper() not in remove]



def _aligned_reference_to_left_frame(left_block: List[Dict], reference_block: List[Dict]) -> List[Dict]:
    """Align a guai4 reference residue into the canonical guai1 local frame.

    This preserves the guai4 internal H/O substituent orientation, but rotates it
    into the same ring/chain frame as guai1 before any atoms are copied.
    """
    left_map = _atom_dict_from_list(left_block)
    target_o4, target_basis = _frame_from_atoms(left_map)
    return _transform_block_to_frame(reference_block, target_o4, target_basis)

def _make_consistent_guai_blocks(
    left_block: List[Dict],
    reference_middle_block: Optional[List[Dict]] = None,
) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """
    Build GUAI blocks with one fixed orientation for the whole chain.

    Some GUAI template files contain residues rotated differently around the
    O4->C8 chain axis.  That is why the old generator could make the middle
    residue appear flipped.  Here the first block from guai1.pdb is kept as
    the canonical orientation, and the middle/right blocks are derived from
    that same canonical geometry, so every ring has the same face direction.
    """
    left = _deepcopy_atoms(left_block)

    # Middle unit: same ring orientation as guai1, but without terminal HO4
    # because O4 is used for the incoming polymer bond.
    middle = _remove_atoms(_deepcopy_atoms(left_block), ("HO4",))

    # Internal GUAI units need the C7 hydroxyl and the correct C8 side-group
    # orientation from guai4.  Important: first rotate guai4 into the guai1
    # local O4/C8/C4 frame; copying raw guai4 vectors only by translation puts
    # H7/H8/O7/O9 on the wrong side of the join.
    if reference_middle_block is not None:
        ref_aligned = _aligned_reference_to_left_frame(left_block, reference_middle_block)
        _copy_atoms_relative_to_anchor(middle, ref_aligned, ("O7", "HO7", "H7"), anchor_name="C7")
        _copy_atoms_relative_to_anchor(middle, ref_aligned, ("C9", "O9", "HO9", "H91", "H92", "H8"), anchor_name="C8")

    # Right terminal unit: same orientation as guai1, no incoming HO4, and no
    # C7 hydroxyl, matching the terminal residue style from guai4.pdb.
    right = _remove_atoms(_deepcopy_atoms(left_block), ("HO4", "O7", "HO7"))

    return left, middle, right


def _get_template_blocks(template_dir: Optional[str] = None) -> Tuple[List[Dict], List[Dict], List[Dict], str]:
    base = Path(template_dir) if template_dir else Path(__file__).resolve().parent

    try:
        guai1 = _parse_guai_residues(str(base / "guai1.pdb"))
        guai4 = _parse_guai_residues(str(base / "guai4.pdb"))
        if 1 in guai1 and 2 in guai4:
            left, middle, right = _make_consistent_guai_blocks(guai1[1], guai4[2])
            return left, middle, right, "guai1.pdb + guai4.pdb | consistent orientation from guai1"
    except Exception:
        pass

    left, middle, right = _make_consistent_guai_blocks(EMBEDDED_LEFT_BLOCK, EMBEDDED_MIDDLE_BLOCK)
    return (
        left,
        middle,
        right,
        "embedded_guai1_blocks_consistent_orientation",
    )


def _atom_dict_from_list(atoms: List[Dict]) -> Dict[str, Dict]:
    return {a["atom"].strip().upper(): a for a in atoms}


def _frame_from_atoms(atoms_by_name: Dict[str, Dict]) -> Tuple[np.ndarray, np.ndarray]:
    o4 = np.array([atoms_by_name["O4"]["x"], atoms_by_name["O4"]["y"], atoms_by_name["O4"]["z"]], dtype=float)
    c8 = np.array([atoms_by_name["C8"]["x"], atoms_by_name["C8"]["y"], atoms_by_name["C8"]["z"]], dtype=float)
    c4 = np.array([atoms_by_name["C4"]["x"], atoms_by_name["C4"]["y"], atoms_by_name["C4"]["z"]], dtype=float)

    ex = c8 - o4
    ex = ex / np.linalg.norm(ex)

    v2 = c4 - o4
    v2 = v2 - np.dot(v2, ex) * ex
    nv2 = np.linalg.norm(v2)
    if nv2 < 1e-12:
        raise ValueError("Could not build a stable local frame from O4/C8/C4.")

    ey = v2 / nv2
    ez = np.cross(ex, ey)
    ez = ez / np.linalg.norm(ez)
    ey = np.cross(ez, ex)
    ey = ey / np.linalg.norm(ey)

    basis = np.column_stack([ex, ey, ez])
    return o4, basis


def _transform_block_to_frame(block: List[Dict], target_o4: np.ndarray, target_basis: np.ndarray) -> List[Dict]:
    atoms = _deepcopy_atoms(block)
    source_map = _atom_dict_from_list(atoms)
    source_o4, source_basis = _frame_from_atoms(source_map)

    R = target_basis @ source_basis.T
    t = target_o4 - R @ source_o4

    for a in atoms:
        p = np.array([a["x"], a["y"], a["z"]], dtype=float)
        p2 = R @ p + t
        a["x"], a["y"], a["z"] = float(p2[0]), float(p2[1]), float(p2[2])

    return atoms


def _format_pdb_line(serial: int, atom: Dict, resseq: int) -> str:
    record = (atom.get("record") or "ATOM").ljust(6)[:6]
    atom_field = atom["atom"].ljust(4)[:4]

    # Normalize residue name for correct parsing in 3Dmol.js/VMD.
    res_name = atom.get("res", RESNAME).strip().upper()
    if res_name.startswith("GUAI"):
        res_name = "GUAI"
    res_field = (" " + res_name).ljust(5)[:5]

    tail = atom.get("tail", DEFAULT_TAIL).rstrip()

    return (
        f"{record}{serial:5d} {atom_field}{res_field}{resseq:4d}     "
        f"{atom['x']:8.3f}{atom['y']:8.3f}{atom['z']:8.3f}{tail}"
    )


def _build_conect(atom_index: List[Tuple[int, int, str]], kinds: List[str]) -> List[str]:
    by_res: Dict[int, Dict[str, int]] = {}
    for serial, resseq, aname in atom_index:
        by_res.setdefault(resseq, {})[aname.strip().upper()] = serial

    bonds = []

    def add_bond(a: int, b: int):
        if a <= 0 or b <= 0 or a == b:
            return
        bonds.append((min(a, b), max(a, b)))

    for resseq, amap in by_res.items():
        kind = kinds[resseq - 1]
        if kind == "SINGLE":
            intra = INTRA_BONDS_SINGLE
        elif kind == "CAP":
            intra = INTRA_BONDS_CAP_LEFT_ONLY
        elif kind in ("END", "TEMPLATE_END"):
            intra = INTRA_BONDS_UNIT_END
        else:
            intra = INTRA_BONDS_UNIT_MID

        for a_name, b_name in intra:
            a = amap.get(a_name.strip().upper(), 0)
            b = amap.get(b_name.strip().upper(), 0)
            if a and b:
                add_bond(a, b)

        if (resseq + 1) in by_res:
            c8 = amap.get("C8", 0)
            o4n = by_res[resseq + 1].get("O4", 0)
            if c8 and o4n:
                add_bond(c8, o4n)

    grouped: Dict[int, List[int]] = {}
    for a, b in sorted(set(bonds)):
        grouped.setdefault(a, []).append(b)

    lines = []
    for a in sorted(grouped.keys()):
        partners = grouped[a]
        for i in range(0, len(partners), 4):
            chunk = partners[i:i + 4]
            lines.append("CONECT" + f"{a:5d}" + "".join(f"{p:5d}" for p in chunk))
    return lines


def _orient_chain_horizontal(residue_blocks: List[Tuple[int, List[Dict], str]]) -> None:
    if not residue_blocks:
        return

    first_o4 = _find_atom(residue_blocks[0][1], "O4")
    last_c8 = _find_atom(residue_blocks[-1][1], "C8") or _find_atom(residue_blocks[-1][1], "O4")
    if first_o4 is None or last_c8 is None:
        return

    p0 = np.array([first_o4["x"], first_o4["y"], first_o4["z"]], dtype=float)
    p1 = np.array([last_c8["x"], last_c8["y"], last_c8["z"]], dtype=float)
    ex = p1 - p0
    nex = np.linalg.norm(ex)
    if nex < 1e-12:
        return
    ex = ex / nex

    ey = None
    for _, atoms, _ in residue_blocks:
        o4 = _find_atom(atoms, "O4")
        c4 = _find_atom(atoms, "C4")
        if o4 is None or c4 is None:
            continue
        vo4 = np.array([o4["x"], o4["y"], o4["z"]], dtype=float)
        vc4 = np.array([c4["x"], c4["y"], c4["z"]], dtype=float)
        vup = vc4 - vo4
        vup = vup - np.dot(vup, ex) * ex
        nvup = np.linalg.norm(vup)
        if nvup > 1e-12:
            ey = vup / nvup
            break

    if ey is None:
        tmp = np.array([0.0, 0.0, 1.0], dtype=float)
        if abs(np.dot(tmp, ex)) > 0.9:
            tmp = np.array([0.0, 1.0, 0.0], dtype=float)
        ey = tmp - np.dot(tmp, ex) * ex
        ey = ey / np.linalg.norm(ey)

    if ey[1] < 0:
        ey = -ey

    ez = np.cross(ex, ey)
    nez = np.linalg.norm(ez)
    if nez < 1e-12:
        return
    ez = ez / nez
    ey = np.cross(ez, ex)
    ey = ey / np.linalg.norm(ey)

    B = np.column_stack([ex, ey, ez])
    R = B.T

    for _, atoms, _ in residue_blocks:
        for a in atoms:
            p = np.array([a["x"], a["y"], a["z"]], dtype=float) - p0
            p2 = R @ p
            a["x"], a["y"], a["z"] = float(p2[0]), float(p2[1]), float(p2[2])


def _rotate_point_around_axis(p: np.ndarray, a0: np.ndarray, axis: np.ndarray, angle_deg: float) -> np.ndarray:
    axis = axis / np.linalg.norm(axis)
    theta = np.deg2rad(angle_deg)
    v = p - a0
    v_rot = (
        v * np.cos(theta)
        + np.cross(axis, v) * np.sin(theta)
        + axis * np.dot(axis, v) * (1 - np.cos(theta))
    )
    return a0 + v_rot


def _rotate_chain_view_around_horizontal_axis(
    residue_blocks: List[Tuple[int, List[Dict], str]],
    angle_deg: float,
) -> None:
    """
    Rotate the whole GUAI chain around its horizontal chain axis.

    This changes only the initial visual orientation of the generated PDB.
    It does not change bond lengths, joins, terminal hydrogens, or local geometry.
    """
    if abs(angle_deg) < 1e-12 or not residue_blocks:
        return

    first_o4 = _find_atom(residue_blocks[0][1], "O4")
    last_c8 = _find_atom(residue_blocks[-1][1], "C8") or _find_atom(residue_blocks[-1][1], "O4")
    if first_o4 is None or last_c8 is None:
        return

    a0 = np.array([first_o4["x"], first_o4["y"], first_o4["z"]], dtype=float)
    a1 = np.array([last_c8["x"], last_c8["y"], last_c8["z"]], dtype=float)
    axis = a1 - a0
    if np.linalg.norm(axis) < 1e-12:
        return

    for _, atoms, _ in residue_blocks:
        for a in atoms:
            p = np.array([a["x"], a["y"], a["z"]], dtype=float)
            p2 = _rotate_point_around_axis(p, a0, axis, angle_deg)
            a["x"], a["y"], a["z"] = float(p2[0]), float(p2[1]), float(p2[2])



def _set_h7_position_from_neighbors(current_atoms: List[Dict]) -> None:
    """
    Reposition H7 when C7 also has the O7/HO7 hydroxyl group.

    guai1.pdb is a terminal block and its H7 direction is correct only for
    the terminal environment.  In an internal GUAI unit C7 is bonded to C1,
    C8 and O7, so H7 must be placed on the opposite tetrahedral side.  This
    keeps the visual join clean without moving the O4-C8 polymer bond.
    """
    c7 = _find_atom(current_atoms, "C7")
    c1 = _find_atom(current_atoms, "C1")
    c8 = _find_atom(current_atoms, "C8")
    o7 = _find_atom(current_atoms, "O7")
    h7 = _find_atom(current_atoms, "H7")

    if c7 is None or c1 is None or c8 is None or o7 is None or h7 is None:
        return

    p_c7 = np.array([c7["x"], c7["y"], c7["z"]], dtype=float)
    p_c1 = np.array([c1["x"], c1["y"], c1["z"]], dtype=float)
    p_c8 = np.array([c8["x"], c8["y"], c8["z"]], dtype=float)
    p_o7 = np.array([o7["x"], o7["y"], o7["z"]], dtype=float)

    bond_len = np.linalg.norm(np.array([h7["x"], h7["y"], h7["z"]], dtype=float) - p_c7)
    if bond_len < 1e-12:
        bond_len = 1.09

    v1 = p_c1 - p_c7
    v2 = p_c8 - p_c7
    v3 = p_o7 - p_c7
    norms = [np.linalg.norm(v) for v in (v1, v2, v3)]
    if min(norms) < 1e-12:
        return

    direction = -(v1 / norms[0] + v2 / norms[1] + v3 / norms[2])
    nd = np.linalg.norm(direction)
    if nd < 1e-12:
        return

    p_h7 = p_c7 + bond_len * direction / nd
    h7["x"], h7["y"], h7["z"] = float(p_h7[0]), float(p_h7[1]), float(p_h7[2])


def _reorient_h7_on_hydroxylated_residues(residue_blocks: List[Tuple[int, List[Dict], str]]) -> None:
    for _, atoms, _ in residue_blocks:
        _set_h7_position_from_neighbors(atoms)


def _set_h8_position_from_neighbors(current_atoms: List[Dict], next_atoms: List[Dict]) -> None:
    c8 = _find_atom(current_atoms, "C8")
    c7 = _find_atom(current_atoms, "C7")
    c9 = _find_atom(current_atoms, "C9")
    o4n = _find_atom(next_atoms, "O4")
    h8 = _find_atom(current_atoms, "H8")

    if c8 is None or c7 is None or c9 is None or o4n is None or h8 is None:
        return

    p_c8 = np.array([c8["x"], c8["y"], c8["z"]], dtype=float)
    p_c7 = np.array([c7["x"], c7["y"], c7["z"]], dtype=float)
    p_c9 = np.array([c9["x"], c9["y"], c9["z"]], dtype=float)
    p_o4n = np.array([o4n["x"], o4n["y"], o4n["z"]], dtype=float)

    bond_len = np.linalg.norm(np.array([h8["x"], h8["y"], h8["z"]], dtype=float) - p_c8)
    if bond_len < 1e-12:
        bond_len = 1.09

    v1 = p_c7 - p_c8
    v2 = p_c9 - p_c8
    v3 = p_o4n - p_c8
    norms = [np.linalg.norm(v) for v in (v1, v2, v3)]
    if min(norms) < 1e-12:
        return

    direction = -(v1 / norms[0] + v2 / norms[1] + v3 / norms[2])
    nd = np.linalg.norm(direction)
    if nd < 1e-12:
        return

    p_h8 = p_c8 + bond_len * direction / nd
    h8["x"], h8["y"], h8["z"] = float(p_h8[0]), float(p_h8[1]), float(p_h8[2])


def _reorient_h8_on_linked_residues(residue_blocks: List[Tuple[int, List[Dict], str]]) -> None:
    if len(residue_blocks) < 2:
        return

    for i in range(len(residue_blocks) - 1):
        _set_h8_position_from_neighbors(residue_blocks[i][1], residue_blocks[i + 1][1])


def _copy_second_join_c8_group_to_first_join(residue_blocks: List[Tuple[int, List[Dict], str]]) -> None:
    """
    Make the first outgoing C8 group look like the second join.

    For n >= 3, residue 1 comes from guai1.pdb and residue 2 comes from the
    middle GUAI template. Their C8/C9/O9/H geometry can look slightly different,
    so the 1->2 join is made to follow the already-correct 2->3 join.
    """
    if len(residue_blocks) < 3:
        return

    first_atoms = residue_blocks[0][1]
    second_atoms = residue_blocks[1][1]

    first_c8 = _find_atom(first_atoms, "C8")
    second_c8 = _find_atom(second_atoms, "C8")
    if first_c8 is None or second_c8 is None:
        return

    p_first_c8 = np.array([first_c8["x"], first_c8["y"], first_c8["z"]], dtype=float)
    p_second_c8 = np.array([second_c8["x"], second_c8["y"], second_c8["z"]], dtype=float)

    atoms_to_copy = ["C9", "O9", "HO9", "H91", "H92", "H8"]

    for atom_name in atoms_to_copy:
        src = _find_atom(second_atoms, atom_name)
        dst = _find_atom(first_atoms, atom_name)
        if src is None or dst is None:
            continue

        p_src = np.array([src["x"], src["y"], src["z"]], dtype=float)
        p_new = p_first_c8 + (p_src - p_second_c8)
        dst["x"], dst["y"], dst["z"] = float(p_new[0]), float(p_new[1]), float(p_new[2])


def _copy_second_join_c7_oh_to_first_join(residue_blocks: List[Tuple[int, List[Dict], str]]) -> None:
    """
    Add/copy the missing C7 join group on the first GUAI join.

    guai1.pdb has the terminal H7 orientation, while the middle GUAI template
    has the correct linked-chain H7 orientation. O7/HO7/H7 are copied relative
    to C7; the ring and O4-C8 chain connection are not moved.
    """
    if len(residue_blocks) < 3:
        return

    first_atoms = residue_blocks[0][1]
    second_atoms = residue_blocks[1][1]

    first_c7 = _find_atom(first_atoms, "C7")
    second_c7 = _find_atom(second_atoms, "C7")
    if first_c7 is None or second_c7 is None:
        return

    p_first_c7 = np.array([first_c7["x"], first_c7["y"], first_c7["z"]], dtype=float)
    p_second_c7 = np.array([second_c7["x"], second_c7["y"], second_c7["z"]], dtype=float)

    for atom_name in ("O7", "HO7", "H7"):
        src = _find_atom(second_atoms, atom_name)
        if src is None:
            continue

        p_src = np.array([src["x"], src["y"], src["z"]], dtype=float)
        p_new = p_first_c7 + (p_src - p_second_c7)

        dst = _find_atom(first_atoms, atom_name)
        if dst is None:
            dst = dict(src)
            dst["res"] = first_c7.get("res", src.get("res", RESNAME))
            first_atoms.append(dst)

        dst["x"], dst["y"], dst["z"] = float(p_new[0]), float(p_new[1]), float(p_new[2])


def _copy_first_join_from_reference_three_chain(
    residue_blocks: List[Tuple[int, List[Dict], str]],
    template_dir: Optional[str] = None,
    right_terminal_angle_deg: float = 0.0,
) -> None:
    """
    Fix the special n=2 case by using the already-correct n=3 first join
    as reference, exactly like the SYR generator logic.
    """
    if len(residue_blocks) != 2:
        return

    try:
        ref_blocks, _, _ = _build_guai_chain(3, template_dir=template_dir)
        _orient_chain_horizontal(ref_blocks)
        _rotate_right_terminal_only(ref_blocks, angle_deg=right_terminal_angle_deg)
        _reorient_h8_on_linked_residues(ref_blocks)
        _copy_second_join_c8_group_to_first_join(ref_blocks)
        _copy_second_join_c7_oh_to_first_join(ref_blocks)
    except Exception:
        return

    dst_atoms = residue_blocks[0][1]
    ref_atoms = ref_blocks[0][1]

    dst_c8 = _find_atom(dst_atoms, "C8")
    ref_c8 = _find_atom(ref_atoms, "C8")
    if dst_c8 is not None and ref_c8 is not None:
        p_dst_c8 = np.array([dst_c8["x"], dst_c8["y"], dst_c8["z"]], dtype=float)
        p_ref_c8 = np.array([ref_c8["x"], ref_c8["y"], ref_c8["z"]], dtype=float)

        for atom_name in ("C9", "O9", "HO9", "H91", "H92", "H8"):
            src = _find_atom(ref_atoms, atom_name)
            dst = _find_atom(dst_atoms, atom_name)
            if src is None or dst is None:
                continue
            p_src = np.array([src["x"], src["y"], src["z"]], dtype=float)
            p_new = p_dst_c8 + (p_src - p_ref_c8)
            dst["x"], dst["y"], dst["z"] = float(p_new[0]), float(p_new[1]), float(p_new[2])

    dst_c7 = _find_atom(dst_atoms, "C7")
    ref_c7 = _find_atom(ref_atoms, "C7")
    if dst_c7 is not None and ref_c7 is not None:
        p_dst_c7 = np.array([dst_c7["x"], dst_c7["y"], dst_c7["z"]], dtype=float)
        p_ref_c7 = np.array([ref_c7["x"], ref_c7["y"], ref_c7["z"]], dtype=float)

        for atom_name in ("O7", "HO7", "H7"):
            src = _find_atom(ref_atoms, atom_name)
            if src is None:
                continue
            p_src = np.array([src["x"], src["y"], src["z"]], dtype=float)
            p_new = p_dst_c7 + (p_src - p_ref_c7)

            dst = _find_atom(dst_atoms, atom_name)
            if dst is None:
                dst = dict(src)
                dst["res"] = dst_c7.get("res", src.get("res", RESNAME))
                dst_atoms.append(dst)
            dst["x"], dst["y"], dst["z"] = float(p_new[0]), float(p_new[1]), float(p_new[2])


def _rotate_right_terminal_only(residue_blocks: List[Tuple[int, List[Dict], str]], angle_deg: float) -> None:
    if abs(angle_deg) < 1e-12 or len(residue_blocks) < 2:
        return

    prev_atoms = residue_blocks[-2][1]
    last_atoms = residue_blocks[-1][1]
    prev_c8 = _find_atom(prev_atoms, "C8")
    last_o4 = _find_atom(last_atoms, "O4")
    if prev_c8 is None or last_o4 is None:
        return

    a0 = np.array([last_o4["x"], last_o4["y"], last_o4["z"]], dtype=float)
    a1 = np.array([prev_c8["x"], prev_c8["y"], prev_c8["z"]], dtype=float)
    axis = a1 - a0
    if np.linalg.norm(axis) < 1e-12:
        return

    for a in last_atoms:
        p = np.array([a["x"], a["y"], a["z"]], dtype=float)
        p2 = _rotate_point_around_axis(p, a0, axis, angle_deg)
        a["x"], a["y"], a["z"] = float(p2[0]), float(p2[1]), float(p2[2])


def _build_guai_chain(n: int, template_dir: Optional[str] = None) -> Tuple[List[Tuple[int, List[Dict], str]], List[str], str]:
    left_block, middle_block, right_block, template_label = _get_template_blocks(template_dir)

    if n == 1:
        # Exact GUAI monomer: keep the first block from guai1.pdb unchanged.
        return [(1, _deepcopy_atoms(left_block), "SINGLE")], ["SINGLE"], template_label

    left_map = _atom_dict_from_list(left_block)
    target_o4, target_basis = _frame_from_atoms(left_map)
    ex = target_basis[:, 0]

    residue_blocks: List[Tuple[int, List[Dict], str]] = []
    kinds: List[str] = []

    current_atoms = _deepcopy_atoms(left_block)
    residue_blocks.append((1, current_atoms, "CAP"))
    kinds.append("CAP")

    for resseq in range(2, n + 1):
        prev_c8 = _find_atom(current_atoms, "C8")
        if prev_c8 is None:
            raise ValueError(f"Previous GUAI residue {resseq - 1} is missing C8, cannot continue chain.")

        target_o4 = np.array([prev_c8["x"], prev_c8["y"], prev_c8["z"]], dtype=float) + ex * C8_O4_BOND
        source_block = right_block if resseq == n else middle_block
        kind = "TEMPLATE_END" if resseq == n else "MID"
        current_atoms = _transform_block_to_frame(source_block, target_o4, target_basis)
        residue_blocks.append((resseq, current_atoms, kind))
        kinds.append(kind)

    return residue_blocks, kinds, template_label


def generate_guai(
    n: int,
    out_pdb: str,
    template_dir: Optional[str] = None,
    write_conect: bool = False,
    make_horizontal: bool = True,
    right_terminal_angle_deg: float = 0.0,
    initial_view_angle_deg: float = -280.0,
) -> None:
    if n <= 0:
        raise ValueError("n must be >= 1")

    residue_blocks, kinds, template_label = _build_guai_chain(n, template_dir=template_dir)

    if make_horizontal:
        _orient_chain_horizontal(residue_blocks)

    if n >= 2:
        _rotate_right_terminal_only(residue_blocks, angle_deg=right_terminal_angle_deg)
        _reorient_h8_on_linked_residues(residue_blocks)

    # Same visual-join correction style as SYR: keep the first guai1.pdb block,
    # then make the first join match the already-correct middle joins.
    _copy_second_join_c8_group_to_first_join(residue_blocks)
    _copy_second_join_c7_oh_to_first_join(residue_blocks)
    _copy_first_join_from_reference_three_chain(
        residue_blocks,
        template_dir=template_dir,
        right_terminal_angle_deg=right_terminal_angle_deg,
    )

    # Do not recalculate H7/H8 manually here: their orientation is taken from
    # guai4 after frame alignment, which preserves the template join geometry.

    if make_horizontal:
        _rotate_chain_view_around_horizontal_axis(residue_blocks, initial_view_angle_deg)

    serial = 1
    atom_index: List[Tuple[int, int, str]] = []
    out_lines = [
        "REMARK  READ PDB, MANIPULATE STRUCTURE IF NEEDED, AND GENERATE TOPOLOGY FILE",
        f"REMARK  Polymer: {POLYMER_LABEL} | n residues (n= {n})",
        "REMARK  CREATED BY: adaptdelivery.org",
    ]

    for resseq, atomsR, _ in residue_blocks:
        for a in atomsR:
            out_lines.append(_format_pdb_line(serial, a, resseq))
            atom_index.append((serial, resseq, a["atom"].strip()))
            serial += 1

    if write_conect:
        out_lines.extend(_build_conect(atom_index, kinds))

    out_lines.append(f"TER   {serial:5d}      GUAI  {n:4d}")
    out_lines.append("END")

    out_path = Path(out_pdb)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out_lines) + "\n")


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent

    generate_guai(1, str(out_dir / "GUAI_template_1.pdb"), write_conect=False)
    generate_guai(2, str(out_dir / "GUAI_template_2.pdb"), write_conect=False)
    generate_guai(3, str(out_dir / "GUAI_template_3.pdb"), write_conect=False)
    generate_guai(4, str(out_dir / "GUAI_template_4.pdb"), write_conect=False)
    generate_guai(10, str(out_dir / "GUAI_template_10.pdb"), write_conect=False)
