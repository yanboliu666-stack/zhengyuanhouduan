<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import {
  Monitor,
  Connection,
  Operation,
  Document,
  FullScreen,
  Grid,
  DataAnalysis,
  ArrowRight,
  Clock,
  SwitchButton,
  Close,
  VideoPlay,
  VideoPause,
  InfoFilled,
  Aim,
  TrendCharts,
} from "@element-plus/icons-vue";
import SiteView from "../terrain/SiteView.vue";
import {
  bindingOK,
  demoBinding,
  district,
  arms as roads,
} from "../terrain/site";
import {
  dirs,
  resolve,
  text,
  evNames,
  valid,
  demoFeed,
  signalColorsToLamps,
  type Feed,
  type EventRow,
  type Lamp,
} from "../desk/feed";
import { trafficApi } from "../api/traffic";
const props = defineProps<{ demo?: boolean }>(),
  router = useRouter(),
  f = ref<Feed>({}),
  now = ref(Date.now() / 1000),
  id = ref(import.meta.env.VITE_PANAN_JUNCTION || "mini_1"),
  binding = ref<string[]>(demoBinding.slice()),
  lampColors = ref<Lamp[] | undefined>(undefined),
  confirmed = ref(false),
  panel = ref(""),
  focus = ref(0),
  grid = ref(true),
  wide = ref(false),
  paused = ref(false),
  err = ref(""),
  samples = ref<{ ts: number; ms: number }[]>([]),
  filter = ref("all"),
  nav = ref("监测总览");
let alive = true,
  epoch = 0,
  loading = false,
  offset = 0,
  tick = 192,
  timer = 0,
  timer2 = 0;
const sig = computed(() => resolve(f.value, now.value)),
  online = computed(() => valid(f.value.ts, now.value)),
  age = computed(() =>
    f.value.ts ? Math.max(0, now.value - f.value.ts) : null,
  ),
  current = computed(() => {
    const v = sig.value;
    const arm = dirs.find((d) => d[3] === v.phase);
    return (
      (arm && ["green", "yellow"].includes(v.stage) ? arm[1] + "向" : "") +
      text[v.stage]
    );
  }),
  connection = computed(() =>
    props.demo
      ? "演示回放"
      : err.value ||
        (online.value ? "边缘在线" : f.value.ts ? "遥测过期" : "等待遥测"),
  );
const fmt = (s?: number) =>
  s ? new Date(s * 1000).toLocaleTimeString("en-GB", { hour12: false }) : "—";
const lane = (i: number, k: string) =>
  online.value ? f.value.lanes?.[dirs[i]![2] + "_" + k] : undefined;
function count(i: number, k: string) {
  const v = lane(i, k)?.vehicle_count;
  return typeof v === "number" && Number.isInteger(v) && v >= 0 ? v : null;
}
const totals = computed(() =>
    dirs.map((_, i) => {
      const a = count(i, "through"),
        b = count(i, "left");
      return a !== null && b !== null ? a + b : null;
    }),
  ),
  total = computed(() =>
    totals.value.every((x) => x !== null)
      ? totals.value.reduce((s, x) => s + x!, 0)
      : null,
  ),
  events = computed(() =>
    [...(f.value.events ?? [])].sort((a, b) => b.ts - a.ts),
  ),
  filtered = computed(() =>
    events.value.filter(
      (e) => filter.value === "all" || e.type === filter.value,
    ),
  ),
  realTick = computed(
    () => events.value.find((e) => typeof e.tick === "number")?.tick,
  );
const interval = computed(() =>
    online.value && Number(f.value.interval_ms) > 0
      ? f.value.interval_ms
      : null,
  ),
  rate = computed(() =>
    interval.value ? (1000 / interval.value).toFixed(1) : "—",
  ),
  latency = computed(() =>
    online.value && f.value.received_ms && f.value.ts
      ? Math.round(f.value.received_ms - f.value.ts * 1000)
      : null,
  );
const trace = computed(() => {
  const s = samples.value;
  if (!s.length) return "";
  const m = Math.max(600, ...s.map((v) => v.ms)),
    lo = Math.min(400, ...s.map((v) => v.ms));
  return s
    .map(
      (v, i) =>
        `${(i * 240) / Math.max(1, s.length - 1)},${36 - (32 * (v.ms - lo)) / (m - lo || 1)}`,
    )
    .join(" ");
});
function accept(d: Feed) {
  f.value = d;
  if (
    d.ts &&
    d.interval_ms &&
    Number.isFinite(d.interval_ms) &&
    d.interval_ms > 0 &&
    samples.value.at(-1)?.ts !== d.ts
  ) {
    samples.value.push({ ts: d.ts, ms: d.interval_ms });
    samples.value = samples.value.slice(-32);
  }
}
function sample() {
  now.value = Date.now() / 1000;
  accept(demoFeed(tick, now.value));
}
async function poll() {
  if (loading || !alive) return;
  loading = true;
  const g = epoch;
  try {
    const r = await trafficApi.getJunctionRealtimeState(id.value);
    if (!alive || epoch !== g) return;
    const d = r.data?.data;
    if (!d || d.junction_id !== id.value) throw Error();
    offset =
      typeof d.server_ms === "number"
        ? d.server_ms / 1000 - Date.now() / 1000
        : 0;
    now.value = Date.now() / 1000 + offset;
    binding.value = d.site
      ? bindingOK(d.site.binding)
        ? d.site.binding
        : []
      : demoBinding.slice();
    confirmed.value = !!d.site?.confirmed && binding.value.length === 4;
    err.value = d.edge_feed?.ts ? "" : "未收到感知快照";
    accept(d.edge_feed ?? {});
    // 以边缘计算下发的每盏灯真实颜色为最高优先级；缺失时回退 resolve() 推导
    lampColors.value = signalColorsToLamps(d.signal_colors);
  } catch {
    if (alive && epoch === g) {
      err.value = "接口未连接";
      f.value = {};
    }
  } finally {
    if (epoch === g) loading = false;
  }
}
function eventText(e: EventRow) {
  if (e.type === "decision_change") return `建议相位 ${e.to_phase ?? "—"}`;
  if (e.type === "mode_change" || e.type === "degradation_change")
    return `${e.from_mode ?? "—"} → ${e.to_mode ?? "—"}`;
  return e.reason || e.alarm_type || evNames[e.type] || e.type;
}
function section(s: string) {
  nav.value = s;
  if (s === "监测总览") window.scrollTo({ top: 0, behavior: "smooth" });
  else if (s === "边缘链路" || s === "事件记录") panel.value = s;
  else if (props.demo) panel.value = "演示说明";
  else router.push("/control");
}
function close() {
  panel.value = "";
  wide.value = false;
  nav.value = "监测总览";
}
function esc(e: KeyboardEvent) {
  if (e.key === "Escape") close();
}
onMounted(() => {
  window.addEventListener("keydown", esc);
  if (props.demo) {
    for (let j = tick - 28; j < tick; j++)
      accept(demoFeed(j, now.value - (tick - j) * 0.5));
    sample();
    timer = window.setInterval(() => {
      if (!paused.value) {
        tick++;
        sample();
      }
    }, 500);
  } else {
    void poll();
    timer = window.setInterval(poll, 500);
    timer2 = window.setInterval(
      () => (now.value = Date.now() / 1000 + offset),
      200,
    );
  }
});
onUnmounted(() => {
  alive = false;
  epoch++;
  clearInterval(timer);
  clearInterval(timer2);
  window.removeEventListener("keydown", esc);
});
const links = [
  { name: "监测总览", icon: Monitor },
  { name: "边缘链路", icon: Connection },
  { name: "事件记录", icon: Document },
  { name: "配时控制", icon: Operation },
];
const modeName = computed(
  () =>
    ({
      normal: "常规放行",
      clearance: "黄灯清空",
      all_red: "全红过渡",
      fault: "故障模式",
      manual_override: "人工 / 本地",
    })[f.value.mode ?? ""] ?? "等待模式事件",
);
function logout() {
  localStorage.removeItem("token");
  router.push("/login");
}
</script>
<template>
  <div class="desk">
    <aside class="rail">
      <div class="brand">
        <svg viewBox="0 0 42 42" aria-hidden="true">
          <rect width="42" height="42" rx="12" fill="#7764ff" />
          <g fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round">
            <path
              d="M10 30V17q0-6 6-6h3M18 31V21q0-5 5-5h8M26 31v-5q0-3 4-3h2"
            />
          </g>
        </svg>
        <div><b>路序</b><small>SIGNAL DESK</small></div>
      </div>
      <div class="railnav">
        <label>WORKSPACE</label
        ><button
          v-for="l in links"
          :aria-label="l.name"
          :key="l.name"
          :class="{ active: nav === l.name }"
          @click="section(l.name)"
        >
          <component :is="l.icon" /><span>{{ l.name }}</span>
        </button>
      </div>
      <div class="railbottom">
        <div class="railgraph">
          <svg viewBox="0 0 150 66" aria-hidden="true">
            <g
              stroke="#8e83ed"
              fill="none"
              opacity=".65"
              transform="translate(72 35) scale(1 .42) rotate(35)"
            >
              <rect
                v-for="k in 6"
                :key="k"
                :x="-8 * k"
                :y="-8 * k"
                :width="16 * k"
                :height="16 * k"
                rx="4"
              />
              <path d="M-70 0H70M0-70V70" />
            </g></svg
          ><b>PAN’AN FIELD LAB</b><small>磐安 · 路口观测站</small>
        </div>
        <button @click="panel = '接入信息'"><InfoFilled /> 接入信息</button>
      </div>
    </aside>
    <div class="shell">
      <header class="top">
        <div><Grid /> 工作空间 <i>/</i> <strong>信号监测</strong></div>
        <div>
          <span class="clock"><Clock />{{ fmt(now) }}</span
          ><button
            class="avatar"
            aria-label="账户与接入信息"
            @click="panel = '接入信息'"
          >
            OP
          </button>
        </div>
      </header>
      <main>
        <div class="heading">
          <div>
            <div class="overline">
              <b></b> TERRAIN OBSERVATORY <i>/</i> SITE 01
            </div>
            <h1>南环路 <span>×</span> 双溪路</h1>
            <p>{{ district.region }} <i>/</i> 路口三维数字孪生</p>
          </div>
          <div class="tools">
            <span class="badge" :class="{ ok: online && !demo }"
              ><i />{{ connection }}</span
            ><button v-if="demo" @click="paused = !paused">
              <component :is="paused ? VideoPlay : VideoPause" />{{
                paused ? "继续" : "暂停"
              }}</button
            ><span v-else class="siteid">{{ id }}</span>
          </div>
        </div>
        <div class="primary">
          <section class="card map" :class="{ wide }">
            <div class="cardhead">
              <div class="titlegroup">
                <span class="tile"><Aim /></span>
                <div>
                  <small>SPATIAL DIGITAL TWIN</small>
                  <h2>路口三维实景模拟</h2>
                </div>
              </div>
              <div class="mapbuttons">
                <span class="node">{{ id.toUpperCase() }}</span
                ><button
                  title="显示或隐藏地名"
                  aria-label="显示或隐藏地名"
                  :aria-pressed="grid"
                  @click="grid = !grid"
                >
                  <Grid /></button
                ><button
                  title="放大或还原路口图"
                  aria-label="放大或还原路口图"
                  @click="wide = !wide"
                >
                  <FullScreen />
                </button>
              </div>
            </div>
            <div class="mapview">
              <SiteView
                :stage="sig.stage"
                :phase="sig.phase"
                :focus="focus"
                :labels="grid"
              :binding="binding"
              :counts="totals"
              :confirmed="confirmed"
              :demo="!!demo"
              :lamp-colors="lampColors"
              @select="focus = $event"
              />
            </div>
            <div class="legend">
              <span><i class="green" />放行</span
              ><span><i class="yellow" />清空</span
              ><span><i class="red" />禁行</span
              ><span><i class="unknown" />未知</span><small>四向独立灯组</small>
            </div>
          </section>
          <div class="right">
            <section class="card phase">
              <div class="kicker">
                <span class="mark">◉</span> SIGNAL PHASE
                <span class="righttag">当前相位</span>
              </div>
              <h2>{{ current }}</h2>
              <div class="phaseid">
                <code>{{ sig.phase || "—" }}</code
                ><span>{{ demo ? "演示样例" : sig.source }}</span>
              </div>
              <div class="roadread">
                {{
                  sig.phase && binding.includes(sig.phase)
                    ? roads[binding.indexOf(sig.phase)]?.name
                    : "暂无可定位相位"
                }}
                <small>{{
                  demo ? "演示" : confirmed ? "配置已核验" : "暂定映射"
                }}</small>
              </div>
              <div class="phasefoot">
                <span>控制模式</span><b>{{ online ? modeName : "未同步" }}</b>
              </div>
            </section>
            <section class="card pulse">
              <div class="kicker">
                <TrendCharts /> EDGE PULSE
                <button aria-label="查看边缘链路" @click="section('边缘链路')">
                  <ArrowRight />
                </button>
              </div>
              <h2>边缘数据脉搏</h2>
              <div class="pulserow">
                <div class="big">{{ rate }}<small> Hz</small></div>
                <svg
                  viewBox="0 0 240 42"
                  preserveAspectRatio="none"
                  aria-label="实际收到的相邻样本间隔"
                >
                  <path
                    d="M0 33h240M0 18h240"
                    stroke="#e4e3f2"
                    stroke-dasharray="3 4"
                  />
                  <polyline
                    :points="trace"
                    fill="none"
                    stroke="#7959ee"
                    stroke-width="2.3"
                    vector-effect="non-scaling-stroke"
                  />
                </svg>
              </div>
              <div class="pulsefacts">
                <div>
                  <small>最新采样间隔</small
                  ><b>{{ interval ?? "—" }} <em>ms</em></b>
                </div>
                <div>
                  <small>样本年龄</small
                  ><b>{{ age !== null ? age.toFixed(1) : "—" }} <em>s</em></b>
                </div>
              </div>
              <p :key="f.ts" class="stamp">
                <i :class="{ beat: online }" />{{
                  demo ? "回放样本" : "边缘样本"
                }}
                <b>#{{ f.seq ?? "—" }}</b> · {{ fmt(f.ts) }}
              </p>
            </section>
          </div>
        </div>
        <div
          v-if="!demo && (!online || sig.stage === 'unknown')"
          class="diagnostic"
        >
          <strong>{{ connection }}</strong> ·
          {{
            !online
              ? err === "接口未连接"
                ? "检查 Network 中状态 API、网关与登录状态。"
                : f.ts
                  ? "样本已过期；请核对边缘和服务器时钟及 MQTT 积压。"
                  : `已选 ${id}。检查 ingest-svc 是否接收到该路口的 event/traffic_state。`
              : "感知在更新，但灯色证据不足。请检查实际相位和 mode_change 事件。"
          }}
          地形始终显示，不用演示数据补灯。
        </div>
        <div class="secondary">
          <section class="card traffic">
            <div class="cardhead">
              <div class="titlegroup">
                <span class="tile mint"><DataAnalysis /></span>
                <div>
                  <small>APPROACH LOAD</small>
                  <h2>进口车辆分布</h2>
                </div>
              </div>
              <div class="total">
                合计 <b>{{ total ?? "—" }}</b> 辆
              </div>
            </div>
            <div class="loadrows">
              <button
                v-for="(d, i) in dirs"
                :key="d[0]"
                :class="{ chosen: focus === i }"
                @click="focus = i"
              >
                <span class="letter">{{ d[0] }}</span
                ><strong>{{ d[1] }}进口</strong
                ><span class="track"
                  ><i
                    :style="{
                      width: `${(100 * (totals[i] ?? 0)) / Math.max(1, ...totals.map((v) => v ?? 0))}%`,
                    }" /></span
                ><b>{{ totals[i] ?? "—" }} <small>辆</small></b>
              </button>
            </div>
            <div class="trafficfoot">
              {{ dirs[focus]![1] }}进口明细 <i>/</i> 直行
              {{ count(focus, "through") ?? "—" }} 辆 <i>·</i> 左转
              {{ count(focus, "left") ?? "—" }} 辆
            </div>
          </section>
          <section class="card events">
            <div class="cardhead">
              <div class="titlegroup">
                <span class="tile gold"><Document /></span>
                <div>
                  <small>EVENT FEED</small>
                  <h2>边缘事件流</h2>
                </div>
              </div>
              <button class="more" @click="section('事件记录')">
                查看全部 <ArrowRight />
              </button>
            </div>
            <div
              v-for="e in events.slice(0, 4)"
              :key="e.ts + e.type"
              class="event"
            >
              <time>{{ fmt(e.ts) }}</time
              ><span :class="['eventtype', e.type]">{{
                evNames[e.type] ?? e.type
              }}</span
              ><strong>{{ eventText(e) }}</strong>
            </div>
            <div v-if="!events.length" class="empty">
              尚未收到边缘变化事件；没有事件不代表感知离线。
            </div>
          </section>
        </div>
        <footer>
          SIGNAL DESK <i>/</i> 只读监测
          <span>{{
            demo
              ? "DEMO · 本地演示，非现场数据"
              : "EDGE TELEMETRY · MQTT → Redis → Web"
          }}</span>
        </footer>
      </main>
    </div>
    <div v-if="panel" class="veil" @click.self="close">
      <section
        class="modal card"
        role="dialog"
        aria-modal="true"
        :aria-label="panel"
      >
        <div class="cardhead">
          <div>
            <small>OPERATIONS INSPECTOR</small>
            <h2>{{ panel }}</h2>
          </div>
          <button @click="close" aria-label="关闭"><Close /></button>
        </div>
        <template v-if="panel === '事件记录'"
          ><select v-model="filter" aria-label="筛选事件">
            <option value="all">全部事件</option>
            <option v-for="(n, k) in evNames" :key="k" :value="k">
              {{ n }}
            </option>
          </select>
          <div v-for="e in filtered" :key="e.ts + e.type" class="event">
            <time>{{ fmt(e.ts) }}</time
            ><span class="eventtype">{{ evNames[e.type] }}</span
            ><strong>{{ eventText(e) }}</strong
            ><small>#{{ e.tick ?? "—" }}</small>
          </div>
          <p v-if="!filtered.length">暂无匹配事件。</p></template
        ><template v-else
          ><p>
            {{
              demo
                ? "本页为演示回放：只用本地样例，不访问设备或后端。"
                : "此页消费云端已有 MQTT 遥测，不向 GD32 下发指令。"
            }}
          </p>
          <dl>
            <dt>数据链路</dt>
            <dd>{{ connection }}</dd>
            <dt>当前灯色依据</dt>
            <dd>{{ demo ? "样例" : sig.source }}</dd>
            <dt>最近感知上报</dt>
            <dd>{{ fmt(f.ts) }}</dd>
            <dt>上报至接收时差¹</dt>
            <dd>{{ latency ?? "—" }} ms</dd>
            <dt>最近事件 Tick</dt>
            <dd>{{ realTick ?? "—" }}</dd>
            <dt>降级状态</dt>
            <dd>{{ f.degradation ?? "—" }}</dd>
          </dl>
          <p>
            ¹ 需要服务器与边缘主机校时，不是网络 RTT。4
            秒无新鲜样本会标记过期；策略建议不会直接点亮绿灯。
          </p>
          <button v-if="demo" @click="router.push('/dashboard')">
            前往现场监测 <ArrowRight /></button
          ><button v-else @click="logout">
            <SwitchButton /> 退出登录
          </button></template
        >
      </section>
    </div>
  </div>
</template>
<style src="../desk/desk.css" scoped></style>
<style src="../terrain/workbench.css" scoped></style>
