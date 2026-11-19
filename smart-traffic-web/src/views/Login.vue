<template>
  <div class="login-bg">
    <el-card class="login-card">
      <div class="title">🚦 智慧路口管理平台</div>
      <el-form @keyup.enter="handleLogin">
        <el-form-item>
          <el-input v-model="form.username" placeholder="用户名" size="large" prefix-icon="User" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" type="password" placeholder="密码" size="large" prefix-icon="Lock" show-password />
        </el-form-item>
        <el-button type="primary" size="large" style="width: 100%" :loading="loading" @click="handleLogin">
          登 录
        </el-button>
      </el-form>
      <div class="tip">默认账号：admin / password</div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login } from '../api/traffic'

const router = useRouter()
const loading = ref(false)
const form = ref({ username: 'admin', password: 'password' })

const handleLogin = async () => {
  loading.value = true
  try {
    const res: any = await login(form.value)
    const token = res.data?.token || res.token
    localStorage.setItem('token', token)
    ElMessage.success('登录成功')
    router.push('/')
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-bg {
  height: 100vh;
  background: linear-gradient(135deg, #1e3c72, #2a5298);
  display: flex; justify-content: center; align-items: center;
}
.login-card { width: 420px; padding: 20px; }
.title { font-size: 22px; font-weight: bold; text-align: center; margin-bottom: 30px; }
.tip { text-align: center; color: #909399; font-size: 12px; margin-top: 10px; }
</style>