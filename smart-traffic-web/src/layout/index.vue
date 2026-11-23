<template>
  <router-view v-if="$route.name === 'Dashboard'" />
  <el-container v-else class="layout-container">
    <el-aside width="220px" class="aside">
      <div class="logo">🚦 智慧路口平台</div>
      <el-menu
        router
        :default-active="$route.path"
        background-color="#001529"
        text-color="#fff"
        active-text-color="#409EFF"
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataAnalysis /></el-icon>
          <span>实时监控大屏</span>
        </el-menu-item>
        <el-menu-item index="/control">
          <el-icon><Operation /></el-icon>
          <span>信号灯控制</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <span class="title">路口智能调控中心</span>
        <el-dropdown @command="handleCommand">
          <span class="user">
            <el-icon><User /></el-icon> admin
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>

      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
const router = useRouter()

const handleCommand = (cmd: string) => {
  if (cmd === 'logout') {
    localStorage.removeItem('token')
    router.push('/login')
  }
}
</script>

<style scoped>
.layout-container { height: 100vh; }
.aside { background: #001529; }
.logo {
  height: 60px; line-height: 60px; color: #fff;
  text-align: center; font-size: 16px; font-weight: bold;
  border-bottom: 1px solid #1f2d3d;
}
.header {
  background: #fff; display: flex; justify-content: space-between;
  align-items: center; border-bottom: 1px solid #e4e7ed;
}
.title { font-size: 18px; font-weight: 500; }
.user { cursor: pointer; display: flex; align-items: center; gap: 4px; }
.main { background: #f0f2f5; }
.el-menu { border-right: none; }
</style>