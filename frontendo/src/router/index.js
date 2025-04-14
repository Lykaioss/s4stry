import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'
import LoginView from '@/views/LoginView.vue'
import UploadsView from '@/views/UploadsView.vue'


const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/log',
      name: 'log',
      component: LoginView,
    },
    {
      path: '/upload',
      name: 'upload',
      component: UploadsView,
    },
    
  ],
})

export default router
