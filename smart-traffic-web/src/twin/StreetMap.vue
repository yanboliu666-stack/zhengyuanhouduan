<script setup lang="ts">
import { arms, lamp, type Stage } from "./state";
const p = defineProps<{
  stage: Stage;
  phase?: string | null;
  zoom: number;
  selected: number;
}>();
const emit = defineEmits<{ select: [number] }>();
const color = {
  green: "#8cedaa",
  yellow: "#f3bf65",
  red: "#ef8878",
  flash: "#f3bf65",
  off: "#49534e",
  unknown: "#66726b",
};
const pt = (x: number, y: number, z = 0) => [
  360 + (x - y) * 1.13,
  219 + (x + y) * 0.52 - z,
];
const point = (x: number, y: number, z = 0) => pt(x, y, z).join(",");
const rect = (x: number, y: number, w: number, d: number, z = 0) =>
  [
    [x, y],
    [x + w, y],
    [x + w, y + d],
    [x, y + d],
  ]
    .map(([a, b]) => point(a!, b!, z))
    .join(" ");
const rot = (x: number, y: number, i: number) =>
  [
    [x, y],
    [-y, x],
    [-x, -y],
    [y, -x],
  ][i] as [number, number];
const rp = (x: number, y: number, i: number, z = 0) =>
  point(...rot(x, y, i), z);
const rr = (x: number, y: number, w: number, d: number, i: number, z = 0) =>
  [
    [x, y],
    [x + w, y],
    [x + w, y + d],
    [x, y + d],
  ]
    .map(([a, b]) => rp(a!, b!, i, z))
    .join(" ");
const boxes = Array.from({ length: 4 }, (_, i) =>
  [
    [61, 67, 43, 30, 23],
    [122, 68, 51, 33, 37],
    [68, 127, 33, 44, 36],
    [127, 125, 42, 40, 16],
  ].map(([x, y, w, d, h]) => {
    const corners = [
      [x!, y!],
      [x! + w!, y! + d!],
    ].map(([a, b]) => rot(a!, b!, i));
    return {
      x: Math.min(...corners.map((c) => c[0])),
      y: Math.min(...corners.map((c) => c[1])),
      w: i % 2 ? d! : w!,
      d: i % 2 ? w! : d!,
      h: h!,
      i,
    };
  }),
)
  .flat()
  .sort((a, b) => a.x + a.y + a.w + a.d - b.x - b.y - b.w - b.d);
const trees = Array.from({ length: 4 }, (_, i) =>
  [
    [52, 79],
    [52, 105],
    [79, 52],
    [108, 52],
    [143, 52],
    [52, 150],
  ].map(([x, y]) => pt(...rot(x!, y!, i))),
)
  .flat()
  .sort((a, b) => a[1]! - b[1]!);
const pos = (x: number, y: number, i: number) => `translate(${rp(x, y, i)})`;
</script>
<template>
  <svg
    class="city"
    viewBox="0 0 720 420"
    role="img"
    aria-label="四进口轴测路口示意，方向标签可选择车道详情"
  >
    <defs>
      <pattern id="dots" width="14" height="14" patternUnits="userSpaceOnUse">
        <circle cx="1" cy="1" r=".7" fill="#414c45" />
      </pattern>
      <radialGradient id="base">
        <stop stop-color="#293b30" />
        <stop offset="1" stop-color="#141c19" />
      </radialGradient>
      <filter id="shine"><feGaussianBlur stdDeviation="3" /></filter>
    </defs>
    <rect width="720" height="420" fill="url(#base)" />
    <rect width="720" height="420" fill="url(#dots)" />
    <g :transform="`translate(360 213) scale(${p.zoom}) translate(-360 -213)`">
      <g stroke="#304038" stroke-width=".65" opacity=".65">
        <template v-for="i in 23" :key="i">
          <polyline
            :points="
              point(-250 + i * 22, -270) + ' ' + point(-250 + i * 22, 270)
            "
          />
          <polyline
            :points="
              point(-270, -250 + i * 22) + ' ' + point(270, -250 + i * 22)
            "
          />
        </template>
      </g>
      <polygon
        :points="rect(-196, -196, 392, 392, -4)"
        fill="#18241d"
        stroke="#4b5a50"
      />
      <polygon
        :points="rect(-196, -196, 392, 392)"
        fill="#28332e"
        stroke="#59665c"
      />
      <g v-for="(_, i) in arms" :key="i">
        <polygon
          :points="rr(44, 44, 150, 150, i)"
          fill="#435047"
          stroke="#879488"
          stroke-width=".8"
        />
        <polyline
          :points="rp(-1, -194, i) + ' ' + rp(-1, -50, i)"
          stroke="#ad9e70"
        />
        <polyline
          :points="rp(1, -194, i) + ' ' + rp(1, -50, i)"
          stroke="#ad9e70"
        />
        <polyline
          v-for="x in [-22, 22]"
          :key="x"
          :points="rp(x, -194, i) + ' ' + rp(x, -61, i)"
          stroke="#a1aba1"
          stroke-dasharray="8 7"
          stroke-width="1.25"
        />
        <polygon
          v-for="j in 12"
          :key="j"
          :points="rr(-41 + j * 6, -53, 3.1, 10, i)"
          fill="#c0cabe"
        />
        <polygon :points="rr(-41, -60, 38, 2, i)" fill="#d0d5c9" />
        <polyline
          v-if="lamp(stage, phase, arms[i]![3]) === 'green'"
          :points="rp(-12, -177, i) + ' ' + rp(-12, 33, i)"
          stroke="#a9efad"
          stroke-width="3"
          stroke-dasharray="6 9"
          class="flow"
        />
      </g>
      <g
        v-for="(b, k) in boxes"
        :key="'b' + k"
        stroke-width=".85"
        stroke="#748378"
        stroke-linejoin="round"
      >
        <polygon
          :points="
            [
              point(b.x, b.y + b.d),
              point(b.x + b.w, b.y + b.d),
              point(b.x + b.w, b.y + b.d, b.h),
              point(b.x, b.y + b.d, b.h),
            ].join(' ')
          "
          fill="#36433c"
        />
        <polygon
          :points="
            [
              point(b.x + b.w, b.y),
              point(b.x + b.w, b.y + b.d),
              point(b.x + b.w, b.y + b.d, b.h),
              point(b.x + b.w, b.y, b.h),
            ].join(' ')
          "
          fill="#28362e"
        />
        <g stroke="#586a5c" stroke-width="1.1">
          <polyline
            v-for="f in Math.floor(b.h / 8)"
            :key="f"
            :points="
              point(b.x, b.y + b.d, f * 7) +
              ' ' +
              point(b.x + b.w, b.y + b.d, f * 7) +
              ' ' +
              point(b.x + b.w, b.y, f * 7)
            "
          />
        </g>
        <polygon :points="rect(b.x, b.y, b.w, b.d, b.h)" fill="#56645a" />
        <polygon
          :points="rect(b.x + 3, b.y + 3, b.w - 6, b.d - 6, b.h + 0.3)"
          fill="#48574d"
        />
        <polygon
          :points="rect(b.x + 7, b.y + 7, 10, 7, b.h + 1)"
          fill="#34443a"
        />
        <polygon
          :points="rect(b.x + 8, b.y + 6, 10, 7, b.h + 3)"
          fill="#68786b"
        />
      </g>
      <g
        v-for="(v, k) in trees"
        :key="'t' + k"
        :transform="`translate(${v.join(',')})`"
      >
        <ellipse rx="6" ry="2.8" fill="#314137" />
        <path d="M0 0v-7" stroke="#929d8e" />
        <path
          d="M-5 -6l1 -7 4 -4 5 4 1 6 -6 3z"
          fill="#536957"
          stroke="#788b76"
          stroke-width=".65"
        />
      </g>
      <g v-for="(a, i) in arms" :key="a[0]" :transform="pos(-34, -66, i)">
        <path d="M0 0v-17" stroke="#c7d0c6" />
        <circle
          cy="-19"
          r="8"
          :fill="color[lamp(stage, phase, a[3])]"
          opacity=".5"
          filter="url(#shine)"
        />
        <circle
          cy="-19"
          r="4.4"
          :fill="color[lamp(stage, phase, a[3])]"
          stroke="#17241e"
        />
      </g>
      <g
        v-for="(a, i) in arms"
        :key="a[3]"
        :transform="pos(0, -170, i)"
        class="maplabel"
        @click="emit('select', i)"
        @keydown.enter="emit('select', i)"
        tabindex="0"
        role="button"
        :aria-label="a[1] + '进口详情'"
      >
        <rect
          x="-24"
          y="-13"
          width="48"
          height="24"
          rx="4"
          fill="#19211d"
          :stroke="selected === i ? '#ff9665' : '#758479'"
        />
        <text text-anchor="middle" y="3" fill="#e5eee3" font-size="11">
          {{ a[0] }} · {{ a[1] }}
        </text>
      </g>
    </g>
  </svg>
</template>
<style scoped>
.city polyline {
  fill: none;
}
.city {
  width: 100%;
  height: 100%;
  display: block;
}
.maplabel {
  cursor: pointer;
}
.maplabel:hover rect {
  stroke: white;
}
.flow {
  animation: travel 1.8s linear infinite;
}
@keyframes travel {
  to {
    stroke-dashoffset: -60;
  }
}
@media (prefers-reduced-motion: reduce) {
  .flow {
    animation: none;
  }
}
</style>
