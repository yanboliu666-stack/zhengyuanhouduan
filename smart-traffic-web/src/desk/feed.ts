export const dirs = [
  ["N", "北", "north", "P_N"],
  ["E", "东", "east", "P_E"],
  ["S", "南", "south", "P_S"],
  ["W", "西", "west", "P_W"],
] as const;
export type Stage =
  | "green"
  | "yellow"
  | "all_red"
  | "unknown"
  | "flash"
  | "off";
export type Lamp = "green" | "yellow" | "red" | "unknown" | "flash" | "off";
export interface EventRow {
  ts: number;
  type: string;
  tick?: number;
  to_phase?: string;
  from_phase?: string;
  from_mode?: string;
  to_mode?: string;
  reason?: string;
  alarm_type?: string;
}
export interface Feed {
  ts?: number;
  phase?: string;
  mode?: string;
  received_ms?: number;
  interval_ms?: number;
  seq?: number;
  await_phase?: boolean;
  degradation?: string;
  lanes?: Record<string, { vehicle_count: number; oldest_wait_s: number }>;
  board?: { updated_at: number; stage: string; phase_id: string };
  events?: EventRow[];
}
export const valid = (ts: number | undefined, n: number) =>
  !!ts && Number.isFinite(ts) && n - ts >= -1 && n - ts < 4;
export function resolve(f: Feed, n: number) {
  let stage: Stage = "unknown",
    phase = "",
    source = "无有效依据";
  const b = f.board,
    known = (p: string) => dirs.some((d) => d[3] === p);
  if (b && valid(b.updated_at, n)) {
    phase = b.phase_id;
    source = "板端帧";
    if (["green", "yellow", "all_red", "flash", "off"].includes(b.stage))
      stage = b.stage as Stage;
  } else if (valid(f.ts, n)) {
    source = "边缘状态重建";
    phase = f.phase ?? "";
    if (f.mode === "all_red") stage = "all_red";
    if (f.mode === "clearance") stage = "yellow";
    if (f.mode === "normal" && !f.await_phase) stage = "green";
  }
  if (["green", "yellow"].includes(stage) && !known(phase)) stage = "unknown";
  return { stage, phase, source };
}
export function color(stage: Stage, phase: string, target: string): Lamp {
  if (stage === "unknown" || stage === "flash" || stage === "off") return stage;
  return stage !== "all_red" && phase === target ? stage : "red";
}

/** 把后端下发的每盏灯真实颜色（signal_colors）转成与四方向一一对应的 Lamp[]。
 * 顺序：北→东→南→西，与 arms / binding 保持一致，直接交给 Three.js 点灯。
 * 缺失或无法识别时返回 null，由调用方回退到 resolve() 推导。 */
export function signalColorsToLamps(
  colors: Record<string, string> | undefined,
): Lamp[] | undefined {
  if (!colors || typeof colors !== "object") return undefined;
  const out: Lamp[] = [];
  for (const dir of ["north", "east", "south", "west"]) {
    const v = String(
      colors[dir] ?? colors[dir + "_through"] ?? "unknown",
    );
    out.push(
      ["green", "yellow", "red", "unknown", "flash", "off"].includes(v)
        ? (v as Lamp)
        : "unknown",
    );
  }
  return out.length === 4 ? out : undefined;
}
export const text = {
  green: "绿灯放行",
  yellow: "黄灯清空",
  all_red: "四向全红",
  flash: "黄灯闪烁",
  off: "灯组熄灭",
  unknown: "灯态未确认",
  red: "红灯等待",
};
export const evNames: Record<string, string> = {
  decision_change: "策略建议",
  mode_change: "模式切换",
  degradation_change: "降级变化",
  heartbeat_fault: "心跳异常",
  feedback_failure: "反馈异常",
  alarm: "边缘告警",
};
export function demoFeed(t: number, n: number): Feed {
  const j = Math.floor(t / 24) % 4,
    k = t % 24,
    mode = k < 17 ? "normal" : k < 22 ? "clearance" : "all_red",
    lanes: NonNullable<Feed["lanes"]> = {};
  dirs.forEach((d, i) => {
    for (const [l, key] of ["through", "left"].entries()) {
      lanes[d[2] + "_" + key] = {
        vehicle_count: Math.max(
          0,
          [6, 4, 3, 8][i]! - l * 2 + (i === j ? -Math.floor(k / 7) : 0),
        ),
        oldest_wait_s: 5 + i * 6 + (k % 5),
      };
    }
  });
  const events: EventRow[] = [];
  for (let i = t; i >= Math.max(0, t - 150); i--) {
    const a = i % 24;
    if (a === 0 || a === 17 || a === 22)
      events.push({
        type: "mode_change",
        ts: n - (t - i) * 0.5,
        to_mode: a === 0 ? "normal" : a === 17 ? "clearance" : "all_red",
        tick: i,
      });
    if (a === 15)
      events.push({
        type: "decision_change",
        to_phase: dirs[(Math.floor(i / 24) + 1) % 4]![3],
        ts: n - (t - i) * 0.5,
        tick: i,
      });
  }
  return {
    ts: n - 0.08,
    phase: dirs[j]![3],
    mode,
    seq: t,
    interval_ms: [497, 508, 501, 492, 505, 498, 510][t % 7],
    received_ms: n * 1000,
    events,
    lanes,
    degradation: "normal",
  };
}
