#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Linear PEI (EIMI) PDB generator - NO TEMPLATE at runtime.

Built from a 490-mer template by extracting:
  - Left cap residue geometry (res 1) including terminal HN2 on N1
  - Two alternating internal repeat geometries (A=res2, B=res3)
  - Two alternating translation steps between N1 anchors: A->B and B->A
and writing PDB + CONECT so VMD draws bonds consistently.

Features:
  - No template file is read at runtime (everything is hardcoded below)
  - Supports n=1, small n, large n (1000+)
  - Adds right terminal H22 on C2 so it continues chain direction:
        direction ~ (N1_last + step_to_next) - C2_last
  - make_horizontal=True applies rigid rotations only (no distortion)
    to make the chain visually horizontal in VMD.

Usage (IDLE):
  - Open this file, press F5
  - It will write PEI_1.pdb, PEI_10.pdb, PEI_490.pdb (edit bottom to change)
"""

from __future__ import annotations
from typing import Dict, List, Tuple, Optional
import numpy as np

POLYMER_LABEL = "PEI"

# ---------- Hardcoded geometry (relative to N1 anchor of each residue) ----------

# Left-cap residue (res 1) includes terminal HN2 on N1
CAP_L: List[Dict] = [{'record': 'ATOM', 'atom': ' N1 ', 'res': ' EIMI', 'tail': '  1.00  0.00      P1  ', 'dx': 0.0, 'dy': 0.0, 'dz': 0.0}, {'record': 'ATOM', 'atom': ' HN1', 'res': ' EIMI', 'tail': '  1.00  0.00      P1  ', 'dx': -0.027, 'dy': -1.019, 'dz': 0.113}, {'record': 'ATOM', 'atom': ' C1 ', 'res': ' EIMI', 'tail': '  1.00  0.00      P1  ', 'dx': 1.381, 'dy': 0.543, 'dz': 0.548}, {'record': 'ATOM', 'atom': ' HN2', 'res': ' EIMI', 'tail': '  1.00  0.00      P1  ', 'dx': -0.598, 'dy': 0.798, 'dz': -0.339}, {'record': 'ATOM', 'atom': ' H11', 'res': ' EIMI', 'tail': '  1.00  0.00      P1  ', 'dx': 1.869, 'dy': 1.205, 'dz': -0.26}, {'record': 'ATOM', 'atom': ' H13', 'res': ' EIMI', 'tail': '  1.00  0.00      P1  ', 'dx': 1.183, 'dy': 1.189, 'dz': 1.487}, {'record': 'ATOM', 'atom': ' C2 ', 'res': ' EIMI', 'tail': '  1.00  0.00      P1  ', 'dx': 2.455, 'dy': -0.678, 'dz': 0.978}, {'record': 'ATOM', 'atom': ' H21', 'res': ' EIMI', 'tail': '  1.00  0.00      P1  ', 'dx': 2.661, 'dy': -1.312, 'dz': 0.033}, {'record': 'ATOM', 'atom': ' H23', 'res': ' EIMI', 'tail': '  1.00  0.00      P1  ', 'dx': 1.947, 'dy': -1.35, 'dz': 1.768}]

# Internal repeat A (res 2, 4, 6, ...)
UNIT_A: List[Dict] = [{'record': 'ATOM', 'atom': ' N1 ', 'res': ' EIMI', 'tail': '  1.00  0.00      P1  ', 'dx': 0.0, 'dy': 0.0, 'dz': 0.0}, {'record': 'ATOM', 'atom': ' HN1', 'res': ' EIMI', 'tail': '  1.00  0.00      P1  ', 'dx': -0.02, 'dy': 1.024, 'dz': 0.052}, {'record': 'ATOM', 'atom': ' C1 ', 'res': ' EIMI', 'tail': '  1.00  0.00      P1  ', 'dx': 1.385, 'dy': -0.472, 'dz': -0.608}, {'record': 'ATOM', 'atom': ' H11', 'res': ' EIMI', 'tail': '  1.00  0.00      P1  ', 'dx': 1.935, 'dy': -1.114, 'dz': 0.178}, {'record': 'ATOM', 'atom': ' H13', 'res': ' EIMI', 'tail': '  1.00  0.00      P1  ', 'dx': 1.178, 'dy': -1.127, 'dz': -1.539}, {'record': 'ATOM', 'atom': ' C2 ', 'res': ' EIMI', 'tail': '  1.00  0.00      P1  ', 'dx': 2.393, 'dy': 0.789, 'dz': -1.082}, {'record': 'ATOM', 'atom': ' H21', 'res': ' EIMI', 'tail': '  1.00  0.00      P1  ', 'dx': 2.598, 'dy': 1.442, 'dz': -0.149}, {'record': 'ATOM', 'atom': ' H23', 'res': ' EIMI', 'tail': '  1.00  0.00      P1  ', 'dx': 1.833, 'dy': 1.43, 'dz': -1.862}]

# Internal repeat B (res 3, 5, 7, ...)
UNIT_B: List[Dict] = [{'record': 'ATOM', 'atom': ' N1 ', 'res': ' EIMI', 'tail': '  1.00  0.00      P1  ', 'dx': 0.0, 'dy': 0.0, 'dz': 0.0}, {'record': 'ATOM', 'atom': ' HN1', 'res': ' EIMI', 'tail': '  1.00  0.00      P1  ', 'dx': -0.016, 'dy': -1.008, 'dz': -0.19}, {'record': 'ATOM', 'atom': ' C1 ', 'res': ' EIMI', 'tail': '  1.00  0.00      P1  ', 'dx': 1.388, 'dy': 0.415, 'dz': 0.643}, {'record': 'ATOM', 'atom': ' H11', 'res': ' EIMI', 'tail': '  1.00  0.00      P1  ', 'dx': 1.982, 'dy': 1.033, 'dz': -0.13}, {'record': 'ATOM', 'atom': ' H13', 'res': ' EIMI', 'tail': '  1.00  0.00      P1  ', 'dx': 1.182, 'dy': 1.081, 'dz': 1.567}, {'record': 'ATOM', 'atom': ' C2 ', 'res': ' EIMI', 'tail': '  1.00  0.00      P1  ', 'dx': 2.343, 'dy': -0.876, 'dz': 1.149}, {'record': 'ATOM', 'atom': ' H21', 'res': ' EIMI', 'tail': '  1.00  0.00      P1  ', 'dx': 2.542, 'dy': -1.545, 'dz': 0.225}, {'record': 'ATOM', 'atom': ' H23', 'res': ' EIMI', 'tail': '  1.00  0.00      P1  ', 'dx': 1.744, 'dy': -1.49, 'dz': 1.922}]

# Translation of N1 anchor from residue 1 -> residue 2 (cap -> A)
DELTA_12 = np.array([3.83, -0.157, 1.56], dtype=float)

# Alternating translations of N1 anchor
DELTA_AB = np.array([3.78, 0.333, -1.699], dtype=float)  # A -> B
DELTA_BA = np.array([3.736, -0.474, 1.79], dtype=float)  # B -> A

# Terminal bond length (Å) from template: C2 - H22
H22_BONDLEN = 1.140327146042


# ---------- Helpers ----------

def _place_block(block: List[Dict], anchor_xyz: Tuple[float, float, float]) -> List[Dict]:
    ax, ay, az = anchor_xyz
    out = []
    for b in block:
        out.append({
            "record": b["record"],
            "atom": b["atom"],     # keep 4-char field
            "res":  b["res"],      # keep 5-char field
            "tail": b["tail"],
            "x": float(ax + b["dx"]),
            "y": float(ay + b["dy"]),
            "z": float(az + b["dz"]),
        })
    return out


def _find_atom(atoms: List[Dict], atom_name: str) -> Optional[Dict]:
    atom_name = atom_name.strip().upper()
    for a in atoms:
        if a["atom"].strip().upper() == atom_name:
            return a
    return None


def _format_pdb_line(serial: int, atom: Dict, resseq: int) -> str:
    # IMPORTANT: fixed-column PDB formatting so VMD doesn't mis-parse large coordinates
    record = (atom.get("record") or "ATOM").ljust(6)[:6]
    atom_field = atom["atom"].ljust(4)[:4]
    res_field  = atom["res"].ljust(5)[:5]
    tail = atom.get("tail", "").rstrip()
    return (
        f"{record}{serial:5d} {atom_field}{res_field}{resseq:4d}"
        f"     {atom['x']:8.3f}{atom['y']:8.3f}{atom['z']:8.3f}"
        f"{tail}"
    )


# ---------- Terminal atom (right cap) ----------

def _add_right_terminal_h22(residue_blocks: List[Tuple[int, List[Dict], str]]) -> None:
    """
    Add terminal H22 on the last residue so it continues the chain.
    Inter-residue bond is C2(i) - N1(i+1).
    Forward direction at end:
        d = (N1_last + step_to_next) - C2_last
    """
    if not residue_blocks:
        return
    last_resseq, last_atoms, last_kind = residue_blocks[-1]
    if _find_atom(last_atoms, "H22") is not None:
        return

    c2 = _find_atom(last_atoms, "C2")
    n1 = _find_atom(last_atoms, "N1")
    if c2 is None or n1 is None:
        return

    c2_xyz = np.array([c2["x"], c2["y"], c2["z"]], dtype=float)
    n1_xyz = np.array([n1["x"], n1["y"], n1["z"]], dtype=float)

    if last_kind == "CAP":
        step = DELTA_12
    elif last_kind == "A":
        step = DELTA_AB
    else:
        step = DELTA_BA

    d = (n1_xyz + step) - c2_xyz
    nd = float(np.linalg.norm(d))
    if nd == 0:
        d = np.array([1.0, 0.0, 0.0], dtype=float)
        nd = 1.0
    d = d / nd

    h_pos = c2_xyz + H22_BONDLEN * d
    # Tail + res name copied from residue atoms (keeps occupancy/B-factor/segid format)
    last_atoms.append({
        "record": "ATOM",
        "atom": " H22",
        "res": last_atoms[0]["res"],
        "tail": last_atoms[0]["tail"],
        "x": float(h_pos[0]),
        "y": float(h_pos[1]),
        "z": float(h_pos[2]),
    })


# ---------- Rigid alignment (same style as PEO/PE) ----------

def rigid_align_smoothed_end_to_x(residue_blocks: List[Tuple[int, List[Dict], str]], m: int = 5) -> None:
    if len(residue_blocks) < 2:
        return

    pts = []
    for _, atoms, _ in residue_blocks:
        a = _find_atom(atoms, "C2") or _find_atom(atoms, "N1")
        if a is not None:
            pts.append(np.array([a["x"], a["y"], a["z"]], dtype=float))
    if len(pts) < 2:
        return

    m = int(max(1, min(m, len(pts)//2 if len(pts) >= 2 else 1)))
    p0 = np.mean(pts[:m], axis=0)
    p1 = np.mean(pts[-m:], axis=0)

    v = p1 - p0
    nv = float(np.linalg.norm(v))
    if nv == 0:
        return
    v = v / nv
    x_axis = np.array([1.0, 0.0, 0.0], dtype=float)

    k = np.cross(v, x_axis)
    s = float(np.linalg.norm(k))
    c = float(np.dot(v, x_axis))

    if s == 0:
        if c > 0:
            R = np.eye(3, dtype=float)
        else:
            tmp = np.array([0.0, 1.0, 0.0], dtype=float)
            if abs(v[1]) > 0.9:
                tmp = np.array([0.0, 0.0, 1.0], dtype=float)
            axis = np.cross(v, tmp)
            axis = axis / np.linalg.norm(axis)
            K = np.array([[0, -axis[2], axis[1]],
                          [axis[2], 0, -axis[0]],
                          [-axis[1], axis[0], 0]], dtype=float)
            R = np.eye(3) + 2.0 * (K @ K)
    else:
        k = k / s
        K = np.array([[0, -k[2], k[1]],
                      [k[2], 0, -k[0]],
                      [-k[1], k[0], 0]], dtype=float)
        R = np.eye(3) + K * s + (K @ K) * (1.0 - c)

    for _, atoms, _ in residue_blocks:
        for a in atoms:
            p = np.array([a["x"], a["y"], a["z"]], dtype=float) - p0
            p2 = R @ p
            a["x"], a["y"], a["z"] = float(p2[0] + p0[0]), float(p2[1] + p0[1]), float(p2[2] + p0[2])


def rigid_flatten_backbone_to_x(residue_blocks: List[Tuple[int, List[Dict], str]], m: int = 5) -> None:
    if len(residue_blocks) < 2:
        return

    pts = []
    for _, atoms, _ in residue_blocks:
        a = _find_atom(atoms, "C2") or _find_atom(atoms, "N1")
        if a is not None:
            pts.append(np.array([a["x"], a["y"], a["z"]], dtype=float))
    if len(pts) < 2:
        return

    m = int(max(1, min(m, len(pts)//2 if len(pts) >= 2 else 1)))
    p0 = np.mean(pts[:m], axis=0)
    p1 = np.mean(pts[-m:], axis=0)

    v = p1 - p0
    nv = float(np.linalg.norm(v))
    if nv == 0:
        return
    v = v / nv

    yaw = float(np.arctan2(v[1], v[0]))
    cy, sy = float(np.cos(-yaw)), float(np.sin(-yaw))
    Rz = np.array([[cy, -sy, 0.0],
                   [sy,  cy, 0.0],
                   [0.0, 0.0, 1.0]], dtype=float)

    v1 = Rz @ v
    pitch = float(np.arctan2(v1[2], v1[0]))
    cp, sp = float(np.cos(-pitch)), float(np.sin(-pitch))
    Ry = np.array([[ cp, 0.0, sp],
                   [0.0, 1.0, 0.0],
                   [-sp, 0.0, cp]], dtype=float)

    R = Ry @ Rz

    for _, atoms, _ in residue_blocks:
        for a in atoms:
            p = np.array([a["x"], a["y"], a["z"]], dtype=float) - p0
            p2 = R @ p
            a["x"], a["y"], a["z"] = float(p2[0] + p0[0]), float(p2[1] + p0[1]), float(p2[2] + p0[2])

    # center Y/Z around 0 using N1 anchors
    anchors = []
    for _, atoms, _ in residue_blocks:
        a = _find_atom(atoms, "N1")
        if a is not None:
            anchors.append([a["y"], a["z"]])
    if anchors:
        yz = np.mean(np.array(anchors, dtype=float), axis=0)
        dy, dz = float(yz[0]), float(yz[1])
        for _, atoms, _ in residue_blocks:
            for a in atoms:
                a["y"] = float(a["y"] - dy)
                a["z"] = float(a["z"] - dz)


# ---------- CONECT ----------

def _build_conect(atom_index: List[Tuple[int, int, str]]) -> List[str]:
    by_res = {}
    for serial, resseq, aname in atom_index:
        by_res.setdefault(resseq, {})[aname] = serial

    bonds = []

    def add_bond(a: int, b: int):
        if a <= 0 or b <= 0 or a == b:
            return
        bonds.append((min(a, b), max(a, b)))

    for resseq, amap in by_res.items():
        n1 = amap.get("N1", 0)
        c1 = amap.get("C1", 0)
        c2 = amap.get("C2", 0)

        add_bond(n1, c1)
        add_bond(c1, c2)

        for h in ("HN1", "HN2"):
            if h in amap:
                add_bond(n1, amap[h])

        for h in ("H11", "H13"):
            if h in amap:
                add_bond(c1, amap[h])

        for h in ("H21", "H23", "H22"):
            if h in amap:
                add_bond(c2, amap[h])

        # inter-residue: C2(i) - N1(i+1)
        if (resseq + 1) in by_res:
            n1n = by_res[resseq + 1].get("N1", 0)
            if c2 and n1n:
                add_bond(c2, n1n)

    bonds = sorted(set(bonds))
    grouped = {}
    for a, b in bonds:
        grouped.setdefault(a, []).append(b)

    lines = []
    for a in sorted(grouped.keys()):
        partners = grouped[a]
        for i in range(0, len(partners), 4):
            chunk = partners[i:i+4]
            lines.append("CONECT" + f"{a:5d}" + "".join(f"{p:5d}" for p in chunk))
    return lines


# ---------- Main ----------

def generate_pei(n: int, out_pdb: str, make_horizontal: bool = True) -> None:
    if n <= 0:
        raise ValueError("n must be >= 1")

    residue_blocks: List[Tuple[int, List[Dict], str]] = []

    anchor = np.array([0.0, 0.0, 0.0], dtype=float)
    residue_blocks.append((1, _place_block(CAP_L, (float(anchor[0]), float(anchor[1]), float(anchor[2]))), "CAP"))

    if n >= 2:
        anchor = anchor + DELTA_12
        residue_blocks.append((2, _place_block(UNIT_A, (float(anchor[0]), float(anchor[1]), float(anchor[2]))), "A"))

    kind = "A"  # residue 2 kind
    for resseq in range(3, n + 1):
        if kind == "A":
            anchor = anchor + DELTA_AB
            kind = "B"
            block = UNIT_B
        else:
            anchor = anchor + DELTA_BA
            kind = "A"
            block = UNIT_A
        residue_blocks.append((resseq, _place_block(block, (float(anchor[0]), float(anchor[1]), float(anchor[2]))), kind))

    _add_right_terminal_h22(residue_blocks)

    if make_horizontal:
        rigid_align_smoothed_end_to_x(residue_blocks, m=5)
        rigid_flatten_backbone_to_x(residue_blocks, m=5)

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

    #out_lines.extend(_build_conect(atom_index))
    ter_serial = serial  # serial este deja "urmatorul" dupa ultimul atom
    ter_resname = residue_blocks[-1][1][0]["res"].strip()  # ex: EIMI
    ter_resid = n
    out_lines.append(f"TER   {ter_serial:5d}      {ter_resname:>4s} {ter_resid:4d}")
    out_lines.append("END")

    with open(out_pdb, "w", encoding="utf-8") as f:
        f.write("\n".join(out_lines) + "\n")


if __name__ == "__main__":
    generate_pei(490, "PEI_490.pdb", make_horizontal=True)
