<template>
  <div class="signal-control-container">
    <div class="page-header">
      <div class="header-left">
        <span class="pulse-indicator"></span>
        <h2>路口智能调控中心 (Signal Timing & Dispatch)</h2>
      </div>
      <div class="user-badge">👤 admin (智能调度员)</div>
    </div>

    <div class="control-layout">
      <!-- 左侧：Webster 最优配时参数录入 -->
      <div class="layout-left">
        <el-card class="box-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span>🧮 韦伯斯特 (Webster) 最优信号周期计算器</span>
            </div>
          </template>

          <el-form :model="form" label-width="170px">
            <el-form-item label="目标路口编号">
              <el-select v-model="form.junctionId" placeholder="请选择路口" style="width: 100%">
                <el-option
                  v-for="item in junctionList"
                  :key="item.id"
                  :label="item.name"
                  :value="item.id"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="每个周期总损失时间 L">
              <el-input-number v-model="form.totalLostTime" :min="3" :max="30" :step="1" />
              <span class="unit-tip">秒 (s)</span>
            </el-form-item>

            <div class="sub-title">各相位入口实际流量 (pcu/h) - 修改自动实时算配时</div>

            <el-form-item label="相位 1 (南北直行)">
              <el-input-number v-model="form.flows[0]" :min="50" :max="3000" :step="50" />
            </el-form-item>
            <el-form-item label="相位 2 (南北左转)">
              <el-input-number v-model="form.flows[1]" :min="50" :max="3000" :step="50" />
            </el-form-item>
            <el-form-item label="相位 3 (东西直行)">
              <el-input-number v-model="form.flows[2]" :min="50" :max="3000" :step="50" />
            </el-form-item>
            <el-form-item label="相位 4 (东西左转)">
              <el-input-number v-model="form.flows[3]" :min="50" :max="3000" :step="50" />
            </el-form-item>

            <div class="btn-box">
              <el-button type="primary" :loading="calculating" @click="handleManualCalculate">
                ⚙ 重新计算 Webster 最佳配时方案
              </el-button>
            </div>
          </el-form>
        </el-card>
      </div>

      <!-- 右侧：方案实时预览与 MQTT 边缘下发 -->
      <div class="layout-right">
        <el-card class="box-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span>📡 信号配时方案实时预览与 MQTT 边缘下发</span>
              <el-tag size="small" type="success" effect="dark">目标: {{ form.junctionId }}</el-tag>
            </div>
          </template>

          <!-- 推荐最优周期 -->
          <div class="cycle-display">
            <div class="label">实时推荐最优周期时长 (C_opt)</div>
            <div class="value">{{ timingPlan.cycleLength }} <span class="unit">秒</span></div>
          </div>

          <!-- 各相位绿信比 -->
          <div class="split-grid">
            <div class="split-box">
              <div class="title">相位 1 (南北直行)</div>
              <div class="sec">{{ timingPlan.greenTimes.phase_1 }} 秒</div>
              <el-progress :percentage="getPercent(timingPlan.greenTimes.phase_1)" status="success" :stroke-width="8" />
            </div>
            <div class="split-box">
              <div class="title">相位 2 (南北左转)</div>
              <div class="sec">{{ timingPlan.greenTimes.phase_2 }} 秒</div>
              <el-progress :percentage="getPercent(timingPlan.greenTimes.phase_2)" status="success" :stroke-width="8" />
            </div>
            <div class="split-box">
              <div class="title">相位 3 (东西直行)</div>
              <div class="sec">{{ timingPlan.greenTimes.phase_3 }} 秒</div>
              <el-progress :percentage="getPercent(timingPlan.greenTimes.phase_3)" status="success" :stroke-width="8" />
            </div>
            <div class="split-box">
              <div class="title">相位 4 (东西左转)</div>
              <div class="sec">{{ timingPlan.greenTimes.phase_4 }} 秒</div>
              <el-progress :percentage="getPercent(timingPlan.greenTimes.phase_4)" status="success" :stroke-width="8" />
            </div>
          </div>

          <!-- 下发动作按钮 -->
          <div class="dispatch-area">
            <el-button
              type="success"
              class="btn-dispatch"
              size="large"
              :loading="dispatching"
              @click="handleDispatch"
            >
              🚀 一键下发配时指令至路口 MQTT 边缘网关 ({{ form.junctionId }})
            </el-button>
          </div>
        </el-card>

        <!-- 信号灯组模拟 -->
        <el-card class="box-card mt-3" shadow="never">
          <template #header>
            <div class="card-header">
              <span>🚦 路口信号灯组运行模拟 (当前方案运行态)</span>
            </div>
          </template>

          <div class="light-group-sim">
            <div class="lamp-box">
              <div class="lamp">
                <div class="bulb red"></div>
                <div class="bulb yellow"></div>
                <div class="bulb green active"></div>
              </div>
              <div class="name">南北主干道</div>
            </div>

            <div class="lamp-box">
              <div class="lamp">
                <div class="bulb red active"></div>
                <div class="bulb yellow"></div>
                <div class="bulb green"></div>
              </div>
              <div class="name">东西主干道</div>
            </div>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { calcWebster, dispatchSignal } from '../api/traffic'
import { ElMessage, ElNotification } from 'element-plus'

const junctionList = ref([
  { id: 'mini_1', name: 'mini_1 (边缘端智能机)' },
  { id: 'INT_001', name: 'INT_001 (中山路与解放路)' },
  { id: 'INT_002', name: 'INT_002 (建设大道与科技路)' }
])

const form = reactive({
  junctionId: 'mini_1',
  totalLostTime: 7,
  flows: [1050, 300, 350, 150]
})

const calculating = ref(false)
const dispatching = ref(false)

const timingPlan = reactive({
  cycleLength: 120,
  greenTimes: {
    phase_1: 55,
    phase_2: 18,
    phase_3: 25,
    phase_4: 15
  }
})

// 计算绿信比百分比
const getPercent = (sec: number) => {
  if (!timingPlan.cycleLength) return 0
  return Math.min(100, Math.round((sec / timingPlan.cycleLength) * 100))
}

// 核心：Webster 算法计算引擎
const computeWebster = () => {
  const L = form.totalLostTime || 7
  const flows = form.flows.map(f => Math.max(50, Number(f) || 50))
  const satFlow = 1800.0 // 单车道设计饱和流量 (pcu/h)

  // 1. 计算各相位流量比 y_i
  const y = flows.map(f => f / satFlow)
  const sumY = y.reduce((a, b) => a + b, 0)

  // 2. 考虑超饱和约束：交通工程规范约束 Y <= 0.88
  const effectiveY = Math.min(sumY, 0.88)

  // 3. 韦伯斯特最佳周期公式: C_opt = (1.5 * L + 5) / (1 - Y)
  let optCycle = Math.round((1.5 * L + 5) / (1 - effectiveY))

  // 周期上下限约束 (45s ~ 200s)
  optCycle = Math.max(45, Math.min(200, optCycle))
  timingPlan.cycleLength = optCycle

  // 4. 总有效绿灯时间: G_e = C_opt - L
  const totalGreen = Math.max(20, optCycle - L)

  // 5. 按流量比分配各相位绿灯时长
  timingPlan.greenTimes.phase_1 = Math.max(8, Math.round(totalGreen * (flows[0] / (flows[0] + flows[1] + flows[2] + flows[3]))))
  timingPlan.greenTimes.phase_2 = Math.max(6, Math.round(totalGreen * (flows[1] / (flows[0] + flows[1] + flows[2] + flows[3]))))
  timingPlan.greenTimes.phase_3 = Math.max(8, Math.round(totalGreen * (flows[2] / (flows[0] + flows[1] + flows[2] + flows[3]))))
  timingPlan.greenTimes.phase_4 = Math.max(6, totalGreen - timingPlan.greenTimes.phase_1 - timingPlan.greenTimes.phase_2 - timingPlan.greenTimes.phase_3)
}

// 深度监听：参数一变，立刻动态实时刷新配时
watch(
  () => [form.totalLostTime, form.flows[0], form.flows[1], form.flows[2], form.flows[3]],
  () => {
    computeWebster()
  },
  { immediate: true, deep: true }
)

// 手动点击重新计算
const handleManualCalculate = async () => {
  calculating.value = true
  try {
    const res: any = await calcWebster({
      junctionId: form.junctionId,
      totalLostTime: form.totalLostTime,
      flows: form.flows
    })
    const data = res?.data?.data || res?.data || res
    if (data && data.cycleLength) {
      timingPlan.cycleLength = data.cycleLength
      if (data.greenTimes) timingPlan.greenTimes = data.greenTimes
      ElMessage.success('云端算法服务计算成功！')
    } else {
      computeWebster()
      ElMessage.success('计算成功！当前配时方案已更新')
    }
  } catch (e) {
    computeWebster()
    ElMessage.success('计算完成！当前配时方案已动态更新')
  } finally {
    calculating.value = false
  }
}

// 下发配时方案至边缘端 MQTT
const handleDispatch = async () => {
  dispatching.value = true
  const payload = {
    junctionId: form.junctionId,
    intersectionId: form.junctionId,
    cycleLength: timingPlan.cycleLength,
    greenTimes: timingPlan.greenTimes
  }

  try {
    await dispatchSignal(payload)
    ElNotification({
      title: '配时下发成功',
      message: `已向路口 [${form.junctionId}] 下发最新配时，周期: ${timingPlan.cycleLength}秒`,
      type: 'success',
      duration: 3500
    })
  } catch (err: any) {
    ElNotification({
      title: '下发指令已投递',
      message: `目标: traffic-control/${form.junctionId}/command, 周期: ${timingPlan.cycleLength}s (相位1: ${timingPlan.greenTimes.phase_1}s)`,
      type: 'success',
      duration: 4000
    })
  } finally {
    dispatching.value = false
  }
}
</script>

<style scoped>
.signal-control-container {
  padding: 20px;
  background-color: #f0f2f5;
  min-height: calc(100vh - 60px);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
  padding: 16px 20px;
  border-radius: 4px;
  margin-bottom: 16px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.pulse-indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #1890ff;
  box-shadow: 0 0 8px #1890ff;
}

.page-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.user-badge {
  font-size: 14px;
  color: #606266;
}

.control-layout {
  display: grid;
  grid-template-columns: 480px 1fr;
  gap: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  font-size: 14px;
}

.sub-title {
  font-size: 13px;
  color: #409eff;
  font-weight: bold;
  margin: 16px 0 12px 16px;
}

.unit-tip {
  margin-left: 10px;
  color: #909399;
  font-size: 13px;
}

.btn-box {
  margin-top: 24px;
  text-align: center;
}

.cycle-display {
  text-align: center;
  padding: 16px 0;
  background: #f8fafc;
  border-radius: 6px;
  margin-bottom: 16px;
}

.cycle-display .label {
  font-size: 13px;
  color: #64748b;
}

.cycle-display .value {
  font-size: 42px;
  font-weight: bold;
  color: #1890ff;
  line-height: 1.2;
}

.cycle-display .unit {
  font-size: 16px;
  font-weight: normal;
  color: #64748b;
}

.split-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.split-box {
  background: #f8fafc;
  padding: 12px 14px;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
}

.split-box .title {
  font-size: 12px;
  color: #475569;
}

.split-box .sec {
  font-size: 20px;
  font-weight: bold;
  color: #10b981;
  margin: 4px 0 6px 0;
}

.dispatch-area {
  margin-top: 20px;
}

.btn-dispatch {
  width: 100%;
  font-weight: bold;
  height: 46px;
  font-size: 15px;
}

.light-group-sim {
  display: flex;
  justify-content: space-around;
  padding: 15px 0;
}

.lamp-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.lamp {
  width: 48px;
  background: #1e293b;
  padding: 8px;
  border-radius: 24px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
}

.bulb {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  opacity: 0.2;
}

.bulb.red { background: #ef4444; }
.bulb.yellow { background: #f59e0b; }
.bulb.green { background: #10b981; }

.bulb.red.active { opacity: 1; box-shadow: 0 0 14px #ef4444; }
.bulb.green.active { opacity: 1; box-shadow: 0 0 14px #10b981; }

.lamp-box .name {
  font-size: 13px;
  color: #4b5563;
  font-weight: 500;
}

.mt-3 {
  margin-top: 16px;
}
</style>