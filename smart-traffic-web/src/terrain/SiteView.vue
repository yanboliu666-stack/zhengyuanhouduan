<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, computed } from "vue";
import { Refresh, ZoomIn, ZoomOut, View } from "@element-plus/icons-vue";
import { arms } from "./site";
import {
  dirs,
  color,
  text,
  type Stage,
  type Lamp,
} from "../desk/feed";
import type { buildModel } from "./model";
import Junction from "../desk/Junction.vue";
const props = defineProps<{
  stage: Stage;
  phase: string;
  focus: number;
  labels: boolean;
  binding: string[];
  counts: (number | null)[];
  confirmed: boolean;
  demo: boolean;
  lampColors?: Lamp[];
}>();
const emit = defineEmits<{ select: [number] }>();
const host = ref<HTMLDivElement>(),
  fallback = ref(false),
  ready = ref(false),
  top = ref(false),
  bearing = ref(0),
  pins = ref<{ x: number; y: number; visible: boolean }[]>([]);
let model: ReturnType<typeof buildModel> | undefined,
  dead = false;
const lamps = computed(() => {
  if (props.lampColors) return props.lampColors;
  return arms.map((_, i) =>
    props.binding[i]
      ? color(props.stage, props.phase, props.binding[i]!)
      : "unknown",
  );
});
const counts = computed(() =>
  arms.map(
    (_, i) =>
      props.counts[dirs.findIndex((d) => d[3] === props.binding[i])] ?? null,
  ),
);
function update() {
  model?.update(lamps.value, counts.value);
}
watch([lamps, counts], update);
function lose(e: Event) {
  e.preventDefault();
  fallback.value = true;
  ready.value = false;
  model?.dispose();
  model = undefined;
}
onMounted(async () => {
  try {
    const { buildModel } = await import("./model");
    if (dead || !host.value) return;
    model = buildModel(host.value, (p, n) => {
      pins.value = p;
      bearing.value = n;
    });
    host.value
      .querySelector("canvas")
      ?.addEventListener("webglcontextlost", lose, { once: true });
    ready.value = true;
    update();
  } catch {
    fallback.value = true;
  }
});
onBeforeUnmount(() => {
  dead = true;
  model?.dispose();
});
function setView(t: boolean) {
  top.value = t;
  model?.home(t);
}
function select(i: number) {
  const d = dirs.findIndex((d) => d[3] === props.binding[i]);
  if (d >= 0) emit("select", d);
}
const sites = ["双溪口桥", "坑口 C 区", "月山路", "双溪口 2 号桥"];
function place(i: number) {
  const p = pins.value[i];
  return p && p.visible
    ? { left: p.x + "px", top: p.y + "px" }
    : { display: "none" };
}
</script>
<template>
  <div class="terrain">
    <div ref="host" class="gl" aria-label="南环路与双溪路可交互三维模型" />
    <template v-if="!fallback"
      ><div class="cornertag"><i /> PAN'AN <em>/</em> SITE 01</div>
      <span class="comp" :style="{ transform: `rotate(${-bearing}deg)` }"
        >▲<small>N</small></span
      >
      <div v-if="!ready" class="loading">正在构建三维地形…</div>
      <template v-if="ready"
        ><button
          v-for="(a, i) in arms"
          :key="a.name"
          class="pin"
          :data-state="lamps[i]"
          :title="a.name + ' · ' + text[lamps[i]!]"
          :style="place(i)"
          @click="select(i)"
        >
          <span class="lens"
            ><i
              v-for="c in ['red', 'yellow', 'green']"
              :key="c"
              :class="{
                [c]: lamps[i] === c || (c === 'yellow' && lamps[i] === 'flash'),
              }" /></span
          ><b>{{ binding[i] || "—" }}</b
          ><small v-if="labels">{{ a.short }}</small></button
        ><template v-if="labels"
          ><span
            v-for="(s, j) in sites"
            :key="s"
            class="poi"
            :style="place(j + 4)"
            >{{ s }}</span
          ></template
        ></template
      >
      <div class="viewtools">
        <button
          title="放大"
          aria-label="放大三维模型"
          @click="model?.zoom(0.84)"
        >
          <ZoomIn /></button
        ><button
          title="缩小"
          aria-label="缩小三维模型"
          @click="model?.zoom(1.18)"
        >
          <ZoomOut /></button
        ><button
          title="恢复初始视角"
          aria-label="恢复初始视角"
          @click="setView(false)"
        >
          <Refresh /></button
        ><button @click="setView(!top)">
          <View />{{ top ? "鸟瞰" : "俯视" }}
        </button>
      </div>
      <span class="instruction">拖动旋转 · 滚轮缩放</span></template
    >
    <div v-else class="fallback">
      <b>当前浏览器不支持 WebGL 2 · 二维信号监测</b
      ><Junction
        :stage="stage"
        :phase="phase"
        :focus="focus"
        :grid="true"
        @select="emit('select', $event)"
      />
    </div>
  </div>
  <div class="sitecaption">
    <strong>3D 地形重建</strong><span>参考地图建模 · 非测绘</span
    ><b>{{
      demo ? "演示绑定" : confirmed ? "进口已配置核验" : "预设绑定 · 待现场核对"
    }}</b>
  </div>
  <div class="lampdock">
    <button
      v-for="(a, i) in arms"
      :key="a.short"
      :class="{ on: binding[i] === dirs[focus]?.[3] }"
      @click="select(i)"
    >
      <span class="threebulbs"
        ><i
          v-for="c in ['red', 'yellow', 'green']"
          :key="c"
          :class="{
            [c]: lamps[i] === c || (c === 'yellow' && lamps[i] === 'flash'),
          }" /></span
      ><strong>{{ a.short }}</strong
      ><small>{{ binding[i] || "—" }} · {{ text[lamps[i]!] }}</small>
    </button>
  </div>
</template>
<style scoped>
.terrain {
  width: 100%;
  height: clamp(390px, 36vw, 550px);
  position: relative;
  overflow: hidden;
  background: #213e49;
  color: white;
}
.gl,
.fallback {
  position: absolute;
  inset: 0;
}
.gl :deep(canvas) {
  width: 100%;
  height: 100%;
  display: block;
  touch-action: none;
  cursor: grab;
}
.gl :deep(canvas:active) {
  cursor: grabbing;
}
.cornertag,
.comp,
.poi,
.instruction {
  position: absolute;
  pointer-events: none;
}
.cornertag {
  font:
    600 10px ui-monospace,
    monospace;
  letter-spacing: 0.12em;
  top: 15px;
  left: 15px;
  padding: 6px 8px;
  background: #183640cf;
  border: 1px solid #aacaaf55;
  border-radius: 4px;
  color: #dceee0;
  display: flex;
  gap: 7px;
  align-items: center;
}
.cornertag i {
  width: 5px;
  height: 5px;
  background: #c2de9b;
  border-radius: 50%;
}
.cornertag em {
  color: #96b889;
}
.comp {
  top: 12px;
  right: 17px;
  border: 1px solid #adc8c177;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  text-align: center;
  font: 11px/17px monospace;
  background: #1b3944bd;
}
.comp small {
  display: block;
  font: 8px/8px monospace;
}
.terrain .pin {
  position: absolute;
  transform: translate(-50%, -100%);
  border: 1px solid #b8caca99;
  color: #edf7f3;
  background: #152c35f2;
  padding: 4px 6px;
  display: grid;
  grid-template-columns: auto auto;
  grid-template-rows: auto auto;
  gap: 2px 4px;
  box-shadow: 0 2px 5px #0a242b44;
  border-radius: 5px;
  font:
    600 10px/1.1 ui-monospace,
    monospace;
  white-space: nowrap;
}
.pin:after {
  content: "";
  position: absolute;
  left: 50%;
  top: 100%;
  height: 6px;
  border-left: 1px solid white;
}
.pin[data-state="green"] {
  border-color: #7bffc7;
  box-shadow: 0 0 0 2px #3ee79833;
}
.pin small {
  font: 10px sans-serif;
  color: #d1e0df;
  grid-column: 1/-1;
}
.lens {
  display: flex;
  gap: 2px;
}
.lens i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #4e6468;
}
.lens .green {
  background: #51ffab;
  box-shadow: 0 0 5px #6aefa2;
}
.lens .red {
  background: #ff7d75;
}
.lens .yellow {
  background: #ffe28a;
}
.poi {
  font-size: 10px;
  font-weight: 600;
  color: white;
  text-shadow:
    0 1px 3px #113328,
    1px 0 3px #113328;
  transform: translate(-50%, -50%);
  white-space: nowrap;
}
.viewtools {
  position: absolute;
  bottom: 12px;
  left: 12px;
  display: flex;
  gap: 3px;
}
.terrain .viewtools button {
  background: #f9fbf5ef;
  border: 0;
  border-radius: 5px;
  color: #284439;
  font-size: 10px;
  padding: 6px 8px;
}
.viewtools svg {
  width: 14px;
  height: 14px;
}
.instruction {
  bottom: 15px;
  right: 14px;
  color: #e3e9e5;
  font-size: 10px;
}
.sitecaption {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 15px;
  color: #52666a;
  background: #f7faf8;
  border-bottom: 1px solid #dce5df;
  font-size: 10px;
}
.sitecaption strong {
  color: #327c69;
}
.sitecaption b {
  margin-left: auto;
  color: #887044;
  font-weight: 500;
}
.loading {
  position: absolute;
  top: 49%;
  width: 100%;
  text-align: center;
}
.fallback b {
  display: block;
  text-align: center;
  padding: 10px;
  background: #223645;
  font-size: 12px;
}
.fallback svg {
  width: 100%;
  height: calc(100% - 40px);
}
@media (max-width: 640px) {
  .terrain {
    height: 370px;
  }
  .instruction {
    display: none;
  }
  .terrain .pin {
    font-size: 8px;
    padding: 3px;
  }
  .pin small,
  .poi {
    font-size: 8px;
  }
  .lens i {
    width: 6px;
    height: 6px;
  }
  .sitecaption {
    gap: 4px;
    font-size: 9px;
  }
}
:global(.wide) .terrain {
  height: calc(86vh - 110px);
}
.lampdock {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 6px;
  padding: 8px 12px;
  background: #f9fbf7;
}
.lampdock button {
  min-width: 0;
  display: grid;
  text-align: left;
  justify-content: start;
  gap: 3px;
  border: 1px solid #dce4db;
  background: #fff;
  border-radius: 6px;
  padding: 6px 8px;
  color: #24483e;
}
.lampdock .on {
  border-color: #83a996;
  background: #edf5ed;
}
.lampdock strong {
  font-size: 12px;
}
.lampdock small {
  font-size: 10px;
  color: #60756a;
}
.threebulbs {
  display: inline-flex;
  justify-self: start;
  gap: 3px;
  background: #21343b;
  border-radius: 7px;
  padding: 3px 5px;
}
.threebulbs i {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #475960;
}
.threebulbs .red {
  background: #ff746b;
}
.threebulbs .green {
  background: #4cf09f;
}
.threebulbs .yellow {
  background: #ffd56a;
}
@media (max-width: 640px) {
  .lampdock {
    gap: 2px;
    padding: 5px;
  }
  .lampdock button {
    padding: 4px;
  }
  .lampdock strong {
    font-size: 10px;
  }
  .lampdock small {
    font-size: 8px;
  }
  .pin small {
    display: none;
  }
}
</style>
