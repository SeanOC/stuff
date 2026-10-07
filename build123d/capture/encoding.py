"""Dependency-free CB2 wire contract: v1;X,Y;…;X,Y, explicit closure, mm."""
from __future__ import annotations

import math
import re

MAX_VERTICES = 256  # distinct ring vertices; closing copy is not counted
MAX_BYTES = 16 * 1024
_NUMBER = re.compile(r"-?(?:0|[1-9]\d*)(?:\.\d{1,2})?\Z")


def validate(points):
    """Return a closed simple ring; require a <=252 mm bounding box.

    Translation is allowed: CB2 can translate the bounding box into its bin.
    Winding is preserved. Holes and multiple rings are deliberately unsupported.
    """
    try:
        p = [tuple(float(v) for v in xy) for xy in points]
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError('coordinates must be finite pairs') from exc
    if not 4 <= len(p) <= MAX_VERTICES + 1:
        raise ValueError('requires 3..256 vertices plus closing copy')
    if any(len(xy) != 2 or not all(math.isfinite(v) for v in xy) for xy in p):
        raise ValueError('coordinates must be finite pairs')
    if p[0] != p[-1]:
        raise ValueError('ring must be explicitly closed')
    if len(set(p[:-1])) != len(p) - 1:
        raise ValueError('repeated vertex')
    # Bound magnitudes as well as span, preventing overflow in area/intersections.
    if any(abs(v) > 1e6 for xy in p for v in xy):
        raise ValueError('coordinate magnitude exceeds 1000000 mm')
    for axis in (0, 1):
        if max(xy[axis] for xy in p) - min(xy[axis] for xy in p) > 252:
            raise ValueError('footprint must fit 6x6 cells (252x252 mm)')

    def cross(a, b, c):
        return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])

    def on(a, b, c):
        return cross(a, b, c) == 0 and all(min(a[k], b[k]) <= c[k] <= max(a[k], b[k]) for k in (0, 1))

    for i, (a, b) in enumerate(zip(p, p[1:])):
        # Adjacent edges may share one endpoint, but may not double back.
        c = p[(i+2) % (len(p)-1)]
        if cross(a, b, c) == 0 and (on(a, b, c) or on(b, c, a)):
            raise ValueError('overlapping adjacent edges')
        for j in range(i+2, len(p)-1):
            if i == 0 and j == len(p)-2:
                continue
            c, d = p[j:j+2]
            if (cross(a,b,c)*cross(a,b,d) < 0 and cross(c,d,a)*cross(c,d,b) < 0) or any((on(a,b,c), on(a,b,d), on(c,d,a), on(c,d,b))):
                raise ValueError('ring must be simple (no crossings or touches)')
    area = abs(sum(a[0]*b[1]-a[1]*b[0] for a, b in zip(p, p[1:]))) / 2
    if area < 25:
        raise ValueError('area must be at least 25 mm²')
    return p


def encode(points):
    """Quantize to 0.01 mm, then validate the actual transmitted geometry."""
    rounded = [(round(float(x), 2), round(float(y), 2)) for x, y in points]
    ring = validate(rounded)
    result = 'v1;' + ';'.join(f'{x:.2f},{y:.2f}' for x, y in ring)
    if len(result.encode('utf-8')) > MAX_BYTES:
        raise ValueError('encoding exceeds 16 KB')
    return result


def parse(value):
    if not isinstance(value, str) or len(value.encode('utf-8')) > MAX_BYTES:
        raise ValueError('encoding must be a string of at most 16 KB')
    fields = value.split(';')
    if fields[0] != 'v1':
        raise ValueError('unsupported footprint version')
    points = []
    for field in fields[1:]:
        xy = field.split(',')
        if len(xy) != 2 or not all(_NUMBER.fullmatch(v) for v in xy):
            raise ValueError('coordinates require decimal mm with <=2 decimal places')
        points.append(tuple(map(float, xy)))
    return validate(points)
