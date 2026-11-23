export const arms = [
  ["N", "北", "north", "P_N"],
  ["E", "东", "east", "P_E"],
  ["S", "南", "south", "P_S"],
  ["W", "西", "west", "P_W"],
] as const;
export type Lamp = "green" | "yellow" | "red" | "flash" | "off" | "unknown";
export type Stage =
  | "green"
  | "yellow"
  | "all_red"
  | "flash"
  | "off"
  | "unknown";
export interface Frame {
  phase_id: string | null;
  stage: Stage;
  updated_at: number;
}
export interface Lane {
  vehicle_count: number;
  oldest_wait_s: number;
}
export interface Snapshot {
  junction_id: string;
  board_frame?: Frame | null;
  traffic_ts?: number;
  lanes?: Record<string, Lane>;
  degradation?: string;
}
export const stageText: Record<Stage, string> = {
  green: "绿灯放行",
  yellow: "黄灯清空",
  all_red: "四向全红",
  flash: "黄灯闪烁",
  off: "信号熄灯",
  unknown: "等待回读",
};
export function fresh(ts: unknown, now: number) {
  return (
    typeof ts === "number" &&
    Number.isFinite(ts) &&
    now >= ts - 1 &&
    now - ts < 4
  );
}
export function stageOf(frame: Frame | null | undefined, now: number): Stage {
  if (!frame || !fresh(frame.updated_at, now)) return "unknown";
  if (frame.stage === "green" || frame.stage === "yellow")
    return arms.some((a) => a[3] === frame.phase_id) ? frame.stage : "unknown";
  return ["all_red", "flash", "off"].includes(frame.stage)
    ? frame.stage
    : "unknown";
}
export function lamp(
  stage: Stage,
  phase: string | null | undefined,
  dir: string,
): Lamp {
  if (stage === "unknown" || stage === "flash" || stage === "off") return stage;
  return stage !== "all_red" && phase === dir ? stage : "red";
}
export function fixture(t: number, now: number): Snapshot {
  const idx = Math.floor(t / 12) % 4,
    step = t % 12,
    n = [4, 7, 3, 5],
    waits = [13, 24, 9, 18];
  const lanes: Record<string, Lane> = {};
  arms.forEach((a, i) => {
    const count = i === idx ? Math.max(1, n[i]! - Math.floor(step / 3)) : n[i]!;
    for (const [j, k] of ["through", "left"].entries())
      lanes[a[2] + "_" + k] = {
        vehicle_count: j ? 1 : count,
        oldest_wait_s: waits[i]! + Math.floor(step / 2) - j * 3,
      };
  });
  return {
    junction_id: "mini_1",
    board_frame: {
      phase_id: arms[idx]![3],
      stage: step < 8 ? "green" : step < 11 ? "yellow" : "all_red",
      updated_at: now,
    },
    traffic_ts: now,
    lanes,
    degradation: "normal",
  };
}
