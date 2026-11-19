<template>
  <div class="twin-container">
    <!-- 顶部状态抬头栏 -->
    <div class="twin-header">
      <div class="header-left">
        <span class="live-dot"></span>
        <span class="system-title">全息路口数字孪生云控大屏 (Digital Twin Hub)</span>
        <el-tag size="small" type="success" effect="dark" class="sync-badge">
          MQTT 边缘毫秒级同步中
        </el-tag>
      </div>

      <div class="header-right">
        <span class="label">孪生目标路口：</span>
        <el-select v-model="selectedJunction" class="junction-select" @change="handleJunctionChange">
          <el-option
            v-for="item in junctionList"
            :key="item.id"
            :label="item.name"
            :value="item.id"
          />
        </el-select>
        <span class="clock-display">⏱ {{ currentTime }}</span>
      </div>
    </div>

    <!-- 主展示区：三栏布局 -->
    <div class="twin-grid">
      <!-- 左侧：边缘决策态势与指标 -->
      <div class="column-panel left-col">
        <!-- 边缘自治态势卡片 -->
        <el-card class="tech-card">
          <template #header>
            <div class="card-header">
              <span class="icon">⚡</span>
              <span>边缘端决策态势 (Edge Telemetry)</span>
            </div>
          </template>

          <div class="telemetry-grid">
            <div class="tele-item active-phase">
              <div class="tele-title">当前通行相位</div>
              <div class="tele-value glow-green">{{ twinState.current_phase_id || 'P_W' }}</div>
              <div class="tele-desc">{{ getPhaseDesc(twinState.current_phase_id) }}</div>
            </div>

            <div class="tele-item">
              <div class="tele-title">控制运行模式</div>
              <div class="tele-tag-box">
                <el-tag :type="getModeTagType(twinState.mode)" effect="dark" size="large">
                  {{ (twinState.mode || 'NORMAL').toUpperCase() }}
                </el-tag>
              </div>
              <div class="tele-desc">边缘自适应算法</div>
            </div>

            <div class="tele-item">
              <div class="tele-title">降级容灾状态</div>
              <div class="tele-tag-box">
                <el-tag :type="twinState.degradation === 'normal' ? 'success' : 'warning'" effect="plain">
                  {{ twinState.degradation === 'normal' ? '正常 (NORMAL)' : '降级 (PARTIAL)' }}
                </el-tag>
              </div>
              <div class="tele-desc">无缝安全兜底</div>
            </div>

            <div class="tele-item">
              <div class="tele-title">边缘决策 Tick</div>
              <div class="tele-value tick-num">#{{ twinState.tick_id || '2724' }}</div>
              <div class="tele-desc">10Hz 控制节拍</div>
            </div>
          </div>
        </el-card>

        <!-- 交通感知流态指标 -->
        <el-card class="tech-card mt-3">
          <template #header>
            <div class="card-header">
              <span class="icon">📊</span>
              <span>全息交通流实时感知</span>
            </div>
          </template>

          <div class="metric-grid">
            <div class="m-card">
              <div class="m-num">{{ trafficMetrics.vehicleCount }} <small>pcu</small></div>
              <div class="m-label">当前总车流</div>
            </div>
            <div class="m-card">
              <div class="m-num">{{ trafficMetrics.avgSpeed }} <small>km/h</small></div>
              <div class="m-label">平均车速</div>
            </div>
            <div class="m-card">
              <div class="m-num">{{ trafficMetrics.delayTime }} <small>s</small></div>
              <div class="m-label">平均延误</div>
            </div>
            <div class="m-card">
              <div class="m-num glow-green">{{ trafficMetrics.level }}</div>
              <div class="m-label">服务水平</div>
            </div>
          </div>
        </el-card>
      </div>

      <!-- 中间：核心数字孪生 3D 沙盘 (全四向真实信号灯 + 车流动画) -->
      <div class="column-panel center-col">
        <el-card class="tech-card sandbox-card">
          <template #header>
            <div class="card-header justify-between">
              <div>
                <span class="icon">🚦</span>
                <span>数字孪生路口沙盘 ({{ selectedJunction }})</span>
              </div>
              <div class="phase-banner">
                当前放行：<strong class="glow-text">{{ getPhaseDesc(twinState.current_phase_id) }}</strong>
              </div>
            </div>
          </template>

          <div class="sandbox-canvas">
            <!-- 1. 北向信号灯 (North) -->
            <div class="signal-housing signal-north">
              <div class="signal-label">北 (N)</div>
              <div class="signal-frame">
                <div :class="['lamp', 'red', { lit: getLightColor('north') === 'red' }]"></div>
                <div :class="['lamp', 'yellow', { lit: getLightColor('north') === 'yellow' }]"></div>
                <div :class="['lamp', 'green', { lit: getLightColor('north') === 'green' }]"></div>
              </div>
            </div>

            <!-- 2. 南向信号灯 (South) -->
            <div class="signal-housing signal-south">
              <div class="signal-frame">
                <div :class="['lamp', 'red', { lit: getLightColor('south') === 'red' }]"></div>
                <div :class="['lamp', 'yellow', { lit: getLightColor('south') === 'yellow' }]"></div>
                <div :class="['lamp', 'green', { lit: getLightColor('south') === 'green' }]"></div>
              </div>
              <div class="signal-label">南 (S)</div>
            </div>

            <!-- 3. 西向信号灯 (West) -->
            <div class="signal-housing signal-west">
              <div class="signal-label">西 (W)</div>
              <div class="signal-frame horizontal">
                <div :class="['lamp', 'red', { lit: getLightColor('west') === 'red' }]"></div>
                <div :class="['lamp', 'yellow', { lit: getLightColor('west') === 'yellow' }]"></div>
                <div :class="['lamp', 'green', { lit: getLightColor('west') === 'green' }]"></div>
              </div>
            </div>

            <!-- 4. 东向信号灯 (East) -->
            <div class="signal-housing signal-east">
              <div class="signal-frame horizontal">
                <div :class="['lamp', 'red', { lit: getLightColor('east') === 'red' }]"></div>
                <div :class="['lamp', 'yellow', { lit: getLightColor('east') === 'yellow' }]"></div>
                <div :class="['lamp', 'green', { lit: getLightColor('east') === 'green' }]"></div>
              </div>
              <div class="signal-label">东 (E)</div>
            </div>

            <!-- 十字路口道路拓扑 -->
            <div class="crossroad-roadbed">
              <!-- 北路面 & 斑马线 -->
              <div class="road-arm road-north">
                <div class="lane-divider-v"></div>
                <div class="zebra-stripe zebra-h top-zebra"></div>
                <!-- 南北绿灯时的动态流动车流粒子 -->
                <div v-if="isNorthSouthGreen" class="traffic-particle particle-ns particle-ns-1"></div>
                <div v-if="isNorthSouthGreen" class="traffic-particle particle-sn particle-sn-1"></div>
              </div>

              <!-- 南路面 & 斑马线 -->
              <div class="road-arm road-south">
                <div class="lane-divider-v"></div>
                <div class="zebra-stripe zebra-h bottom-zebra"></div>
              </div>

              <!-- 西路面 & 斑马线 -->
              <div class="road-arm road-west">
                <div class="lane-divider-h"></div>
                <div class="zebra-stripe zebra-v left-zebra"></div>
                <!-- 东西绿灯时的动态流动车流粒子 -->
                <div v-if="isEastWestGreen" class="traffic-particle particle-we particle-we-1"></div>
                <div v-if="isEastWestGreen" class="traffic-particle particle-ew particle-ew-1"></div>
              </div>

              <!-- 东路面 & 斑马线 -->
              <div class="road-arm road-east">
                <div class="lane-divider-h"></div>
                <div class="zebra-stripe zebra-v right-zebra"></div>
              </div>

              <!-- 交叉口核心中央环岛 -->
              <div class="intersection-center">
                <div class="radar-scan"></div>
                <div class="center-content">
                  <div class="junction-tag">{{ selectedJunction }}</div>
                  <div class="junction-state-tag">{{ twinState.mode?.toUpperCase() || 'NORMAL' }}</div>
                </div>
              </div>
            </div>
          </div>
        </el-card>
      </div>

      <!-- 右侧：边缘告警流水 & 车道级排队感知 -->
      <div class="column-panel right-col">
        <!-- 实时告警流水 -->
        <el-card class="tech-card">
          <template #header>
            <div class="card-header justify-between">
              <div>
                <span class="icon">🚨</span>
                <span>边缘端实时告警流水</span>
              </div>
              <el-badge :value="alerts.length" :max="99" class="alert-badge" type="danger" />
            </div>
          </template>

          <div class="alarm-flow-list">
            <div v-for="alarm in alerts" :key="alarm.id" class="alarm-card">
              <div class="alarm-top">
                <el-tag size="small" :type="alarm.level === 'warning' ? 'warning' : 'danger'" effect="dark">
                  {{ alarm.alarm_type || alarm.type || 'ALARM' }}
                </el-tag>
                <span class="alarm-tick">Tick: #{{ alarm.tick_id || '2724' }}</span>
              </div>
              <div class="alarm-body">
                {{ alarm.detail?.reason || alarm.description || 'controller_not_normal / 降级策略生效' }}
              </div>
            </div>
            <div v-if="alerts.length === 0" class="no-alarm">
              <span>🛡 边缘感知节点正常，未发生异常告警</span>
            </div>
          </div>
        </el-card>

        <!-- 车道排队感知 -->
        <el-card class="tech-card mt-3">
          <template #header>
            <div class="card-header">
              <span class="icon">📈</span>
              <span>进口道排队长度实时感知</span>
            </div>
          </template>

          <div class="queue-list">
            <div class="queue-row">
              <div class="q-label">北进口 (直行)</div>
              <el-progress :percentage="isNorthSouthGreen ? 25 : 78" :status="isNorthSouthGreen ? 'success' : 'warning'" :stroke-width="10" />
            </div>
            <div class="queue-row">
              <div class="q-label">南进口 (直行)</div>
              <el-progress :percentage="isNorthSouthGreen ? 30 : 82" :status="isNorthSouthGreen ? 'success' : 'exception'" :stroke-width="10" />
            </div>
            <div class="queue-row">
              <div class="q-label">东进口 (左转/直行)</div>
              <el-progress :percentage="isEastWestGreen ? 20 : 65" :status="isEastWestGreen ? 'success' : 'warning'" :stroke-width="10" />
            </div>
            <div class="queue-row">
              <div class="q-label">西进口 (左转/直行)</div>
              <el-progress :percentage="isEastWestGreen ? 15 : 55" :status="isEastWestGreen ? 'success' : 'warning'" :stroke-width="10" />
            </div>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { trafficApi, type RealtimeState } from '../api/traffic'

const selectedJunction = ref('mini_1')
const currentTime = ref('')
let timer: any = null
let clockTimer: any = null

const junctionList = ref([
  { id: 'mini_1', name: 'mini_1 (边缘端智能机)' },
  { id: 'INT_001', name: 'INT_001 (中山路与解放路)' },
  { id: 'INT_002', name: 'INT_002 (建设大道与科技路)' }
])

const twinState = reactive<RealtimeState>({
  junction_id: 'mini_1',
  current_phase_id: 'P_W',
  mode: 'normal',
  degradation: 'normal',
  tick_id: '2724',
  signal_colors: {
    north_through: 'red',
    south_through: 'red',
    east_through: 'green',
    west_through: 'green'
  }
})

const trafficMetrics = reactive({
  vehicleCount: 152,
  avgSpeed: 41.2,
  delayTime: 16.5,
  level: '畅通'
})

const alerts = ref<any[]>([])

// 计算当前是否为南北绿灯
const isNorthSouthGreen = computed(() => {
  return getLightColor('north') === 'green' || getLightColor('south') === 'green'
})

// 计算当前是否为东西绿灯
const isEastWestGreen = computed(() => {
  return getLightColor('east') === 'green' || getLightColor('west') === 'green'
})

// 获取四向红绿灯状态
const getLightColor = (direction: 'north' | 'south' | 'east' | 'west') => {
  const mode = (twinState.mode || 'normal').toLowerCase()
  if (mode === 'all_red') return 'red'
  if (mode === 'clearance') return 'yellow'

  const colors = twinState.signal_colors as any
  if (colors && colors[direction]) {
    return colors[direction]
  }
  if (colors && colors[`${direction}_through`]) {
    return colors[`${direction}_through`]
  }

  // 根据当前相位回退推算
  const phase = (twinState.current_phase_id || 'P_W').toUpperCase()
  if (phase.includes('N') || phase.includes('S')) {
    return (direction === 'north' || direction === 'south') ? 'green' : 'red'
  } else {
    return (direction === 'east' || direction === 'west') ? 'green' : 'red'
  }
}

const getPhaseDesc = (phaseId: string = '') => {
  const p = (phaseId || '').toUpperCase()
  if (p.includes('W') || p.includes('E') || p === '2' || p === '3') {
    return '东西主干道放行 (East-West Green)'
  }
  if (p.includes('N') || p.includes('S') || p === '0' || p === '1') {
    return '南北主干道放行 (North-South Green)'
  }
  return '全向相位协调中'
}

const getModeTagType = (mode: string = '') => {
  const m = mode.toLowerCase()
  if (m === 'normal') return 'success'
  if (m === 'all_red') return 'danger'
  if (m === 'clearance') return 'warning'
  return 'info'
}

const updateClock = () => {
  currentTime.value = new Date().toLocaleTimeString()
}

// 核心拉取函数：安全健壮解析
const fetchAllData = async () => {
  try {
    const resState: any = await trafficApi.getJunctionRealtimeState(selectedJunction.value)
    const stateData = resState?.data?.data || resState?.data || resState
    if (stateData && typeof stateData === 'object') {
      Object.assign(twinState, stateData)
    }

    const resMetrics: any = await trafficApi.getRealtimeData(selectedJunction.value)
    const metricData = resMetrics?.data?.data || resMetrics?.data || resMetrics
    if (metricData && typeof metricData === 'object') {
      Object.assign(trafficMetrics, metricData)
    }

    const resAlerts: any = await trafficApi.getAlerts(selectedJunction.value)
    const alertList = resAlerts?.data?.data || resAlerts?.data || resAlerts
    if (Array.isArray(alertList)) {
      alerts.value = alertList
    }
  } catch (error) {
    console.error('拉取数字孪生数据异常:', error)
  }
}

const handleJunctionChange = () => {
  fetchAllData()
}

onMounted(() => {
  updateClock()
  clockTimer = setInterval(updateClock, 1000)
  fetchAllData()
  // 500ms 高频刷新，与边缘端 MQTT 同步
  timer = setInterval(fetchAllData, 500)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
  if (clockTimer) clearInterval(clockTimer)
})
</script>

<style scoped>
.twin-container {
  padding: 16px;
  background-color: #080d1a;
  min-height: calc(100vh - 60px);
  color: #e2e8f0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

/* 顶部 Header */
.twin-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  background: rgba(15, 23, 42, 0.9);
  border: 1px solid rgba(0, 229, 255, 0.25);
  border-radius: 8px;
  margin-bottom: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.live-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #00ff88;
  box-shadow: 0 0 10px #00ff88;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 255, 136, 0.7); }
  70% { transform: scale(1.15); box-shadow: 0 0 0 10px rgba(0, 255, 136, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 255, 136, 0); }
}

.system-title {
  font-size: 18px;
  font-weight: 700;
  color: #00e5ff;
  letter-spacing: 0.5px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.junction-select {
  width: 240px;
}

.clock-display {
  font-family: monospace;
  font-size: 15px;
  color: #94a3b8;
}

/* 三栏布局 */
.twin-grid {
  display: grid;
  grid-template-columns: 340px 1fr 340px;
  gap: 16px;
}

.tech-card {
  background: rgba(15, 23, 42, 0.8) !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  color: #fff !important;
  border-radius: 8px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #00e5ff;
}

.justify-between {
  justify-content: space-between;
  width: 100%;
}

.phase-banner {
  font-size: 13px;
  color: #94a3b8;
}

.glow-text {
  color: #00ff88;
}

/* 左侧遥测数据 */
.telemetry-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.tele-item {
  background: rgba(0, 0, 0, 0.35);
  padding: 12px;
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.tele-title {
  font-size: 12px;
  color: #94a3b8;
}

.tele-value {
  font-size: 22px;
  font-weight: bold;
  margin: 6px 0;
}

.glow-green {
  color: #00ff88;
  text-shadow: 0 0 10px rgba(0, 255, 136, 0.5);
}

.tick-num {
  color: #38bdf8;
  font-family: monospace;
}

.tele-desc {
  font-size: 11px;
  color: #64748b;
}

.tele-tag-box {
  margin: 6px 0;
}

/* 感知指标 */
.metric-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.m-card {
  background: rgba(0, 0, 0, 0.3);
  padding: 12px;
  border-radius: 6px;
  text-align: center;
}

.m-num {
  font-size: 22px;
  font-weight: bold;
  color: #f8fafc;
}

.m-num small {
  font-size: 12px;
  color: #94a3b8;
}

.m-label {
  font-size: 12px;
  color: #64748b;
  margin-top: 4px;
}

/* 中间沙盘 */
.sandbox-card {
  height: 590px;
  position: relative;
}

.sandbox-canvas {
  width: 100%;
  height: 500px;
  position: relative;
  background: radial-gradient(circle at center, #131c31 0%, #080d1a 100%);
  border-radius: 6px;
  display: flex;
  justify-content: center;
  align-items: center;
  overflow: hidden;
}

/* 道路底座 */
.crossroad-roadbed {
  width: 320px;
  height: 320px;
  position: relative;
  background: #1e293b;
  border-radius: 8px;
}

/* 四个路口臂 */
.road-arm {
  position: absolute;
  background: #1e293b;
}

.road-north {
  top: -100px;
  left: 90px;
  width: 140px;
  height: 100px;
  border-left: 2px solid #475569;
  border-right: 2px solid #475569;
}

.road-south {
  bottom: -100px;
  left: 90px;
  width: 140px;
  height: 100px;
  border-left: 2px solid #475569;
  border-right: 2px solid #475569;
}

.road-west {
  left: -100px;
  top: 90px;
  width: 100px;
  height: 140px;
  border-top: 2px solid #475569;
  border-bottom: 2px solid #475569;
}

.road-east {
  right: -100px;
  top: 90px;
  width: 100px;
  height: 140px;
  border-top: 2px solid #475569;
  border-bottom: 2px solid #475569;
}

.lane-divider-v {
  position: absolute;
  left: 50%;
  top: 0;
  bottom: 0;
  width: 2px;
  border-left: 2px dashed #eab308;
}

.lane-divider-h {
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 2px;
  border-top: 2px dashed #eab308;
}

/* 斑马线 */
.zebra-stripe {
  position: absolute;
}
.zebra-h {
  width: 140px;
  height: 14px;
  background: repeating-linear-gradient(90deg, #fff 0, #fff 10px, transparent 10px, transparent 20px);
}
.top-zebra { bottom: 0; }
.bottom-zebra { top: 0; }

.zebra-v {
  width: 14px;
  height: 140px;
  background: repeating-linear-gradient(0deg, #fff 0, #fff 10px, transparent 10px, transparent 20px);
}
.left-zebra { right: 0; }
.right-zebra { left: 0; }

/* 交叉中心环岛 */
.intersection-center {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 130px;
  height: 130px;
  background: rgba(14, 165, 233, 0.15);
  border: 2px solid #0284c7;
  border-radius: 50%;
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 10;
}

.radar-scan {
  position: absolute;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  border: 2px dashed rgba(56, 189, 248, 0.4);
  animation: spin 10s linear infinite;
}

@keyframes spin {
  100% { transform: rotate(360deg); }
}

.center-content {
  text-align: center;
}

.junction-tag {
  font-weight: bold;
  font-size: 15px;
  color: #f8fafc;
}

.junction-state-tag {
  font-size: 11px;
  color: #38bdf8;
  margin-top: 2px;
}

/* 四向信号灯外观 */
.signal-housing {
  position: absolute;
  z-index: 25;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.signal-north { top: 15px; }
.signal-south { bottom: 15px; }
.signal-west { left: 25px; flex-direction: row; }
.signal-east { right: 25px; flex-direction: row; }

.signal-label {
  font-size: 13px;
  font-weight: 700;
  color: #cbd5e1;
}

.signal-frame {
  background: #090d16;
  padding: 6px 8px;
  border-radius: 20px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  border: 2px solid #334155;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.6);
}

.signal-frame.horizontal {
  flex-direction: row;
}

.lamp {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  opacity: 0.15;
  transition: all 0.2s ease-in-out;
}

.lamp.red { background: #ef4444; }
.lamp.yellow { background: #eab308; }
.lamp.green { background: #22c55e; }

.lamp.red.lit {
  opacity: 1;
  box-shadow: 0 0 16px #ef4444, 0 0 4px #fff;
}

.lamp.yellow.lit {
  opacity: 1;
  box-shadow: 0 0 16px #eab308, 0 0 4px #fff;
}

.lamp.green.lit {
  opacity: 1;
  box-shadow: 0 0 16px #22c55e, 0 0 4px #fff;
}

/* 车流动画粒子 */
.traffic-particle {
  position: absolute;
  width: 8px;
  height: 16px;
  background: #38bdf8;
  border-radius: 3px;
  box-shadow: 0 0 8px #38bdf8;
}

.particle-ns-1 {
  left: 30px;
  animation: moveNorthSouth 2s infinite linear;
}
.particle-sn-1 {
  right: 30px;
  animation: moveSouthNorth 2s infinite linear;
}

.particle-we-1 {
  top: 30px;
  width: 16px;
  height: 8px;
  animation: moveWestEast 2s infinite linear;
}
.particle-ew-1 {
  bottom: 30px;
  width: 16px;
  height: 8px;
  animation: moveEastWest 2s infinite linear;
}

@keyframes moveNorthSouth {
  0% { top: -80px; opacity: 0; }
  20% { opacity: 1; }
  80% { opacity: 1; }
  100% { top: 400px; opacity: 0; }
}

@keyframes moveSouthNorth {
  0% { bottom: -80px; opacity: 0; }
  20% { opacity: 1; }
  80% { opacity: 1; }
  100% { bottom: 400px; opacity: 0; }
}

@keyframes moveWestEast {
  0% { left: -80px; opacity: 0; }
  20% { opacity: 1; }
  80% { opacity: 1; }
  100% { left: 400px; opacity: 0; }
}

@keyframes moveEastWest {
  0% { right: -80px; opacity: 0; }
  20% { opacity: 1; }
  80% { opacity: 1; }
  100% { right: 400px; opacity: 0; }
}

/* 右侧告警与排队 */
.alarm-flow-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 220px;
  overflow-y: auto;
}

.alarm-card {
  background: rgba(239, 68, 68, 0.12);
  border-left: 3px solid #ef4444;
  padding: 8px 12px;
  border-radius: 4px;
}

.alarm-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.alarm-tick {
  font-size: 11px;
  color: #94a3b8;
  font-family: monospace;
}

.alarm-body {
  font-size: 12px;
  color: #f1f5f9;
  margin-top: 4px;
}

.no-alarm {
  padding: 24px 0;
  text-align: center;
  font-size: 12px;
  color: #64748b;
}

.queue-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.queue-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.q-label {
  font-size: 12px;
  color: #94a3b8;
}

.mt-3 { margin-top: 14px; }
</style>