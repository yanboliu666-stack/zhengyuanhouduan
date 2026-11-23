import * as T from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import { arms, type XY } from "./site";
import type { Lamp } from "../desk/feed";
const clamp = T.MathUtils.clamp;
export function buildModel(
  host: HTMLElement,
  onProject: (
    p: { x: number; y: number; visible: boolean }[],
    north: number,
  ) => void,
) {
  const scene = new T.Scene();
  scene.background = new T.Color("#213e49");
  scene.fog = new T.FogExp2("#24434e", 0.0016);
  const renderer = new T.WebGLRenderer({
    antialias: true,
    preserveDrawingBuffer: true,
    alpha: false,
    powerPreference: "low-power",
  });
  host.appendChild(renderer.domElement);
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.7));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = T.PCFSoftShadowMap;
  renderer.outputColorSpace = T.SRGBColorSpace;
  const camera = new T.PerspectiveCamera(38, 1, 0.5, 900),
    controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.13;
  controls.enablePan = false;
  controls.minDistance = 100;
  controls.maxDistance = 410;
  controls.minPolarAngle = 0.08;
  controls.maxPolarAngle = 1.11;
  controls.rotateSpeed = 0.65;
  scene.add(new T.HemisphereLight("#fff4da", "#aac7c1", 1.95));
  const sun = new T.DirectionalLight("#fff1d4", 2.45);
  sun.position.set(-86, 140, 45);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  Object.assign(sun.shadow.camera, {
    left: -136,
    right: 136,
    top: 120,
    bottom: -120,
    near: 5,
    far: 380,
  });
  sun.shadow.bias = -0.0006;
  sun.shadow.normalBias = 0.13;
  scene.add(sun);
  const mats = new Map<string, T.MeshStandardMaterial>(),
    batch = new Map<string, T.BufferGeometry[]>();
  function mat(c: string) {
    if (!mats.has(c))
      mats.set(
        c,
        new T.MeshStandardMaterial({
          color: c,
          roughness: 0.88,
          side: T.DoubleSide,
        }),
      );
    return mats.get(c)!;
  }
  function add(g: T.BufferGeometry, c: string, x = 0, y = 0, z = 0, ry = 0) {
    g.rotateY(ry);
    g.translate(x, y, z);
    let f = g;
    if (g.index) {
      f = g.toNonIndexed();
      g.dispose();
    }
    f.deleteAttribute("uv");
    if (!batch.has(c)) batch.set(c, []);
    batch.get(c)!.push(f);
  }
  function box(
    x: number,
    y: number,
    z: number,
    w: number,
    h: number,
    d: number,
    c: string,
    r = 0,
  ) {
    add(new T.BoxGeometry(w, h, d), c, x, y, z, r);
  }
  function pole(
    x: number,
    y: number,
    z: number,
    r: number,
    h: number,
    c: string,
  ) {
    add(new T.CylinderGeometry(r, r, h, 8), c, x, y, z);
  }
  function patch(poly: XY[], y: number, c: string) {
    const sh = new T.Shape(poly.map((v) => new T.Vector2(v[0], -v[1])));
    const g = new T.ShapeGeometry(sh);
    g.rotateX(-Math.PI / 2);
    add(g, c, 0, y, 0);
  }
  function ribbon(pts: XY[], width: number, y: number, c: string, offset = 0) {
    const left: XY[] = [],
      right: XY[] = [];
    pts.forEach(([x, z], i) => {
      const a = pts[Math.max(0, i - 1)]!,
        b = pts[Math.min(pts.length - 1, i + 1)]!,
        dx = b[0] - a[0],
        dz = b[1] - a[1],
        len = Math.hypot(dx, dz);
      left.push([
        x - (dz / len) * (offset - width / 2),
        z + (dx / len) * (offset - width / 2),
      ]);
      right.push([
        x - (dz / len) * (offset + width / 2),
        z + (dx / len) * (offset + width / 2),
      ]);
    });
    patch([...left, ...right.reverse()], y, c);
  }
  function sample(pts: XY[], dist: number, off = 0) {
    for (let i = 1; i < pts.length; i++) {
      const a = pts[i - 1]!,
        b = pts[i]!,
        dx = b[0] - a[0],
        dz = b[1] - a[1],
        l = Math.hypot(dx, dz);
      if (dist <= l || i === pts.length - 1) {
        const t = Math.min(dist, l) / l;
        return {
          x: a[0] + dx * t - (dz / l) * off,
          z: a[1] + dz * t + (dx / l) * off,
          r: Math.atan2(dx, dz),
        };
      }
      dist -= l;
    }
    return { x: 0, z: 0, r: 0 };
  }
  function mark(
    pts: XY[],
    d: number,
    off: number,
    w: number,
    len: number,
    y: number,
    c: string,
  ) {
    const p = sample(pts, d, off);
    box(p.x, y, p.z, w, 0.055, len, c, p.r);
  }
  // Clay terrain cutaway, with a watercourse running diagonally behind the junction.
  box(0, -6.8, -8, 214, 3, 170, "#374f55");
  box(0, -4.4, -8, 213, 2, 169, "#a48d74");
  box(0, -2.65, -8, 213, 1.5, 169, "#d5bd91");
  box(0, -1, -8, 212, 2, 168, "#9abc8d");
  const water: XY[] = [
    [-106, -76],
    [-76, -70],
    [-36, -58],
    [0, -52],
    [32, -46],
    [68, -39],
    [106, -34],
  ];
  ribbon(water, 24.5, 0.16, "#e5ce9f");
  ribbon(water, 22, 0.2, "#77bdbb");
  ribbon(water, 19, 0.24, "#3ca1b0");
  ribbon(water, 13, 0.25, "#268998");
  let seed = 493;
  function rand() {
    seed = (Math.imul(1664525, seed) + 1013904223) >>> 0;
    return seed / 4294967296;
  }
  for (let i = 0; i < 100; i++) {
    mark(
      water,
      rand() * 219,
      (rand() - 0.5) * 15,
      0.1,
      1.1 + rand() * 4,
      0.29,
      i % 2 ? "#73bec2" : "#56abb4",
    );
  }
  // Inlet visible under the second bridge and a planted bank separating the approaches.
  const inlet: XY[] = [
    [-106, -30],
    [-87, -40],
    [-73, -49],
    [-60, -56],
    [-40, -62],
  ];
  ribbon(inlet, 11, 0.32, "#78bcba");
  ribbon(inlet, 8.7, 0.34, "#3799a4");
  patch(
    [
      [-15, -41],
      [16, -33],
      [34, -36],
      [25, -26],
      [-1, -21],
      [-29, -23],
      [-41, -31],
    ],
    0.33,
    "#8caa7b",
  );
  patch(
    [
      [28, 48],
      [52, 39],
      [73, 45],
      [97, 60],
      [93, 72],
      [50, 74],
    ],
    0.28,
    "#95af7e",
  );
  const northRoad: XY[] = [
    [-106, -89],
    [-62, -80],
    [-12, -76],
    [36, -75],
    [70, -74],
    [106, -74],
  ];
  function deck(pts: XY[], w: number, level: number, start: number) {
    ribbon(pts, w + 3.6, level - 0.12, "#cecabc");
    ribbon(pts, w, level, "#4d5b60");
    const l = pts
      .slice(1)
      .reduce(
        (s, b, i) => s + Math.hypot(b[0] - pts[i]![0], b[1] - pts[i]![1]),
        0,
      );
    for (let d = start; d < l - 2; d += 4) {
      mark(pts, d, -0.22, 0.15, 4.01, level + 0.08, "#e8be6f");
      mark(pts, d, 0.22, 0.15, 4.01, level + 0.08, "#e8be6f");
      if (w > 11) {
        mark(pts, d, w / 4, 0.14, 1.9, level + 0.08, "#e2e6e0");
        mark(pts, d, -w / 4, 0.14, 1.9, level + 0.08, "#e2e6e0");
      }
    }
  }
  deck(northRoad, 8, 0.55, 0);
  for (const a of arms) deck(a.points, a.width, 0.87, 20);
  patch(
    [
      [-14, -10],
      [-5, -12],
      [12, -14],
      [17, -8],
      [19, 4],
      [15, 12],
      [5, 12],
      [-16, 13],
      [-24, 7],
      [-21, -4],
    ],
    0.98,
    "#4d5b60",
  );
  for (const [i, a] of arms.entries()) {
    const d = [21, 21, 24, 24][i]!;
    for (let s = -a.width / 2 + 1; s < a.width / 2 - 0.5; s += 1.15)
      mark(a.points, d, s, 0.57, 3.2, 1.05, "#f7f2e1");
    mark(
      a.points,
      d + 3,
      -a.width * 0.255,
      a.width * 0.43,
      0.42,
      1.05,
      "#f7f2e1",
    );
  }
  // Curved riverside connector and the west-side turning pocket visible in the reference.
  const slip: XY[] = [
    [-57, -30],
    [-43, -24],
    [-33, -20],
    [-24, -17.4],
    [-13, -16],
    [-3, -16.6],
    [8, -18.5],
    [18, -21.5],
    [23, -24.5],
    [29, -28],
  ];
  ribbon(slip, 6.7, 0.985, "#d5d0bd");
  ribbon(slip, 5.8, 1.0, "#536167");
  for (let t = -2.5; t < 2.6; t += 0.77)
    mark(slip, 44, t, 0.33, 2.1, 1.07, "#eee9d6");
  const westTurn: XY[] = [
    [-51, -25],
    [-38, -18],
    [-32, -13],
    [-29, -8],
    [-29, -3],
    [-32, 2],
    [-38, 5],
    [-53, 10],
  ];
  ribbon(westTurn, 4.2, 1.01, "#b7b8a6");
  ribbon(westTurn, 3.7, 1.03, "#5c676a");
  for (const o of [-7, 7])
    for (let d = 86; d < 111; d += 2.5) {
      const p = sample(arms[3]!.points, d, o);
      box(p.x, 1.63, p.z, 0.38, 1.55, 2.55, "#dedbc7", p.r);
    }
  for (const a of arms) {
    for (let j = 0; j < 2; j++) {
      const q = sample(a.points, 39, -a.width * (j ? 0.13 : 0.36));
      box(q.x, 1.09, q.z, 0.29, 0.06, 2.15, "#e1e1d0", q.r);
      const f = sample(a.points, 37.8, -a.width * (j ? 0.13 : 0.36));
      for (const sign of [-1, 1])
        box(
          f.x + sign * 0.26 * Math.cos(q.r),
          1.09,
          f.z - sign * 0.26 * Math.sin(q.r),
          0.24,
          0.06,
          1.03,
          "#e1e1d0",
          q.r + sign * 0.55,
        );
    }
  }
  // Bridge parapets and piers on the north-east arm. Deck is raised above water.
  for (const o of [-7.5, 7.5]) {
    for (let d = 43; d < 78; d += 2.4) {
      const p = sample(arms[0]!.points, d, o);
      box(p.x, 1.8, p.z, 0.48, 1.9, 2.5, "#d5d4ba", p.r);
      box(p.x, 2.78, p.z, 0.62, 0.18, 2.55, "#f3eada", p.r);
    }
    for (const d of [49, 62, 74]) {
      const p = sample(arms[0]!.points, d, o * 0.78);
      pole(p.x, 0.6, p.z, 1, 1.35, "#86918b");
    }
  }
  // An elevated bridge deck: graded approach slabs, concrete fascia, spaced rail posts.
  const bridge = arms[0]!.points;
  const elev = (d: number) =>
    0.98 +
    Math.min(clamp((d - 36) / 10, 0, 1), clamp((83 - d) / 9, 0, 1)) * 2.9;
  for (let d = 36; d < 83; d += 1) {
    const pt = sample(bridge, d + 0.5);
    box(pt.x, elev(d) - 0.22, pt.z, 15, 0.42, 1.09, "#adada3", pt.r);
    box(pt.x, elev(d) + 0.03, pt.z, 13.1, 0.1, 1.12, "#536069", pt.r);
    for (const off of [-7.2, 7.2]) {
      const q = sample(bridge, d + 0.5, off);
      box(q.x, elev(d) + 1.03, q.z, 0.24, 0.22, 1.12, "#dae1d6", q.r);
      if (d % 3 === 0)
        box(q.x, elev(d) + 0.5, q.z, 0.3, 1, 0.33, "#bbc5bd", q.r);
    }
    for (const off of [-0.2, 0.2])
      mark(bridge, d + 0.5, off, 0.15, 1.07, elev(d) + 0.105, "#dec084");
    if (d % 5 < 2)
      for (const off of [-3.2, 3.2])
        mark(bridge, d + 0.5, off, 0.13, 1.04, elev(d) + 0.11, "#dbe1dc");
  }
  for (const d of [50, 63, 71])
    for (const o of [-5.3, 5.3]) {
      const q = sample(bridge, d, o);
      pole(q.x, 1.7, q.z, 0.8, 2.8, "#849695");
    }
  // Buildings: individual wall/window geometry, roof coping, roof plant and entry walks.
  function house(
    x: number,
    z: number,
    w: number,
    d: number,
    h: number,
    rotation: number,
    c: string,
  ) {
    const cs = Math.cos(rotation),
      sn = Math.sin(rotation);
    function part(
      xx: number,
      y: number,
      zz: number,
      ww: number,
      hh: number,
      dd: number,
      col: string,
    ) {
      box(
        x + xx * cs + zz * sn,
        y,
        z - xx * sn + zz * cs,
        ww,
        hh,
        dd,
        col,
        rotation,
      );
    }
    part(0, 0.22, 0, w + 3, 0.42, d + 3, "#c5bfa7");
    part(0, h / 2 + 0.4, 0, w, h, d, c);
    for (let y = 2; y < h; y += 2.7) {
      for (const face of [-1, 1]) {
        part(
          0,
          y + 0.79,
          face * (d / 2 + 0.06),
          w + 0.05,
          0.2,
          0.22,
          "#cad1c8",
        );
        for (let xx = -w / 2 + 1.3; xx < w / 2 - 1; xx += 2.6)
          part(xx, y, face * (d / 2 + 0.07), 1.4, 1.15, 0.15, "#607b80");
        for (let zz = -d / 2 + 1.3; zz < d / 2 - 1; zz += 2.6)
          part(face * (w / 2 + 0.07), y, zz, 0.16, 1.15, 1.4, "#789498");
      }
    }
    part(0, h + 0.52, 0, w + 0.65, 0.55, d + 0.65, "#f1ebd8");
    part(0, h + 0.83, 0, w - 0.6, 0.08, d - 0.6, "#9eada9");
    part(w * 0.17, h + 1.5, d * 0.14, w * 0.32, 1.3, d * 0.28, "#d3d4c4");
    part(-w * 0.21, h + 0.98, -d * 0.11, w * 0.19, 0.3, d * 0.32, "#7f9698");
  }
  house(-58, 32, 20, 9, 12, 0.19, "#e1dac0");
  house(-34, 28, 14, 8, 9, 0.19, "#d6ceba");
  house(-75, 49, 16, 9, 9, 0.17, "#e2ddca");
  house(-45, 50, 21, 10, 15, 0.19, "#d4cebb");
  house(-68, 66, 16, 8, 11, 0.15, "#e5ddc1");
  house(-18, 51, 12, 8, 8, 0.19, "#dfd3b8");
  house(17, 28, 12, 7, 4.6, -0.25, "#d8bb98");
  house(72, -12, 14, 8, 7, -0.25, "#e2d3b8");
  house(94, -5, 12, 9, 9, -0.25, "#e4dfcf");
  const paths: XY[][] = [
    [
      [-104, 37],
      [-70, 29],
      [-35, 19],
      [-21, 18],
    ],
    [
      [-97, 70],
      [-66, 60],
      [-30, 59],
      [-14, 48],
      [1, 36],
      [10, 23],
    ],
    [
      [17, 75],
      [25, 54],
      [47, 39],
      [63, 31],
    ],
  ];
  for (const p of paths) ribbon(p, 1.8, 0.25, "#dbd3b6");
  function tree(x: number, z: number, s: number) {
    pole(x, 1.4 * s, z, 0.26 * s, 2.8 * s, "#806f59");
    const g = new T.IcosahedronGeometry(1, 0);
    g.scale(2.7 * s, 3.6 * s, 2.6 * s);
    add(
      g,
      ["#5c936e", "#77a075", "#709872", "#8ca871"][Math.floor(rand() * 4)]!,
      x,
      4 * s,
      z,
      rand() * 3,
    );
  }
  for (const a of arms) {
    for (let d = 32; d < 88; d += 9) {
      for (const side of [-1, 1]) {
        const p = sample(a.points, d, side * (a.width / 2 + 3.3));
        if ((a === arms[0] && d > 41) || (a === arms[2] && side === -1))
          continue;
        tree(p.x, p.z, 0.62 + rand() * 0.27);
      }
    }
  }
  for (const [cx, cz] of [
    [60, 59],
    [86, 62],
    [8, 61],
    [-85, -24],
    [-12, -31],
    [-60, -88],
    [30, -85],
  ])
    for (let j = 0; j < 9; j++)
      tree(
        cx! + (rand() - 0.5) * 19,
        cz! + (rand() - 0.5) * 10,
        0.72 + rand() * 0.6,
      );
  // Controller symbols on physical posts. Live count markers are aggregated, not trajectories.
  const pins: T.Vector3[] = [];
  const lights: T.Mesh[][] = [];
  const carSets: T.Group[][] = [];
  const dynamic: T.Material[] = [];
  const dynGeo: T.BufferGeometry[] = [];
  const sphere = new T.SphereGeometry(0.59, 10, 8);
  dynGeo.push(sphere);
  for (const [i, a] of arms.entries()) {
    const stop = [25, 25, 29, 29][i]!,
      p = sample(a.points, stop, -a.width / 2 - 1);
    pole(p.x, 4, p.z, 0.24, 6.2, "#54666b");
    box(p.x, 7.4, p.z, 1.75, 4.65, 1.24, "#253238");
    pins.push(new T.Vector3(p.x, 10.2, p.z));
    const bulbs: T.Mesh[] = [];
    for (let j = 0; j < 3; j++) {
      const m = new T.MeshBasicMaterial({ color: "#425054" });
      dynamic.push(m);
      const b = new T.Mesh(sphere, m);
      b.position.set(p.x, 8.7 - j * 1.26, p.z + 0.6);
      scene.add(b);
      bulbs.push(b);
    }
    lights.push(bulbs);
    const cars: T.Group[] = [];
    for (let j = 0; j < 10; j++) {
      const k = sample(
        a.points,
        stop + 4 + Math.floor(j / 2) * 5.4,
        -a.width * (j % 2 ? 0.14 : 0.36),
      );
      const car = new T.Group();
      car.position.set(
        k.x,
        i === 0 && stop + 4 + Math.floor(j / 2) * 5.4 >= 36
          ? elev(stop + 4 + Math.floor(j / 2) * 5.4) + 0.2
          : 1.17,
        k.z,
      );
      car.rotation.y = k.r;
      for (const [w, h, d, y, col] of [
        [
          1.55,
          0.65,
          3.35,
          0.38,
          j % 3 === 0 ? "#eccb77" : j % 3 === 1 ? "#e2eeeb" : "#749eb4",
        ],
        [1.29, 0.54, 1.55, 0.94, "#6d8891"],
      ] as const) {
        const geom = new T.BoxGeometry(w, h, d);
        dynGeo.push(geom);
        const piece = new T.Mesh(geom, mat(col));
        piece.position.y = y;
        piece.castShadow = true;
        car.add(piece);
      }
      scene.add(car);
      cars.push(car);
    }
    carSets.push(cars);
  }
  for (const [c, geoms] of batch) {
    const g = mergeGeometries(geoms);
    const mesh = new T.Mesh(g, mat(c));
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    scene.add(mesh);
    dynGeo.push(g);
    geoms.forEach((q) => q.dispose());
  }
  const grid = new T.GridHelper(650, 65, "#426270", "#35535e");
  grid.position.y = -8.6;
  scene.add(grid);
  let dirty = true,
    active = true,
    raf = 0,
    dead = false;
  const ro = new ResizeObserver(size);
  ro.observe(host);
  function size() {
    const w = host.clientWidth,
      h = host.clientHeight;
    if (w && h) {
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h, false);
      dirty = true;
    }
  }
  function home(top = false) {
    size();
    controls.target.set(-2, 1, -5);
    const factor = clamp(1.63 / camera.aspect, 0.95, 1.85);
    camera.position
      .copy(controls.target)
      .add(
        (top
          ? new T.Vector3(0, 190, 0.3)
          : new T.Vector3(22, 153, 178)
        ).multiplyScalar(factor),
      );
    controls.update();
    dirty = true;
  }
  home();
  controls.addEventListener("change", () => {
    dirty = true;
  });
  function frame() {
    if (dead) return;
    raf = requestAnimationFrame(frame);
    if (!active || document.hidden) return;
    controls.update();
    if (!dirty) return;
    dirty = false;
    renderer.render(scene, camera);
    const w = host.clientWidth,
      h = host.clientHeight;
    const pts = [
      ...pins,
      new T.Vector3(51, 4, -64),
      new T.Vector3(-49, 18, 53),
      new T.Vector3(-12, 2, -76),
      new T.Vector3(-84, 4, -44),
    ].map((p) => {
      const q = p.clone().project(camera);
      return {
        x: ((q.x + 1) * w) / 2,
        y: ((1 - q.y) * h) / 2,
        visible: Math.abs(q.x) < 0.96 && Math.abs(q.y) < 0.96 && q.z < 1,
      };
    });
    onProject(pts, (controls.getAzimuthalAngle() * 180) / Math.PI);
  }
  frame();
  const io = new IntersectionObserver((e) => {
    active = e[0]?.isIntersecting ?? true;
    if (active) dirty = true;
  });
  io.observe(host);
  function update(colors: Lamp[], counts: (number | null)[]) {
    lights.forEach((bs, i) =>
      bs.forEach((b, j) => {
        const c = ["red", "yellow", "green"][j];
        (b.material as T.MeshBasicMaterial).color.set(
          colors[i] === c || (colors[i] === "flash" && j === 1)
            ? ["#ff4749", "#ffb52c", "#40ff98"][j]!
            : "#38444a",
        );
      }),
    );
    carSets.forEach((cs, i) =>
      cs.forEach((c, j) => (c.visible = j < Math.min(10, counts[i] ?? 0))),
    );
    dirty = true;
  }
  return {
    home,
    update,
    zoom: (v: number) => {
      camera.position
        .sub(controls.target)
        .multiplyScalar(v)
        .add(controls.target);
      controls.update();
      dirty = true;
    },
    dispose: () => {
      dead = true;
      cancelAnimationFrame(raf);
      ro.disconnect();
      io.disconnect();
      controls.dispose();
      grid.geometry.dispose();
      (grid.material as T.Material).dispose();
      dynGeo.forEach((g) => g.dispose());
      dynamic.forEach((m) => m.dispose());
      mats.forEach((m) => m.dispose());
      sun.shadow.dispose();
      renderer.dispose();
      renderer.domElement.remove();
    },
  };
}
