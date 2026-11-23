<script setup lang="ts">
import { dirs, color, text, type Stage } from "./feed";
const p = defineProps<{
    stage: Stage;
    phase: string;
    focus: number;
    grid: boolean;
  }>(),
  emit = defineEmits<{ select: [number] }>();
const pos = [
  [358, 45],
  [508, 184],
  [358, 320],
  [212, 184],
];
const hue = {
  green: "#46f4a4",
  yellow: "#ffc65a",
  red: "#ff716f",
  flash: "#ffc65a",
  off: "#a6b6c9",
  unknown: "#a6b6c9",
};
const bulb = (i: number) => color(p.stage, p.phase, dirs[i]![3]);
const lit = (i: number, c: string) =>
  bulb(i) === c || (bulb(i) === "flash" && c === "yellow");
</script>
<template>
  <svg
    viewBox="0 0 720 365"
    class="junction"
    role="group"
    aria-label="四进口信号灯与通行方向示意"
  >
    <defs>
      <pattern id="grid2" width="19" height="19" patternUnits="userSpaceOnUse">
        <path d="M19 0H0V19" fill="none" stroke="#2c3951" stroke-width=".7" />
      </pattern>
      <pattern
        id="hatch2"
        width="7"
        height="7"
        patternUnits="userSpaceOnUse"
        patternTransform="rotate(38)"
      >
        <path d="M0 0v7" stroke="#435371" stroke-width="1" />
      </pattern>
      <filter id="glow2" x="-100%" y="-100%" width="300%" height="300%">
        <feGaussianBlur stdDeviation="5" />
      </filter>
      <linearGradient id="road2" x2="1" y2="1">
        <stop stop-color="#354156" />
        <stop offset="1" stop-color="#253248" />
      </linearGradient>
    </defs>
    <rect width="720" height="365" fill="#101b2e" />
    <rect v-if="grid" width="720" height="365" fill="url(#grid2)" />
    <!-- Low-contrast block footprints: the road and lamps carry the live information. -->
    <g
      v-for="(t, k) in [
        'translate(0 0)',
        'translate(720 0) scale(-1 1)',
        'translate(0 365) scale(1 -1)',
        'translate(720 365) scale(-1 -1)',
      ]"
      :key="t"
      :transform="t"
    >
      <path d="M-10 6h200l55 45v50l-12 15H0" fill="#19263c" stroke="#3e506e" />
      <path
        d="M14 16h70v70H14zM94 16h73l44 38v32H94z"
        fill="url(#hatch2)"
        stroke="#354761"
      />
      <path
        d="M-5 103h212q23 0 24-23V49l-40-35"
        fill="none"
        stroke="#465976"
        stroke-width="1.3"
      />
      <text x="18" y="98" font-family="monospace" font-size="7" fill="#8194b1">
        SECTOR / 0{{ k + 1 }}
      </text>
    </g>
    <path
      d="M301 -5h118v116q0 26 28 26h278v93H447q-28 0-28 26v114H301V256q0-26-28-26H-5v-93h278q28 0 28-26Z"
      fill="url(#road2)"
      stroke="#647696"
      stroke-width="2"
    />
    <g
      v-for="i in 4"
      :key="i"
      :transform="`translate(360 184) rotate(${(i - 1) * 90})`"
    >
      <path d="M-2 -360v282m4-282v282" stroke="#b2a278" stroke-width="1.2" />
      <path
        d="M-26 -360v279m52-279v279"
        stroke="#a6b4c9"
        stroke-dasharray="11 9"
        stroke-width="1.3"
      />
      <g :transform="i % 2 ? 'translate(0 0)' : 'scale(.75 1)'">
        <path
          v-for="x in 14"
          :key="x"
          :d="`M${-53 + x * 7} -71v13`"
          stroke="#d1d8e4"
          stroke-width="4.4"
        />
        <path d="M-53-79h50" stroke="#cdd6e4" stroke-width="2.6" />
      </g>
    </g>
    <g
      v-if="stage === 'green'"
      :transform="`translate(360 184) rotate(${
        Math.max(
          0,
          dirs.findIndex((d) => d[3] === phase),
        ) * 90
      })`"
    >
      <rect
        x="-21"
        y="-140"
        width="20"
        height="210"
        rx="10"
        fill="#3bf7aa"
        opacity=".11"
      />
      <path
        d="M-11 -141V68"
        stroke="#65f6bb"
        stroke-width="2.5"
        stroke-dasharray="6 8"
        class="dash"
      />
      <path
        d="m-18 52 7 10 7-10"
        fill="none"
        stroke="#75f7c2"
        stroke-width="3"
      />
    </g>
    <g transform="translate(360 184)">
      <circle r="25" fill="#1c2941" stroke="#6883b1" stroke-dasharray="2 3" />
      <circle r="18" fill="#303f63" stroke="#8b9cd5" />
      <path d="m-9 3 6-11h5L-4 3zm8 5 6-11h5L4 8z" fill="#d5dbff" />
    </g>
    <g
      v-for="(a, i) in dirs"
      :key="a[0]"
      class="head"
      :data-lamp="bulb(i)"
      :transform="`translate(${pos[i]!.join(' ')})`"
      tabindex="0"
      role="button"
      :aria-label="a[1] + '进口：' + text[bulb(i)]"
      @click="emit('select', i)"
      @keydown.enter="emit('select', i)"
      @keydown.space.prevent="emit('select', i)"
    >
      <rect
        x="-61"
        y="-32"
        width="122"
        height="67"
        rx="10"
        fill="#070e1a"
        stroke="#72839c"
        :stroke-width="focus === i ? 2 : 1"
      />
      <text x="-48" y="-13" fill="#f5f7fd" font-size="13" font-weight="bold">
        {{ a[1] }}进口
      </text>
      <text
        x="48"
        y="-13"
        text-anchor="end"
        fill="#aeb9d1"
        font-family="monospace"
        font-size="11"
      >
        {{ a[0] }} / 0{{ i + 1 }}
      </text>
      <g
        v-for="(c, j) in ['red', 'yellow', 'green'] as const"
        :key="c"
        :transform="`translate(${-34 + j * 34} 11)`"
      >
        <circle
          r="13"
          :fill="lit(i, c) ? hue[c] : '#182335'"
          :stroke="lit(i, c) ? hue[c] : '#3a495c'"
        />
        <circle
          v-if="lit(i, c)"
          r="13"
          :fill="hue[c]"
          opacity=".48"
          filter="url(#glow2)"
        />
        <circle
          v-if="lit(i, c)"
          r="7"
          :fill="hue[c]"
          stroke="#fff"
          stroke-opacity=".6"
        />
      </g>
    </g>
    <g
      font-family="monospace"
      fill="#adb9d0"
      font-size="9"
      letter-spacing="1.4"
    >
      <text x="20" y="23">PLAN VIEW / 01</text>
      <text x="700" y="23" text-anchor="end">↑ N</text>
      <text x="20" y="348">SCALE · NTS</text>
      <text x="700" y="348" text-anchor="end">INTERSECTION SCHEMATIC</text>
    </g>
  </svg>
</template>
<style scoped>
.junction {
  width: 100%;
  display: block;
  background: #101b2e;
}
.head {
  cursor: pointer;
}
.head:focus rect,
.head:hover rect {
  stroke: #dedcff;
}
.dash {
  animation: dash 1.4s linear infinite;
}
@keyframes dash {
  to {
    stroke-dashoffset: -56;
  }
}
@media (prefers-reduced-motion: reduce) {
  .dash {
    animation: none;
  }
}
</style>
