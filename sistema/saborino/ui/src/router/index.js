import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AppLayout from '@/components/AppLayout.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue') },
    { path: '/esqueci-senha', name: 'forgot-password', component: () => import('@/views/ForgotPasswordView.vue') },
    { path: '/reenviar-confirmacao', name: 'resend-verification', component: () => import('@/views/ResendVerificationView.vue') },
    { path: '/redefinir-senha', name: 'reset-password', component: () => import('@/views/ResetPasswordView.vue') },
    { path: '/confirmar-email', name: 'confirm-email', component: () => import('@/views/ConfirmEmailView.vue') },
    {
      path: '/',
      component: AppLayout,
      meta: { requiresAuth: true },
      children: [
        { path: '', name: 'dashboard', component: () => import('@/views/DashboardView.vue') },
        { path: 'venda', name: 'venda', component: () => import('@/views/VendaRapidaView.vue') },
        { path: 'vendas', name: 'vendas', component: () => import('@/views/VendasView.vue') },
        { path: 'a-receber', name: 'a-receber', component: () => import('@/views/AReceberView.vue') },
        { path: 'produtos', name: 'produtos', component: () => import('@/views/ProdutosView.vue') },
        { path: 'clientes', name: 'clientes', component: () => import('@/views/ClientesView.vue') },
        { path: 'compras', name: 'compras', component: () => import('@/views/ComprasView.vue') },
        { path: 'producao', name: 'producao', component: () => import('@/views/ProducaoView.vue') },
        { path: 'fechamento', name: 'fechamento', component: () => import('@/views/FechamentoView.vue') },
        { path: 'config', name: 'config', component: () => import('@/views/ConfigView.vue') },
        { path: 'conta/seguranca', name: 'account-security', component: () => import('@/views/AccountSecurityView.vue') },
      ],
    },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.initialize()
  if (to.meta.requiresAuth && !auth.isAuthenticated) return { name: 'login' }
  if (to.name === 'login' && auth.isAuthenticated) return { name: 'dashboard' }
  return true
})

export default router
