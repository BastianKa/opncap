# SPDX-License-Identifier: Apache-2.0
"""Small deterministic two-layer grid router used by gen_pcb.py.

Nodes sit on the 0.3175 mm grid defined in layout.py. Every obstacle is
written into an ownership map with its clearance already added, so a search
only has to test one integer per node. The margins are chosen so that tracks
keep at least 0.2 mm to foreign copper, while the KiCad design rule checked
afterwards is 0.15 mm.
"""
import heapq
import math

F, B = 0, 1
BLOCK = -1

TRACK_W = 0.25
POWER_W = 0.5
VIA_D = 0.6
VIA_DRILL = 0.3

PAD_THR = 0.40            # node to foreign pad copper
TRACK_THR = 0.455         # node to foreign 0.25 mm track centre line
WIDE_THR = 0.58           # node to foreign 0.5 mm track centre line
VIA_THR = 0.67            # node to foreign via centre
EDGE_THR = 0.55           # node to board edge / cut-out
HOLE_THR = 0.45           # node to edge of an unplated hole

VIA_COST = 14.0
OFF_AXIS = 1.6            # penalty for running against the layer's preferred direction


class Router:
    def __init__(self, x0, y0, g, nx, ny):
        self.x0, self.y0, self.g, self.nx, self.ny = x0, y0, g, nx, ny
        self.plane = nx * ny
        self.own = [0] * (2 * self.plane)
        self.novia = bytearray(self.plane)
        self.tracks = []      # (net, layer, x1, y1, x2, y2, width)
        self.vias = []        # (net, x, y)

    # ------------------------------------------------------------ helpers
    def xy(self, ix, iy):
        return (self.x0 + ix * self.g, self.y0 + iy * self.g)

    def cell(self, x, y):
        return (int(round((x - self.x0) / self.g)), int(round((y - self.y0) / self.g)))

    def _set(self, layer, ix, iy, net):
        if 0 <= ix < self.nx and 0 <= iy < self.ny:
            i = layer * self.plane + iy * self.nx + ix
            o = self.own[i]
            if o == 0:
                self.own[i] = net
            elif o != net:
                self.own[i] = BLOCK

    def _range(self, lo, hi, org, n):
        a = max(0, int(math.floor((lo - org) / self.g)))
        b = min(n - 1, int(math.ceil((hi - org) / self.g)))
        return range(a, b + 1)

    def mark_circle(self, layers, cx, cy, r, net):
        r2 = r * r
        for iy in self._range(cy - r, cy + r, self.y0, self.ny):
            y = self.y0 + iy * self.g
            for ix in self._range(cx - r, cx + r, self.x0, self.nx):
                x = self.x0 + ix * self.g
                if (x - cx) ** 2 + (y - cy) ** 2 < r2:
                    for layer in layers:
                        self._set(layer, ix, iy, net)

    def mark_rect(self, layers, x1, y1, x2, y2, infl, net):
        for iy in self._range(y1 - infl, y2 + infl, self.y0, self.ny):
            y = self.y0 + iy * self.g
            dy = max(y1 - y, 0.0, y - y2)
            for ix in self._range(x1 - infl, x2 + infl, self.x0, self.nx):
                x = self.x0 + ix * self.g
                dx = max(x1 - x, 0.0, x - x2)
                if dx * dx + dy * dy < infl * infl:
                    for layer in layers:
                        self._set(layer, ix, iy, net)

    def forbid_via_rect(self, x1, y1, x2, y2, infl):
        for iy in self._range(y1 - infl, y2 + infl, self.y0, self.ny):
            for ix in self._range(x1 - infl, x2 + infl, self.x0, self.nx):
                self.novia[iy * self.nx + ix] = 1

    def nodes_in_rect(self, layers, x1, y1, x2, y2):
        out = []
        for iy in self._range(y1, y2, self.y0, self.ny):
            y = self.y0 + iy * self.g
            if not (y1 <= y <= y2):
                continue
            for ix in self._range(x1, x2, self.x0, self.nx):
                x = self.x0 + ix * self.g
                if x1 <= x <= x2:
                    for layer in layers:
                        out.append(layer * self.plane + iy * self.nx + ix)
        return out

    def nodes_in_circle(self, layers, cx, cy, r):
        out = []
        for i in self.nodes_in_rect(layers, cx - r, cy - r, cx + r, cy + r):
            layer, rem = divmod(i, self.plane)
            iy, ix = divmod(rem, self.nx)
            x, y = self.xy(ix, iy)
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                out.append(i)
        return out

    # ------------------------------------------------------------ search
    def _free(self, i, net):
        o = self.own[i]
        return o == 0 or o == net

    def _wide_ok(self, i, net):
        nx = self.nx
        own = self.own
        for d in (-nx - 1, -nx, -nx + 1, -1, 1, nx - 1, nx, nx + 1):
            o = own[i + d]
            if o != 0 and o != net:
                return False
        return True

    def _via_ok(self, rem, net):
        if self.novia[rem]:
            return False
        for layer in (0, 1):
            i = layer * self.plane + rem
            if not self._free(i, net) or not self._wide_ok(i, net):
                return False
        return True

    def astar(self, net, sources, targets, tx, ty, wide, margin):
        nx, ny, plane, own = self.nx, self.ny, self.plane, self.own
        tix, tiy = self.cell(tx, ty)
        xs, ys = [tix], [tiy]
        for i in sources:
            rem = i % plane
            ys.append(rem // nx)
            xs.append(rem % nx)
        x_lo, x_hi = max(1, min(xs) - margin), min(nx - 2, max(xs) + margin)
        y_lo, y_hi = max(1, min(ys) - margin), min(ny - 2, max(ys) + margin)

        def h(ix, iy):
            dx, dy = abs(ix - tix), abs(iy - tiy)
            return (dx + dy) + (1.4142 - 2) * min(dx, dy)

        best = {}
        came = {}
        heap = []
        n = 0
        for i in sources:
            rem = i % plane
            best[i] = 0.0
            heapq.heappush(heap, (h(rem % nx, rem // nx), n, 0.0, i))
            n += 1
        moves = ((1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
                 (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142))
        via_cache = {}
        while heap:
            _, _, gi, i = heapq.heappop(heap)
            if gi > best.get(i, 1e18):
                continue
            if i in targets:
                path = [i]
                while i in came:
                    i = came[i]
                    path.append(i)
                return path[::-1]
            layer, rem = divmod(i, plane)
            iy, ix = divmod(rem, nx)
            for dx, dy, c in moves:
                jx, jy = ix + dx, iy + dy
                if jx < x_lo or jx > x_hi or jy < y_lo or jy > y_hi:
                    continue
                j = i + dx + dy * nx
                o = own[j]
                if o != 0 and o != net:
                    continue
                if wide and j not in targets and not self._wide_ok(j, net):
                    continue
                if layer == F:
                    cost = c * (OFF_AXIS if dx != 0 else 1.0)
                else:
                    cost = c * (OFF_AXIS if dy != 0 else 1.0)
                gj = gi + cost
                if gj < best.get(j, 1e18):
                    best[j] = gj
                    came[j] = i
                    heapq.heappush(heap, (gj + h(jx, jy), n, gj, j))
                    n += 1
            ok = via_cache.get(rem)
            if ok is None:
                ok = via_cache[rem] = self._via_ok(rem, net)
            if ok:
                j = rem + (1 - layer) * plane
                gj = gi + VIA_COST
                if gj < best.get(j, 1e18):
                    best[j] = gj
                    came[j] = i
                    heapq.heappush(heap, (gj + h(ix, iy), n, gj, j))
                    n += 1
        return None

    # ------------------------------------------------------------ commit
    def commit(self, net, path, wide):
        """Write a found path into the track list and the ownership map."""
        plane, nx = self.plane, self.nx
        thr = WIDE_THR if wide else TRACK_THR
        width = POWER_W if wide else TRACK_W
        pts = []
        for i in path:
            layer, rem = divmod(i, plane)
            iy, ix = divmod(rem, nx)
            pts.append((layer, ix, iy))
        run_start = 0
        for k in range(1, len(pts) + 1):
            end_run = k == len(pts) or pts[k][0] != pts[k - 1][0]
            if not end_run and k - run_start >= 2:
                a, b, c = pts[k - 2], pts[k - 1], pts[k]
                if (b[1] - a[1], b[2] - a[2]) != (c[1] - b[1], c[2] - b[2]):
                    self._emit(net, pts[run_start], pts[k - 1], width)
                    run_start = k - 1
            if end_run:
                if k - 1 > run_start:
                    self._emit(net, pts[run_start], pts[k - 1], width)
                if k < len(pts):
                    x, y = self.xy(pts[k][1], pts[k][2])
                    self.vias.append((net, x, y))
                    self.mark_circle((F, B), x, y, VIA_THR, net)
                run_start = k
        for k, (layer, ix, iy) in enumerate(pts):
            x, y = self.xy(ix, iy)
            self.mark_circle((layer,), x, y, thr, net)
            if k and pts[k - 1][0] == layer:
                px, py = self.xy(pts[k - 1][1], pts[k - 1][2])
                self.mark_circle((layer,), (x + px) / 2, (y + py) / 2, thr, net)

    def _emit(self, net, a, b, width):
        x1, y1 = self.xy(a[1], a[2])
        x2, y2 = self.xy(b[1], b[2])
        self.tracks.append((net, a[0], x1, y1, x2, y2, width))
