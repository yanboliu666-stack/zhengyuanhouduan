// Local modelling units. +X points right and +Z down in the supplied map.
// Road arms ordered: bridge, Nanhuan, provincial road, Shuangxi. Not survey data.
export type XY = [number, number];
export const arms = [
  {
    name: "双溪口桥侧",
    short: "双溪口桥",
    points: [
      [0, 0],
      [15, -10],
      [30, -26],
      [46, -48],
      [55, -61],
      [57, -71],
      [53, -75],
    ] as XY[],
    width: 13,
  },
  {
    name: "南环路侧",
    short: "南环路",
    points: [
      [0, 0],
      [19, 9],
      [41, 19],
      [75, 33],
      [106, 44],
    ] as XY[],
    width: 16,
  },
  {
    name: "219 省道侧",
    short: "219 省道",
    points: [
      [0, 0],
      [-25, 6],
      [-59, 13],
      [-106, 19],
    ] as XY[],
    width: 17,
  },
  {
    name: "双溪路侧",
    short: "双溪路",
    points: [
      [0, 0],
      [-16, -8],
      [-41, -20],
      [-65, -34],
      [-106, -55],
    ] as XY[],
    width: 13,
  },
];
export const demoBinding = ["P_N", "P_E", "P_S", "P_W"];
export const district = {
  code: "PA · 01",
  title: "南环路 × 双溪路",
  region: "浙江省 · 金华市 · 磐安县",
};
export function bindingOK(x: unknown): x is string[] {
  return (
    Array.isArray(x) &&
    x.length === 4 &&
    new Set(x).size === 4 &&
    x.every((v) => demoBinding.includes(v))
  );
}
