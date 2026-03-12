import { createRouter, createWebHashHistory } from 'vue-router'

import HomeView from '../views/HomeView.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: HomeView
  },
  {
    path: '/notion',
    name: 'ChongQiNaoYu',
    component: () => import('../notion/ChongQiNaoYu.vue')
  },
  {
    path: '/leetcode',
    name: 'LeetCodeView',
    component: () => import('../views/code/leetCodeView.vue')
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

export default router

