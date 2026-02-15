<template>
  <div class="layout-shell">
    <aside class="sidebar">
      <div class="brand">
        <p class="brand-title">Bin AI Console</p>
        <p class="brand-sub">Tech Intelligence Radar</p>
      </div>
      <el-menu
        class="menu"
        :default-active="$route.path"
        router
        background-color="transparent"
        text-color="#d9e8ff"
        active-text-color="#22c55e"
      >
        <el-menu-item index="/dashboard">Dashboard</el-menu-item>
        <el-menu-item index="/contents">Contents</el-menu-item>
        <el-menu-item index="/settings">Settings</el-menu-item>
        <el-menu-item index="/history">History</el-menu-item>
      </el-menu>
    </aside>

    <section class="main-zone">
      <header class="topbar">
        <div>
          <h1 class="topbar-title">AI 资讯监控与推送系统</h1>
          <p class="topbar-sub">聚合、分析、分发三段式看板</p>
        </div>
        <el-tag class="req-tag" effect="dark" type="success">
          请求中 {{ pendingCount }}
        </el-tag>
      </header>
      <main class="page-content">
        <transition name="page" mode="out-in">
          <slot />
        </transition>
      </main>
    </section>
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { useGlobalLoading } from '../../composables/uiFeedback'

useRoute()
const { pendingCount } = useGlobalLoading()
</script>

<style scoped>
.layout-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 250px minmax(0, 1fr);
}

.sidebar {
  border-right: 1px solid rgba(54, 82, 123, 0.52);
  background: linear-gradient(180deg, rgba(12, 26, 47, 0.9), rgba(9, 20, 40, 0.92));
  padding: 24px 16px;
}

.brand {
  padding: 4px 12px 20px;
}

.brand-title {
  font-family: 'Lexend', sans-serif;
  font-size: 22px;
  letter-spacing: 0.4px;
}

.brand-sub {
  margin-top: 6px;
  color: var(--text-sub);
  font-size: 12px;
  letter-spacing: 0.8px;
  text-transform: uppercase;
}

.menu {
  border: 0;
}

:deep(.el-menu-item) {
  border-radius: 10px;
  margin-bottom: 8px;
  transition: all 220ms ease;
}

:deep(.el-menu-item:hover) {
  background: rgba(29, 64, 107, 0.62);
}

.main-zone {
  min-width: 0;
  padding: 20px 22px 26px;
}

.topbar {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 18px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(150deg, rgba(17, 33, 60, 0.94), rgba(12, 26, 50, 0.82));
}

.topbar-title {
  font-size: 24px;
}

.topbar-sub {
  margin-top: 6px;
  color: var(--text-sub);
}

.req-tag {
  font-family: 'Lexend', sans-serif;
}

.page-content {
  margin-top: 18px;
}

@media (max-width: 1024px) {
  .layout-shell {
    grid-template-columns: 1fr;
  }

  .sidebar {
    border-right: 0;
    border-bottom: 1px solid rgba(54, 82, 123, 0.52);
    padding-bottom: 8px;
  }

  :deep(.el-menu--vertical) {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 8px;
  }

  :deep(.el-menu-item) {
    margin-bottom: 0;
    justify-content: center;
  }

  .main-zone {
    padding: 14px;
  }

  .topbar {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
}
</style>
